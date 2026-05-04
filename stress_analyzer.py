"""
Stress Week Analyzer.
For each week: total estimated effort + exam presence -> High Stress / Busy / Normal.
"""

from datetime import date, timedelta
from collections import defaultdict

# Thresholds (hours per week)
HIGH_STRESS_EFFORT = 20.0
BUSY_EFFORT_MIN = 10.0


def _week_start(d: date) -> date:
    """Monday of the week containing d."""
    # weekday(): Monday=0, Sunday=6
    return d - timedelta(days=d.weekday())


def _week_key(d: date) -> str:
    """String key for the week (e.g. '2025-02-17') for grouping."""
    return _week_start(d).isoformat()


def analyze_stress_weeks(assignments: list, exams: list, today: date = None) -> dict:
    """
    For each week that has assignments or exams:
    - Sum estimated effort (hours) of assignments with deadline in that week.
    - Check if any exam falls in that week.
    - Classify: effort > 20 or exam present -> "High Stress";
                10 <= effort <= 20 -> "Busy"; else -> "Normal".

    assignments: list of objects with .deadline, .estimated_effort_hours
    exams: list of objects with .exam_date
    Returns dict: { "week_key": { "level": "High Stress"|"Busy"|"Normal", "effort": float, "has_exam": bool } }
    """
    if today is None:
        today = date.today()

    # Sum effort per week (by assignment deadline week)
    effort_by_week = defaultdict(float)
    for a in assignments:
        if getattr(a, "deadline", None) is None:
            continue
        d = a.deadline.date() if hasattr(a.deadline, "date") else a.deadline
        wk = _week_key(d)
        effort_by_week[wk] += getattr(a, "estimated_effort_hours", 0) or 0

    # Mark weeks with exams
    exam_weeks = set()
    for e in exams:
        if getattr(e, "exam_date", None) is None:
            continue
        d = e.exam_date.date() if hasattr(e.exam_date, "date") else e.exam_date
        exam_weeks.add(_week_key(d))

    # Build result for every week we care about (weeks with effort or exam)
    all_weeks = set(effort_by_week.keys()) | exam_weeks
    result = {}
    for wk in sorted(all_weeks):
        effort = effort_by_week.get(wk, 0.0)
        has_exam = wk in exam_weeks
        if effort > HIGH_STRESS_EFFORT or has_exam:
            level = "High Stress"
        elif BUSY_EFFORT_MIN <= effort <= HIGH_STRESS_EFFORT:
            level = "Busy"
        else:
            level = "Normal"
        result[wk] = {"level": level, "effort": round(effort, 1), "has_exam": has_exam}
    return result


def get_week_level(week_start_date: date, assignments: list, exams: list, today: date = None) -> str:
    """Return stress level for the week containing week_start_date."""
    wk = _week_key(week_start_date)
    analysis = analyze_stress_weeks(assignments, exams, today)
    return analysis.get(wk, {}).get("level", "Normal")
