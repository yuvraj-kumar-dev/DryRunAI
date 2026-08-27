"""Loads the v0 problem bank and provides selection/progression lookups.

Progression is selection logic, not a data relationship: "next problem" means same topic, a tier
chosen from how the last one went, excluding anything already seen this session. See
backend/app/data/dsa_problems_v0.json's metadata.escalation_note for why.
"""

import json
import random
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data" / "dsa_problems_v0.json"

with open(DATA_PATH, encoding="utf-8") as f:
    _BANK = json.load(f)

PROBLEMS = _BANK["problems"]
TOPICS = _BANK["metadata"]["topics"]
DIFFICULTY_ORDER = _BANK["metadata"]["difficulty_order"]

_BY_ID = {p["id"]: p for p in PROBLEMS}

# Fields shown to the candidate on screen (and pushed to the browser when the problem changes).
# Deliberately excludes hints (for the AI to use verbally if needed, not for the candidate to
# read), follow_up_questions, source_reference, and prep_sheets_seen_on (internal/attribution
# metadata, not interview content).
PUBLIC_FIELDS = [
    "id",
    "title",
    "topic",
    "difficulty",
    "problem_statement",
    "constraints",
    "examples",
]


def public_problem(problem: dict) -> dict:
    return {k: problem[k] for k in PUBLIC_FIELDS}


def get_problem(problem_id: str) -> dict:
    return _BY_ID[problem_id]


def select_problem(topic: str, difficulty: str) -> dict:
    """Pick a random problem matching topic + difficulty."""
    candidates = [p for p in PROBLEMS if p["topic"] == topic and p["difficulty"] == difficulty]
    if not candidates:
        raise ValueError(f"No problems for topic={topic!r} difficulty={difficulty!r}")
    return random.choice(candidates)


def _candidates(topic: str, difficulty: str, exclude_ids: list[str]) -> list[dict]:
    return [
        p
        for p in PROBLEMS
        if p["topic"] == topic and p["difficulty"] == difficulty and p["id"] not in exclude_ids
    ]


def get_next_problem(current: dict, solved: bool, exclude_ids: list[str]) -> dict | None:
    """The problem to hand the candidate after `current`.

    Solved it well -> step up a difficulty tier. Struggled -> stay at the same tier with a
    different problem, so they get another fair shot rather than being buried. Either way the
    interview moves on: a candidate who is stuck still needs a new problem, which is the whole
    point of this function existing (interviews used to never leave question one).

    Falls back to the other tier if the preferred one is exhausted, then to any unseen problem in
    the topic. Returns None only if the topic has nothing left at all.
    """
    idx = DIFFICULTY_ORDER.index(current["difficulty"])
    harder = DIFFICULTY_ORDER[idx + 1] if idx + 1 < len(DIFFICULTY_ORDER) else None
    same = current["difficulty"]

    preference = [harder, same] if solved else [same, harder]
    for difficulty in preference:
        if difficulty is None:
            continue
        candidates = _candidates(current["topic"], difficulty, exclude_ids)
        if candidates:
            return random.choice(candidates)

    remaining = [p for p in PROBLEMS if p["topic"] == current["topic"] and p["id"] not in exclude_ids]
    return random.choice(remaining) if remaining else None
