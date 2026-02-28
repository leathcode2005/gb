"""Report generation for GradeBook Pro."""

import os
from typing import Optional
from datetime import datetime

from .database import DatabaseManager
from .utils import (
    format_percent, calculate_letter_grade, format_date, truncate_text
)


class ReportGenerator:
    """Generates text-based reports for classes and students."""

    def __init__(self, db: DatabaseManager):
        """Initialize with a DatabaseManager."""
        self.db = db

    # ------------------------------------------------------------------ #
    #  Student Report Card                                                 #
    # ------------------------------------------------------------------ #

    def generate_student_report(self, student_id: int) -> str:
        """Generate a full report card for a single student."""
        student = self.db.get_student(student_id)
        if student is None:
            return "Student not found."

        class_ = self.db.get_class(student.class_id)
        if class_ is None:
            return "Class not found."

        result = self.db.calculate_student_grade(student_id, student.class_id)
        pct = result["weighted_percent"]

        thresholds = []
        if class_.grade_scale_id:
            thresholds = self.db.get_thresholds_for_scale(class_.grade_scale_id)
        letter = calculate_letter_grade(pct, thresholds) if thresholds else "N/A"

        lines = [
            "=" * 60,
            "  STUDENT REPORT CARD",
            "=" * 60,
            f"  Student : {student.name}",
            f"  ID      : {student.student_id or 'N/A'}",
            f"  Email   : {student.email or 'N/A'}",
            f"  Class   : {class_.name}  [{class_.section}]",
            f"  Semester: {class_.semester} {class_.year}",
            "-" * 60,
            f"  Overall Grade : {format_percent(pct)}  ({letter})",
            "-" * 60,
            "  CATEGORY BREAKDOWN",
            "",
        ]

        for cat_name, info in result["category_scores"].items():
            lines.append(
                f"  {truncate_text(cat_name, 22):<22}"
                f"  Avg: {format_percent(info['average']):<8}"
                f"  Weight: {info['weight']:.0f}%"
                f"  (n={info['count']})"
            )

        lines += ["", "-" * 60, "  ASSIGNMENT DETAIL", ""]

        categories = self.db.get_categories_for_class(student.class_id)
        for cat in categories:
            lines.append(f"  [{cat.name}]")
            assignments = self.db.get_assignments_for_category(cat.id)  # type: ignore[arg-type]
            for asgn in assignments:
                grade = self.db.get_grade(asgn.id, student_id)  # type: ignore[arg-type]
                if grade:
                    if grade.status == "excused":
                        score_str = "Excused"
                    elif grade.status == "missing":
                        score_str = "Missing"
                    elif grade.points_earned is not None:
                        score_str = (
                            f"{grade.points_earned:.1f}/{asgn.total_points:.0f}"
                            f" ({grade.points_earned/asgn.total_points*100:.1f}%)"
                        )
                    else:
                        score_str = "Not graded"
                else:
                    score_str = "Not graded"
                lines.append(
                    f"    {truncate_text(asgn.name, 30):<30}  {score_str}"
                )
            lines.append("")

        lines += [
            "=" * 60,
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Class Roster                                                        #
    # ------------------------------------------------------------------ #

    def generate_class_roster(self, class_id: int) -> str:
        """Generate a full roster with grades for a class."""
        class_ = self.db.get_class(class_id)
        if class_ is None:
            return "Class not found."

        students = self.db.get_students_for_class(class_id)

        thresholds = []
        if class_.grade_scale_id:
            thresholds = self.db.get_thresholds_for_scale(class_.grade_scale_id)

        lines = [
            "=" * 70,
            f"  CLASS ROSTER: {class_.name}  [{class_.section}]",
            f"  {class_.semester} {class_.year}",
            "=" * 70,
            f"  {'NAME':<25}  {'ID':<12}  {'GRADE %':>8}  {'LETTER':>6}",
            "-" * 70,
        ]

        for student in students:
            result = self.db.calculate_student_grade(student.id, class_id)  # type: ignore[arg-type]
            pct = result["weighted_percent"]
            letter = calculate_letter_grade(pct, thresholds) if thresholds else "N/A"
            lines.append(
                f"  {truncate_text(student.name, 25):<25}"
                f"  {truncate_text(student.student_id or 'N/A', 12):<12}"
                f"  {format_percent(pct):>8}"
                f"  {letter:>6}"
            )

        lines += [
            "-" * 70,
            f"  Total Students: {len(students)}",
            "=" * 70,
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 70,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Statistics Summary                                                  #
    # ------------------------------------------------------------------ #

    def generate_statistics(self, class_id: int) -> str:
        """Generate a statistics summary for a class."""
        class_ = self.db.get_class(class_id)
        if class_ is None:
            return "Class not found."

        stats = self.db.get_class_statistics(class_id)
        lines = [
            "=" * 50,
            f"  CLASS STATISTICS: {class_.name}",
            "=" * 50,
            f"  Students : {stats['count']}",
            f"  Average  : {format_percent(stats['average'])}",
            f"  Median   : {format_percent(stats['median'])}",
            f"  Highest  : {format_percent(stats['high'])}",
            f"  Lowest   : {format_percent(stats['low'])}",
        ]

        if stats["grade_distribution"]:
            lines += ["", "  GRADE DISTRIBUTION", "  " + "-" * 20]
            for letter in sorted(stats["grade_distribution"]):
                lines.append(f"  {letter:<4}: {stats['grade_distribution'][letter]}")

        lines += [
            "=" * 50,
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  ASCII Histogram                                                     #
    # ------------------------------------------------------------------ #

    def generate_distribution_histogram(self, class_id: int) -> str:
        """Generate an ASCII histogram of grade distribution."""
        class_ = self.db.get_class(class_id)
        if class_ is None:
            return "Class not found."

        students = self.db.get_students_for_class(class_id)
        if not students:
            return "No students in class."

        buckets = {
            "90-100": 0, "80-89": 0, "70-79": 0,
            "60-69": 0, "0-59": 0,
        }
        for student in students:
            result = self.db.calculate_student_grade(student.id, class_id)  # type: ignore[arg-type]
            pct = result["weighted_percent"]
            if pct >= 90:
                buckets["90-100"] += 1
            elif pct >= 80:
                buckets["80-89"] += 1
            elif pct >= 70:
                buckets["70-79"] += 1
            elif pct >= 60:
                buckets["60-69"] += 1
            else:
                buckets["0-59"] += 1

        max_count = max(buckets.values()) if buckets.values() else 1
        bar_width = 30

        lines = [
            "=" * 50,
            f"  GRADE DISTRIBUTION: {class_.name}",
            "=" * 50,
        ]
        for label, count in buckets.items():
            bar_len = int(count / max_count * bar_width) if max_count else 0
            bar = "█" * bar_len
            lines.append(f"  {label} |{bar:<{bar_width}}| {count}")

        lines += [
            "=" * 50,
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  File Export                                                         #
    # ------------------------------------------------------------------ #

    def export_to_file(self, content: str, filename: str) -> bool:
        """
        Write *content* to *filename*.

        Returns True on success, False on failure.
        """
        try:
            with open(filename, "w", encoding="utf-8") as fh:
                fh.write(content)
            return True
        except Exception:
            return False
