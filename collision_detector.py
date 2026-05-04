"""
Deadline Collision Detection.
- Multiple assignments within the same 7-day window.
- Assignment deadline within 3 days of an exam.
"""

from datetime import date, timedelta
from collections import defaultdict


def _to_date(d) -> date:
    """Normalize to date."""
    if hasattr(d, "date"):
        return d.date()
    return d


def _week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def _week_key(d: date) -> str:
    """String key for the week for grouping."""
    return _week_start(d).isoformat()


def collisions_7day(assignments: list, today: date = None) -> list:
    """
    Detect if multiple assignments fall within the same 7-day window (same calendar week).
    Returns list of groups: each group is a list of (assignment, deadline) where
    all deadlines fall in one week. Only groups with 2+ items are returned.
    """
    if today is None:
        today = date.today()
    buckets = defaultdict(list)
    for a in assignments:
        dl = getattr(a, "deadline", None)
        if dl is None:
            continue
        d = _to_date(dl)
        if d < today:
            continue
        key = _week_key(d)
        buckets[key].append((a, d))
    return [group for group in buckets.values() if len(group) >= 2]


def collisions_near_exam(assignments: list, exams: list, days_near: int = 3, today: date = None) -> list:
    """
    Detect if any assignment deadline is within `days_near` days of an exam.
    Returns list of dicts: { "assignment": a, "exam": e, "days_between": int }.
    """
    if today is None:
        today = date.today()
    result = []
    for a in assignments:
        dl = getattr(a, "deadline", None)
        if dl is None:
            continue
        d = _to_date(dl)
        if d < today:
            continue
        for e in exams:
            ed = getattr(e, "exam_date", None)
            if ed is None:
                continue
            ed = _to_date(ed)
            delta = abs((d - ed).days)
            if delta <= days_near:
                result.append({"assignment": a, "exam": e, "days_between": delta})
    return result


def all_collisions(assignments: list, exams: list, today: date = None) -> dict:
    """
    Return both 7-day and exam-near collisions for dashboard.
    """
    return {
        "seven_day": collisions_7day(assignments, today),
        "near_exam": collisions_near_exam(assignments, exams, days_near=3, today=today),
    }
