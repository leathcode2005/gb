"""Utility helpers for GradeBook Pro."""

import re
from typing import List, Optional
from .models import GradeThreshold


def format_grade(points_earned: Optional[float], total_points: float) -> str:
    """
    Format a grade as 'earned/total (pct%)'.

    Returns '--' if points_earned is None.
    """
    if points_earned is None:
        return f"--/{total_points:.0f}"
    pct = (points_earned / total_points * 100) if total_points else 0.0
    return f"{points_earned:.1f}/{total_points:.0f} ({pct:.1f}%)"


def calculate_letter_grade(percent: float,
                            thresholds: List[GradeThreshold]) -> str:
    """
    Return the letter grade for *percent* using the provided thresholds.

    Thresholds should be ordered by min_percent descending.
    Returns 'N/A' if no threshold matches.
    """
    for t in sorted(thresholds, key=lambda x: x.min_percent, reverse=True):
        if percent >= t.min_percent:
            return t.letter
    return "F"


def format_percent(value: float) -> str:
    """Return a percentage string, e.g. '87.3%'."""
    return f"{value:.1f}%"


def truncate_text(text: str, max_len: int, ellipsis: str = "…") -> str:
    """Truncate *text* to at most *max_len* characters, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    if max_len <= len(ellipsis):
        return ellipsis[:max_len]
    return text[: max_len - len(ellipsis)] + ellipsis


def format_date(date_str: str) -> str:
    """
    Return a human-friendly date string.

    Accepts ISO-8601 or YYYY-MM-DD.  Falls back to the original string.
    """
    if not date_str:
        return ""
    try:
        from datetime import datetime
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str[:len(fmt) + 2], fmt)
                return dt.strftime("%b %d, %Y")
            except ValueError:
                continue
    except Exception:
        pass
    return date_str


def validate_email(email: str) -> bool:
    """Return True if *email* looks like a valid e-mail address."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def gpa_points(letter: str) -> float:
    """Return the 4.0-scale GPA points for a letter grade."""
    mapping = {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0, "D-": 0.7,
        "F": 0.0,
    }
    return mapping.get(letter.upper(), 0.0)


def calculate_gpa(letter_grades: List[str],
                  credit_hours: Optional[List[float]] = None) -> float:
    """
    Calculate GPA from a list of letter grades.

    Optionally weighted by *credit_hours*.
    """
    if not letter_grades:
        return 0.0
    if credit_hours is None:
        credit_hours = [1.0] * len(letter_grades)
    total_credits = sum(credit_hours)
    if total_credits == 0:
        return 0.0
    weighted = sum(gpa_points(g) * c
                   for g, c in zip(letter_grades, credit_hours))
    return weighted / total_credits
