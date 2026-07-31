"""Loads the v0 problem bank and provides selection/escalation lookups.

Escalation is selection logic, not a data relationship: "harder follow-up" means
same topic, next tier in difficulty_order, excluding the current problem. See
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


def get_problem(problem_id: str) -> dict:
    return _BY_ID[problem_id]


def select_problem(topic: str, difficulty: str) -> dict:
    """Pick a random problem matching topic + difficulty."""
    candidates = [p for p in PROBLEMS if p["topic"] == topic and p["difficulty"] == difficulty]
    if not candidates:
        raise ValueError(f"No problems for topic={topic!r} difficulty={difficulty!r}")
    return random.choice(candidates)


def get_escalation_candidate(current: dict) -> dict | None:
    """Same topic, next difficulty tier up, excluding the current problem.

    Returns None if `current` is already at the hardest tier for its topic.
    """
    idx = DIFFICULTY_ORDER.index(current["difficulty"])
    if idx + 1 >= len(DIFFICULTY_ORDER):
        return None
    next_difficulty = DIFFICULTY_ORDER[idx + 1]
    candidates = [
        p
        for p in PROBLEMS
        if p["topic"] == current["topic"] and p["difficulty"] == next_difficulty and p["id"] != current["id"]
    ]
    if not candidates:
        return None
    return random.choice(candidates)
