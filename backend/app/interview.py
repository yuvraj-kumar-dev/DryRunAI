"""Interview logic: persona system prompts, scorecard generation.

Kept separate from voice.py so the Pipecat/transport plumbing doesn't get
tangled up with "what should the interviewer actually say/do" logic.
"""

import json

from groq import AsyncGroq

from app import config

PERSONAS = {
    "neutral": (
        "You are a professional, matter-of-fact technical interviewer -- polite but not going "
        "out of your way to be warm. This is a realistic DSA (data structures and algorithms) "
        "interview, closest to an actual FAANG-style loop."
    ),
    "strict": (
        "You are a strict, high-bar technical interviewer. Minimal hand-holding, higher "
        "expectations. This is closer to a tough FAANG-style interviewer who expects the "
        "candidate to drive the conversation and justify every choice."
    ),
}

INTERVIEWER_BEHAVIOR = """
You are conducting a live, spoken DSA (data structures and algorithms) technical interview.
This is a real-time voice conversation -- keep responses brief and conversational, never long
monologues, since this is spoken aloud, not read as text.

Flow:
1. Present the problem below conversationally (don't just recite it verbatim).
2. Let the candidate ask clarifying questions about constraints/edge cases before they code.
   Answer like a real interviewer would -- don't over-share, make them ask the right questions.
3. Once they say they have an approach, discuss it briefly: why this approach, what's the time/
   space complexity. Use the get_current_code tool to check what they've written so far whenever
   it's relevant -- don't ask them to read their code aloud, and don't announce that you're
   checking it or narrate the result back -- just use what you learn to ask a sharper question.
4. If they seem stuck (long pauses, going in circles, explicitly asking for help), offer a nudge
   using the hints below -- give the smallest hint that unblocks them, not the full solution.
5. When they believe they're done, check their code with get_current_code and discuss correctness
   and complexity with them.
6. If they solved it well (correct, good complexity discussion, handled edge cases), call the
   escalate_to_harder_problem tool to move to a harder follow-up problem in the same topic, and
   introduce it conversationally, the same way you introduced the first problem.
7. There is no time limit -- let the conversation run naturally.

Problem: {title} ({difficulty}, {topic})

{statement}

Constraints: {constraints}

Hints available if they get stuck (use sparingly, smallest hint first): {hints}
""".strip()


def build_system_instruction(problem: dict, persona: str) -> str:
    persona_prompt = PERSONAS.get(persona, PERSONAS["neutral"])
    body = INTERVIEWER_BEHAVIOR.format(
        title=problem["title"],
        difficulty=problem["difficulty"],
        topic=problem["topic"],
        statement=problem["problem_statement"],
        constraints="; ".join(problem["constraints"]),
        hints=" | ".join(problem["hints"]),
    )
    return f"{persona_prompt}\n\n{body}"


SCORECARD_RUBRIC = """
You are scoring a completed DSA technical interview. You'll be given the full conversation
transcript and the candidate's final code. Produce a structured scorecard using this generic
rubric (not company-specific):

- correctness: does the code solve the stated problem? Note any bugs or missed edge cases.
- complexity: did the candidate identify and achieve a reasonable time/space complexity for the
  problem? Note if they settled for a suboptimal approach without recognizing it.
- problem_solving_approach: did they ask good clarifying questions, reason through the approach
  before coding, and handle being stuck (if it came up) productively?
- communication: did they explain their thinking clearly as they went?
- overall_verdict: one of "strong hire", "hire", "no hire" -- a generic bar, not tied to any
  specific company.
- summary: 2-3 sentences of the most useful feedback.

Return ONLY a JSON object with exactly these keys: correctness, complexity,
problem_solving_approach, communication, overall_verdict, summary.
""".strip()


async def generate_scorecard(transcript: list[dict], final_code: str, problem: dict) -> dict:
    """Direct Groq call, outside the voice pipeline -- not latency-sensitive, so it can afford
    more careful prompting than the live conversation.
    """
    client = AsyncGroq(api_key=config.GROQ_API_KEY)
    transcript_text = "\n".join(
        f"{m.get('role', '?')}: {m.get('content', '')}" for m in transcript if m.get("content")
    )
    user_prompt = (
        f"Problem: {problem['title']} ({problem['difficulty']}, {problem['topic']})\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Final code:\n{final_code or '(no code submitted)'}"
    )
    response = await client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SCORECARD_RUBRIC},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
