"""Data models for GradeBook Pro."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class User:
    """Represents an application user."""
    id: Optional[int]
    username: str
    password_hash: str
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class GradeScale:
    """A named grade scale belonging to a user."""
    id: Optional[int]
    user_id: int
    name: str


@dataclass
class GradeThreshold:
    """A single letter-grade threshold within a scale."""
    id: Optional[int]
    scale_id: int
    letter: str
    min_percent: float
    max_percent: float


@dataclass
class Class_:
    """Represents a class/course."""
    id: Optional[int]
    user_id: int
    name: str
    section: str = ""
    semester: str = ""
    year: int = 0
    grade_scale_id: Optional[int] = None

    def __post_init__(self):
        if self.year == 0:
            self.year = datetime.now().year


@dataclass
class Category:
    """An assignment category with a weight."""
    id: Optional[int]
    class_id: int
    name: str
    weight: float          # percentage 0-100
    drop_lowest: int = 0


@dataclass
class Student:
    """A student enrolled in a class."""
    id: Optional[int]
    class_id: int
    name: str
    student_id: str = ""
    email: str = ""


@dataclass
class Assignment:
    """An assignment within a category."""
    id: Optional[int]
    category_id: int
    name: str
    total_points: float
    due_date: str = ""
    description: str = ""


@dataclass
class Grade:
    """A grade for one student on one assignment."""
    id: Optional[int]
    assignment_id: int
    student_id: int
    points_earned: Optional[float] = None
    status: str = "pending"   # pending | graded | excused | missing | late
    submitted_at: str = ""

    def __post_init__(self):
        if not self.submitted_at:
            self.submitted_at = datetime.now().isoformat()


@dataclass
class Attendance:
    """Attendance record for a student on a date."""
    id: Optional[int]
    class_id: int
    student_id: int
    date: str
    status: str = "present"   # present | absent | late | excused


@dataclass
class UndoAction:
    """Represents an undoable action."""
    action_type: str          # insert | update | delete
    table: str
    data: Dict[str, Any]
    old_data: Optional[Dict[str, Any]] = None
