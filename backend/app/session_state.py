"""Session state + problem progression, deliberately free of any Pipecat/transport imports.

Everything here is the "what happens in an interview" logic: which problem is current, how the
interview advances from one problem to the next, what the LLM is reminded of, and what gets
written to the session file. voice.py wraps these in tool functions and adds the realtime
plumbing (pushing updates to the browser, TTS, etc.); scripts/text_interview.py drives the exact
same functions from a terminal with no audio at all, which is the only cheap way to test a full
multi-problem interview end to end.

Keep it that way -- if something in here starts needing a Pipecat import, it belongs in voice.py.
"""

from __future__ import annotations

import time

from app import interview, problems


def new_session(session_id: str, problem: dict, persona: str, plan_size: int) -> dict:
    """A fresh session sitting on its first problem.

    `context` is filled in later by whoever owns the LLM conversation (voice.py's pipeline, or
    the text harness's shim) -- everything here works on the session dict alone.
    """
    return {
        "session_id": session_id,
        "persona": persona,
        "plan_size": plan_size,
        "started_at": time.time(),
        # 0-based index of the problem currently under discussion.
        "problem_index": 0,
        "initial_problem_id": problem["id"],
        "current_problem": problem,
        # Every problem already finished with, in order, each with the code left behind on it.
        "completed_problems": [],
        # Guards against handing the candidate the same problem twice in one interview.
        "seen_problem_ids": [problem["id"]],
        "latest_code": "",
        "code_snapshots": [],
        "finished": False,
        "end_reason": None,
        "scorecard": None,
        "llm_error_timestamps": [],
        "context": None,
        "context_reminder_message": None,
        "consecutive_tool_calls": 0,
    }


def is_on_last_problem(session: dict) -> bool:
    return session["problem_index"] + 1 >= session["plan_size"]


def record_code_snapshot(session: dict, code: str) -> None:
    session["latest_code"] = code
    session["code_snapshots"].append(
        {
            "timestamp": time.time(),
            "problem_id": session["current_problem"]["id"],
            "code": code,
        }
    )
    update_context_reminder(session)


def advance_to_next_problem(session: dict, solved: bool, reason: str) -> dict | None:
    """Archive the current problem and move to the next one. Returns the new problem, or None.

    None means "there is no next problem" -- either the plan is exhausted or the bank has nothing
    left in this topic. The caller is expected to wind the interview up at that point rather than
    treating it as an error.

    `solved` only steers *which* problem comes next (harder tier vs. another at the same tier);
    it never decides whether to move on at all. A candidate who is thoroughly stuck still needs
    to be moved off the problem -- the real sessions that prompted this work were interviews that
    never left question one.
    """
    if is_on_last_problem(session):
        return None
    nxt = problems.get_next_problem(
        session["current_problem"], solved=solved, exclude_ids=session["seen_problem_ids"]
    )
    if nxt is None:
        return None

    current = session["current_problem"]
    session["completed_problems"].append(
        {
            "problem_id": current["id"],
            "title": current["title"],
            "difficulty": current["difficulty"],
            "topic": current["topic"],
            "code": session["latest_code"],
            "solved": solved,
            "reason": reason,
        }
    )
    session["current_problem"] = nxt
    session["seen_problem_ids"].append(nxt["id"])
    session["problem_index"] += 1
    # The editor is cleared client-side for the new problem, so the server's idea of "current
    # code" has to reset in lockstep -- otherwise the Reminder would show the previous problem's
    # solution as if it were work on the new one. The old code is safe in completed_problems.
    session["latest_code"] = ""
    update_context_reminder(session)
    return nxt


def attempted_problems(session: dict) -> list[dict]:
    """Every problem this interview touched, finished or not -- the input the scorecard scores.

    Includes the in-flight current problem, since an interview usually ends on one rather than
    after neatly closing it out.
    """
    attempts = [
        {
            "problem": problems.get_problem(entry["problem_id"]),
            "code": entry["code"],
            "solved": entry["solved"],
        }
        for entry in session["completed_problems"]
    ]
    attempts.append(
        {"problem": session["current_problem"], "code": session["latest_code"], "solved": None}
    )
    return attempts


def update_context_reminder(session: dict) -> None:
    """Create or refresh the single "Reminder" developer message that grounds the LLM.

    This is the authoritative statement of what problem is being discussed and what the candidate
    has written -- deliberately the *only* place the current problem's text lives. The system
    prompt used to carry the initial problem's full statement, which meant that after a problem
    change the prompt and reality disagreed, and the model reliably sided with the (frozen)
    system prompt: real sessions show it inventing its own "harder variant" of problem one
    instead of presenting the problem it had just been handed. With the problem text living only
    here, there is nothing stale left for it to fall back on.

    Re-added at the end of context (removing the previous instance) rather than mutated in place:
    an LLM weighs recent context far more heavily than something buried mid-conversation, so
    keeping this at the tail on every update is what makes it work as a drift countermeasure, not
    just a way of bounding token count.
    """
    context = session.get("context")
    if context is None:
        return
    problem = session["current_problem"]
    index = session["problem_index"] + 1
    total = session["plan_size"]
    code = session["latest_code"]

    lines = [
        "Reminder -- current session state. This is authoritative: it overrides anything said",
        "earlier in this conversation, including by you.",
        "",
        f"You are on problem {index} of {total} in this interview.",
        "",
        "THE PROBLEM CURRENTLY UNDER DISCUSSION -- the only one you may talk about:",
        interview.format_problem_block(problem),
        "",
        "The candidate's current code, exactly as it stands in their editor:",
        code or "(nothing written yet)",
    ]
    if is_on_last_problem(session):
        lines += [
            "",
            "This is the LAST problem of the interview. When it is done, call end_interview "
            "rather than move_to_next_problem.",
        ]
    content = "\n".join(lines)

    old = session.get("context_reminder_message")
    if old is not None:
        try:
            context.messages.remove(old)
        except ValueError:
            pass
    reminder = {"role": "developer", "content": content}
    context.add_message(reminder)
    session["context_reminder_message"] = reminder


def session_record(session: dict, transcript: list[dict], scorecard: dict | None) -> dict:
    """The JSON blob persisted to sessions/ and served back to the report screen."""
    return {
        "session_id": session["session_id"],
        "persona": session["persona"],
        "plan_size": session["plan_size"],
        "initial_problem_id": session["initial_problem_id"],
        "final_problem_id": session["current_problem"]["id"],
        "problems_attempted": [
            {
                "problem_id": a["problem"]["id"],
                "title": a["problem"]["title"],
                "difficulty": a["problem"]["difficulty"],
                "topic": a["problem"]["topic"],
                "code": a["code"],
                "solved": a["solved"],
            }
            for a in attempted_problems(session)
        ],
        "end_reason": session["end_reason"],
        "code_snapshots": session["code_snapshots"],
        "final_code": session["latest_code"],
        "transcript": transcript,
        "scorecard": scorecard,
    }
