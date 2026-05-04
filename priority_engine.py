"""
AI-Assisted Priority Recommendation Engine.
Computes priorityScore = (0.4 * urgency) + (w_difficulty * difficulty_norm) + (0.3 * effort_norm).
Uses user-specific difficulty weight when available (learning component).
"""

from datetime import date
from typing import List, Tuple

# Default weights (urgency, difficulty, effort)
DEFAULT_URGENCY_WEIGHT = 0.4
DEFAULT_DIFFICULTY_WEIGHT = 0.3
DEFAULT_EFFORT_WEIGHT = 0.3


def _urgency(days_left: float) -> float:
    """Urgency = 1 / days_left. Cap days_left at 0.1 to avoid division by zero."""
    if days_left is None or days_left < 0:
        return 0.0
    return 1.0 / max(0.1, days_left)


def _normalize_difficulty(d: int) -> float:
    """Map difficulty 1-5 to 0-1 (higher = harder)."""
    if d is None:
        return 0.5
    return max(0.0, min(1.0, (d - 1) / 4.0))


def _normalize_effort(hours: float, max_hours: float = 40.0) -> float:
    """Map effort hours to 0-1 scale (capped at max_hours)."""
    if hours is None or hours <= 0:
        return 0.0
    return min(1.0, hours / max_hours)


def compute_priority_score(
    days_left: float,
    difficulty: int,
    effort_hours: float,
    difficulty_weight: float = DEFAULT_DIFFICULTY_WEIGHT,
) -> float:
    """
    Compute priority score for one assignment.
    priorityScore = (0.4 * urgency) + (difficulty_weight * difficulty_norm) + (0.3 * effort_norm).
    """
    u = _urgency(days_left)
    d_norm = _normalize_difficulty(difficulty)
    e_norm = _normalize_effort(effort_hours)
    # Keep urgency and effort weights fixed; only difficulty weight is user-tunable
    effort_weight = 1.0 - DEFAULT_URGENCY_WEIGHT - difficulty_weight
    effort_weight = max(0.0, min(0.5, effort_weight))
    return (DEFAULT_URGENCY_WEIGHT * u) + (difficulty_weight * d_norm) + (effort_weight * e_norm)


def get_days_left(deadline, today=None):
    """Return days until deadline (can be negative if past)."""
    if today is None:
        today = date.today()
    if hasattr(deadline, "date"):
        deadline = deadline.date()
    delta = deadline - today
    return delta.days


def recommended_order(assignments: list, today=None, difficulty_weight: float = DEFAULT_DIFFICULTY_WEIGHT) -> List[Tuple]:
    """
    Sort assignments by priority score descending.
    assignments: list of objects with .deadline, .difficulty, .estimated_effort_hours (and optionally .id, .title, etc.)
    Returns list of (assignment, priority_score) tuples, highest score first.
    """
    if today is None:
        today = date.today()
    scored = []
    for a in assignments:
        days_left = get_days_left(a.deadline, today)
        score = compute_priority_score(
            days_left,
            a.difficulty,
            a.estimated_effort_hours,
            difficulty_weight=difficulty_weight,
        )
        scored.append((a, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
