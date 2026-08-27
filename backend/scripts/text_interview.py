"""Drive a full interview from the terminal -- same prompt, same tools, same state, no audio.

Why this exists: the interview's real failure modes (never leaving problem one, presenting an
invented problem instead of the one it was handed, never reaching a scorecard) only show up in a
*complete* multi-problem run. Testing those over voice costs a real spoken session every attempt
and takes ten minutes to reach the interesting part. This reaches it in about a minute of typing,
for a fraction of a cent of Groq tokens, and exercises the exact same code paths that voice.py
does -- interview.build_system_instruction, session_state.*, problems.get_next_problem -- so a
pass here is meaningful, not a mock.

What it does NOT cover: Deepgram STT/TTS, barge-in, and the RTVI push to the browser (it prints
what *would* have been pushed instead). Those still need one real voice run.

Usage, from backend/ with the venv active:
    python -m scripts.text_interview                     # 2 problems, neutral, Array/Easy
    python -m scripts.text_interview --plan-size 2 --topic "Linked List" --difficulty Easy
    python -m scripts.text_interview --persona strict --script scripts/scripted_run.txt
    python -m scripts.text_interview --problem-id ll-e-01 --script scripts/scripted_run_ll.txt

Commands available at the prompt:
    /code <text>   replace your "editor" contents with one line of code
    /code          open a multi-line block, ended with a line containing only "."
    /state         dump problem index / current problem / seen ids
    /end           hit the "End interview" button (forces the scorecard)
    /quit          leave without a scorecard
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groq import AsyncGroq  # noqa: E402

from app import config, interview, problems  # noqa: E402
from app import session_state as state  # noqa: E402


class FakeContext:
    """Stands in for Pipecat's LLMContext.

    session_state only ever touches .messages and .add_message(), so this is the whole contract.
    Keeping it this small is the point: it means the harness needs no Pipecat import at all, and
    can't silently diverge from what the real pipeline stores.
    """

    def __init__(self):
        self.messages: list[dict] = []

    def add_message(self, message: dict) -> None:
        self.messages.append(message)


# Windows consoles default to cp1252, and the model regularly emits characters it can't encode
# (zero-width spaces, curly quotes, em dashes) -- which crashed the harness mid-interview rather
# than printing them. Nothing downstream cares how these render, so replace rather than fail.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

C_BOT = "\033[96m"
C_YOU = "\033[92m"
C_SYS = "\033[93m"
C_DIM = "\033[90m"
C_OFF = "\033[0m"


def say(colour: str, label: str, text: str) -> None:
    print(f"{colour}{label}:{C_OFF} {text}")


# ---------------------------------------------------------------------------------------------
# Tool layer: the same operations voice.py's tools perform, minus the Pipecat plumbing.
# ---------------------------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_code",
            "description": (
                "Read the candidate's current code so far, exactly as it's written in their "
                "editor. You normally do NOT need this -- the Reminder message already carries "
                "their current code and is refreshed automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string", "description": "Why you're checking now."}},
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_to_next_problem",
            "description": (
                "Finish with the current problem and move the interview on to the next one. "
                "After calling this, the Reminder message will name a NEW problem -- present "
                "that problem, exactly as the Reminder states it. Do not invent your own."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Why you're moving on."},
                    "solved": {
                        "type": "boolean",
                        "description": (
                            "true if they genuinely solved it, false if stuck. Only decides how "
                            "hard the next problem is -- either way the interview moves on."
                        ),
                    },
                },
                "required": ["reason", "solved"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "end_interview",
            "description": (
                "End the interview and send the candidate their scorecard. Say a short closing "
                "line immediately after calling it."
            ),
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string", "description": "Why it's ending."}},
                "required": ["reason"],
            },
        },
    },
]


def run_tool(session: dict, name: str, args: dict) -> dict:
    """Mirror of the tool bodies in voice.py. Keep the two in step."""
    if name == "get_current_code":
        code = session["latest_code"]
        say(C_DIM, "tool", f"get_current_code({args.get('reason')!r})")
        return {"code": code or "(the candidate hasn't written any code yet)"}

    if name == "move_to_next_problem":
        solved = bool(args.get("solved"))
        say(C_DIM, "tool", f"move_to_next_problem(solved={solved}, {args.get('reason')!r})")
        nxt = state.advance_to_next_problem(session, solved=solved, reason=args.get("reason", ""))
        if nxt is None:
            return {
                "moved": False,
                "instruction": (
                    "That was the last problem of the interview -- there is no next one. Say a "
                    "brief closing line and call end_interview now."
                ),
            }
        # This is the message the browser receives over the voice WebSocket in the real app --
        # printing it here is how you check the screen would actually have updated.
        say(C_SYS, ">> PUSHED TO BROWSER", f"problem_changed -> {nxt['title']} ({nxt['difficulty']})")
        return {
            "moved": True,
            "instruction": (
                "The interview has moved on. The Reminder message now states the new problem and "
                "the candidate's screen already shows it. Present THAT problem conversationally "
                "right now -- do not describe any other problem."
            ),
            "problem_number": session["problem_index"] + 1,
            "of": session["plan_size"],
        }

    if name == "end_interview":
        say(C_DIM, "tool", f"end_interview({args.get('reason')!r})")
        session["end_requested"] = True
        session["end_reason"] = args.get("reason", "")
        return {
            "ok": True,
            "instruction": (
                "Interview is ending. Say ONE short closing line now -- thank them and tell them "
                "their scorecard is on its way. Do not ask another question."
            ),
        }

    return {"error": f"unknown tool {name}"}


# ---------------------------------------------------------------------------------------------
# Conversation loop
# ---------------------------------------------------------------------------------------------


async def run_turn(client: AsyncGroq, session: dict, system: str) -> None:
    """One completion, following tool calls until the model actually speaks.

    Mirrors the real pipeline's tool-call loop breaker: after MAX_TOOL_HOPS tool calls with no
    spoken output, tools are switched off for the next completion so it is structurally forced to
    produce text (voice.py does this with LLMSetToolChoiceFrame).
    """
    MAX_TOOL_HOPS = 2
    hops = 0
    while True:
        response = await client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "system", "content": system}, *session["context"].messages],
            tools=TOOL_SCHEMAS,
            tool_choice="none" if hops >= MAX_TOOL_HOPS else "auto",
        )
        message = response.choices[0].message
        calls = message.tool_calls or []

        if not calls:
            text = (message.content or "").strip()
            session["context"].add_message({"role": "assistant", "content": text})
            say(C_BOT, "interviewer", text)
            return

        session["context"].add_message(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                    }
                    for c in calls
                ],
            }
        )
        for call in calls:
            raw = call.function.arguments
            # The confirmed Pipecat/Groq zero-argument bug produces the literal string "null"
            # here. Every tool takes a required argument specifically to avoid it, but parse
            # defensively so the harness reports it rather than crashing if it ever recurs.
            try:
                args = json.loads(raw) if raw and raw != "null" else {}
            except json.JSONDecodeError:
                say(C_SYS, "!! bad tool args", repr(raw))
                args = {}
            result = run_tool(session, call.function.name, args)
            if result.get("moved"):
                # Mirror voice.py: a successful move forces the next completion to be speech, so
                # the new problem actually gets presented instead of the model chaining straight
                # into another tool call.
                hops = MAX_TOOL_HOPS - 1
            session["context"].add_message(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
            )
        hops += 1
        # advance_to_next_problem already refreshed the Reminder; this keeps it at the tail of
        # context, after the tool results, which is where it has to be to win.
        state.update_context_reminder(session)


def read_code_block() -> str:
    print(f"{C_DIM}(paste code, end with a line containing only '.'){C_OFF}")
    lines = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-size", type=int, default=2)
    parser.add_argument("--topic", default="Array")
    parser.add_argument("--difficulty", default="Easy")
    parser.add_argument("--persona", default="neutral")
    parser.add_argument("--script", help="File of candidate turns, one per line, run unattended")
    parser.add_argument(
        "--problem-id",
        help=(
            "Pin the first problem (e.g. arr-e-01) instead of picking randomly from topic/"
            "difficulty. Scripted runs need this -- a script written for one problem is nonsense "
            "against another, and the drift looks like a bug in the interviewer."
        ),
    )
    args = parser.parse_args()

    if not config.GROQ_API_KEY:
        sys.exit("GROQ_API_KEY is not set -- check the .env at the repo root.")

    if args.problem_id:
        problem = problems.get_problem(args.problem_id)
        args.topic, args.difficulty = problem["topic"], problem["difficulty"]
    else:
        problem = problems.select_problem(args.topic, args.difficulty)
    session = state.new_session(str(uuid.uuid4()), problem, args.persona, args.plan_size)
    session["context"] = FakeContext()
    system = interview.build_system_instruction(args.persona, args.plan_size)
    client = AsyncGroq(api_key=config.GROQ_API_KEY)

    print(f"{C_SYS}Interview: {args.plan_size} problem(s), {args.topic}/{args.difficulty}, {args.persona} persona{C_OFF}")
    print(f"{C_SYS}Problem 1: {problem['title']} ({problem['difficulty']}){C_OFF}\n")

    state.update_context_reminder(session)
    session["context"].add_message(
        {"role": "developer", "content": "Greet the candidate and present the problem now."}
    )
    await run_turn(client, session, system)

    scripted = None
    if args.script:
        scripted = iter(Path(args.script).read_text(encoding="utf-8").splitlines())

    while not session.get("end_requested"):
        if scripted is not None:
            turn = next(scripted, "/end")
            if not turn.strip():
                continue
            say(C_YOU, "you", turn)
        else:
            try:
                turn = input(f"{C_YOU}you:{C_OFF} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                turn = "/quit"

        if not turn:
            continue
        if turn == "/quit":
            print(f"{C_SYS}Left without a scorecard.{C_OFF}")
            return
        if turn == "/state":
            print(
                f"{C_DIM}problem {session['problem_index'] + 1}/{session['plan_size']} "
                f"| current={session['current_problem']['id']} ({session['current_problem']['title']}) "
                f"| seen={session['seen_problem_ids']} "
                f"| code={len(session['latest_code'])} chars{C_OFF}"
            )
            continue
        if turn == "/end":
            session["end_requested"] = True
            session["end_reason"] = "candidate ended the interview"
            break
        if turn.startswith("/code"):
            rest = turn[len("/code") :].strip()
            # Scripted runs are one turn per line, so a literal \n is the only way to write
            # multi-line code in them.
            code = rest.replace("\\n", "\n") if rest else read_code_block()
            state.record_code_snapshot(session, code)
            say(C_DIM, "editor", f"{len(code)} chars saved")
            continue

        session["context"].add_message({"role": "user", "content": turn})
        await run_turn(client, session, system)

    print(f"\n{C_SYS}Generating scorecard...{C_OFF}")
    attempts = state.attempted_problems(session)
    scorecard = await interview.generate_scorecard(session["context"].messages, attempts)
    record = state.session_record(session, session["context"].messages, scorecard)

    print(f"\n{C_SYS}=== Problems attempted ==={C_OFF}")
    for i, attempt in enumerate(record["problems_attempted"], start=1):
        print(f"  {i}. {attempt['title']} ({attempt['difficulty']}) -- solved={attempt['solved']}, "
              f"{len(attempt['code'] or '')} chars of code")
    print(f"\n{C_SYS}=== Scorecard ==={C_OFF}")
    print(json.dumps(scorecard, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
