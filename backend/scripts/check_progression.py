"""Deterministic checks on interview progression -- no API calls, no network, runs in a second.

Covers the mechanics the LLM sits on top of: does the interview actually advance, does the
Reminder follow it, does the code archive per problem, does the plan end where it should, and
does the scorecard get handed every problem rather than only the last one.

    python -m scripts.check_progression
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import problems  # noqa: E402
from app import session_state as state  # noqa: E402


class FakeContext:
    def __init__(self):
        self.messages: list[dict] = []

    def add_message(self, message: dict) -> None:
        self.messages.append(message)


def make_session(plan_size: int = 2, topic: str = "Array", difficulty: str = "Easy") -> dict:
    problem = problems.select_problem(topic, difficulty)
    session = state.new_session("test-session", problem, "neutral", plan_size)
    session["context"] = FakeContext()
    state.update_context_reminder(session)
    return session


def reminder_text(session: dict) -> str:
    return session["context_reminder_message"]["content"]


checks: list[tuple[str, bool]] = []


def check(label: str, condition: bool) -> None:
    checks.append((label, bool(condition)))


# --- a two-problem interview advances exactly once, then refuses ------------------------------
s = make_session(plan_size=2)
first = s["current_problem"]
state.record_code_snapshot(s, "def solve(nums):\n    return nums")

check("reminder carries the problem statement", first["problem_statement"][:40] in reminder_text(s))
check("reminder carries the candidate's code", "def solve(nums)" in reminder_text(s))
check("reminder shows problem 1 of 2", "problem 1 of 2" in reminder_text(s))
check("problem 1 of 2 is not flagged as the last", "LAST problem" not in reminder_text(s))

second = state.advance_to_next_problem(s, solved=True, reason="clean O(n)")
check("advancing returns a new problem", second is not None)
check("the new problem is different", second["id"] != first["id"])
check("solved=True steps the difficulty up", second["difficulty"] == "Medium")
check("session now points at the new problem", s["current_problem"]["id"] == second["id"])
check("index advanced", s["problem_index"] == 1)
check("editor state reset for the new problem", s["latest_code"] == "")
check("old code archived", s["completed_problems"][0]["code"].startswith("def solve"))
check("archive records the solved flag", s["completed_problems"][0]["solved"] is True)
check("reminder followed the change", second["problem_statement"][:40] in reminder_text(s))
check("stale problem text is gone from the reminder", first["problem_statement"][:40] not in reminder_text(s))
check("reminder no longer shows the old code", "def solve(nums)" not in reminder_text(s))
check("reminder shows problem 2 of 2", "problem 2 of 2" in reminder_text(s))
check("last problem is flagged as last", "LAST problem" in reminder_text(s))
check("exactly one reminder in context", sum(1 for m in s["context"].messages if m["content"].startswith("Reminder")) == 1)
check("reminder is the newest message", s["context"].messages[-1] is s["context_reminder_message"])

check("plan exhausted -> no further advance", state.advance_to_next_problem(s, solved=True, reason="x") is None)
check("refusal left the session untouched", s["current_problem"]["id"] == second["id"] and s["problem_index"] == 1)

# --- struggling keeps the difficulty rather than burying them ---------------------------------
s2 = make_session(plan_size=3)
start = s2["current_problem"]
nxt = state.advance_to_next_problem(s2, solved=False, reason="couldn't get started")
check("solved=False holds the difficulty tier", nxt["difficulty"] == start["difficulty"])
check("solved=False still moves on", nxt["id"] != start["id"])

# --- no repeats across a long interview -------------------------------------------------------
s3 = make_session(plan_size=4)
ids = [s3["current_problem"]["id"]]
while state.advance_to_next_problem(s3, solved=True, reason="ok") is not None:
    ids.append(s3["current_problem"]["id"])
check("a 4-problem plan yields 4 problems", len(ids) == 4)
check("no problem repeats", len(set(ids)) == len(ids))
check("all from the chosen topic", all(problems.get_problem(i)["topic"] == "Array" for i in ids))

# --- a 1-problem interview never tries to advance ---------------------------------------------
s4 = make_session(plan_size=1)
check("1-problem plan is immediately the last", state.is_on_last_problem(s4))
check("1-problem plan cannot advance", state.advance_to_next_problem(s4, solved=True, reason="x") is None)

# --- the scorecard is handed every problem, not just the current one --------------------------
s5 = make_session(plan_size=2)
state.record_code_snapshot(s5, "first problem code")
state.advance_to_next_problem(s5, solved=True, reason="good")
state.record_code_snapshot(s5, "second problem code")
attempts = state.attempted_problems(s5)
check("both problems reach the scorecard", len(attempts) == 2)
check("each attempt keeps its own code", [a["code"] for a in attempts] == ["first problem code", "second problem code"])

record = state.session_record(s5, s5["context"].messages, {"overall_verdict": "hire"})
check("record lists both problems", len(record["problems_attempted"]) == 2)
check("record keeps the initial problem id", record["initial_problem_id"] == attempts[0]["problem"]["id"])
check("record keeps the final problem id", record["final_problem_id"] == attempts[1]["problem"]["id"])
check("record carries the scorecard", record["scorecard"]["overall_verdict"] == "hire")
check("snapshots are attributed per problem", {sn["problem_id"] for sn in record["code_snapshots"]} == {a["problem"]["id"] for a in attempts})

# --- report ------------------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
for label, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
