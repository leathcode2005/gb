"""Database layer for GradeBook Pro using SQLite."""

import sqlite3
import os
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime

from .models import (
    User, Class_, Category, GradeScale, GradeThreshold,
    Student, Assignment, Grade, Attendance
)


DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".gradebook_pro.db")


class DatabaseManager:
    """Manages all SQLite interactions for GradeBook Pro."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize the database manager and create tables."""
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()

    # ------------------------------------------------------------------ #
    #  Connection helpers                                                   #
    # ------------------------------------------------------------------ #

    def _connect(self) -> None:
        """Open the SQLite connection."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def _cursor(self) -> sqlite3.Cursor:
        if self._conn is None:
            self._connect()
        return self._conn.cursor()  # type: ignore[union-attr]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------ #
    #  Schema creation                                                      #
    # ------------------------------------------------------------------ #

    def _create_tables(self) -> None:
        """Create all tables if they do not already exist."""
        ddl = """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS grade_scales (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS grade_thresholds (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            scale_id    INTEGER NOT NULL REFERENCES grade_scales(id) ON DELETE CASCADE,
            letter      TEXT    NOT NULL,
            min_percent REAL    NOT NULL,
            max_percent REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS classes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name           TEXT    NOT NULL,
            section        TEXT    DEFAULT '',
            semester       TEXT    DEFAULT '',
            year           INTEGER DEFAULT 0,
            grade_scale_id INTEGER REFERENCES grade_scales(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id    INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name        TEXT    NOT NULL,
            weight      REAL    NOT NULL,
            drop_lowest INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS students (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id   INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            name       TEXT    NOT NULL,
            student_id TEXT    DEFAULT '',
            email      TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            name         TEXT    NOT NULL,
            total_points REAL    NOT NULL,
            due_date     TEXT    DEFAULT '',
            description  TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS grades (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            student_id    INTEGER NOT NULL REFERENCES students(id)   ON DELETE CASCADE,
            points_earned REAL,
            status        TEXT    DEFAULT 'pending',
            submitted_at  TEXT    NOT NULL,
            UNIQUE(assignment_id, student_id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id   INTEGER NOT NULL REFERENCES classes(id)  ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            date       TEXT    NOT NULL,
            status     TEXT    DEFAULT 'present',
            UNIQUE(class_id, student_id, date)
        );
        """
        cur = self._cursor()
        cur.executescript(ddl)
        self._conn.commit()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    #  Users                                                               #
    # ------------------------------------------------------------------ #

    def create_user(self, username: str, password_hash: str) -> User:
        """Insert a new user and return the User object."""
        created_at = datetime.now().isoformat()
        cur = self._cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
            (username, password_hash, created_at)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return User(id=cur.lastrowid, username=username,
                    password_hash=password_hash, created_at=created_at)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Return a User by username, or None."""
        cur = self._cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row:
            return User(id=row["id"], username=row["username"],
                        password_hash=row["password_hash"],
                        created_at=row["created_at"])
        return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Return a User by id, or None."""
        cur = self._cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if row:
            return User(id=row["id"], username=row["username"],
                        password_hash=row["password_hash"],
                        created_at=row["created_at"])
        return None

    # ------------------------------------------------------------------ #
    #  Grade Scales                                                        #
    # ------------------------------------------------------------------ #

    def create_default_scale(self, user_id: int) -> GradeScale:
        """Create the default A/B/C/D/F grade scale for a user."""
        cur = self._cursor()
        cur.execute(
            "INSERT INTO grade_scales (user_id, name) VALUES (?,?)",
            (user_id, "Default")
        )
        scale_id = cur.lastrowid
        thresholds = [
            ("A+", 97, 100), ("A", 93, 96.99), ("A-", 90, 92.99),
            ("B+", 87, 89.99), ("B", 83, 86.99), ("B-", 80, 82.99),
            ("C+", 77, 79.99), ("C", 73, 76.99), ("C-", 70, 72.99),
            ("D+", 67, 69.99), ("D", 63, 66.99), ("D-", 60, 62.99),
            ("F",   0, 59.99),
        ]
        cur.executemany(
            "INSERT INTO grade_thresholds (scale_id, letter, min_percent, max_percent) VALUES (?,?,?,?)",
            [(scale_id, l, mn, mx) for l, mn, mx in thresholds]
        )
        self._conn.commit()  # type: ignore[union-attr]
        return GradeScale(id=scale_id, user_id=user_id, name="Default")

    def get_scales_for_user(self, user_id: int) -> List[GradeScale]:
        """Return all grade scales for a user."""
        cur = self._cursor()
        cur.execute("SELECT * FROM grade_scales WHERE user_id=?", (user_id,))
        return [GradeScale(id=r["id"], user_id=r["user_id"], name=r["name"])
                for r in cur.fetchall()]

    def get_thresholds_for_scale(self, scale_id: int) -> List[GradeThreshold]:
        """Return all thresholds for a grade scale, ordered by min_percent desc."""
        cur = self._cursor()
        cur.execute(
            "SELECT * FROM grade_thresholds WHERE scale_id=? ORDER BY min_percent DESC",
            (scale_id,)
        )
        return [
            GradeThreshold(id=r["id"], scale_id=r["scale_id"], letter=r["letter"],
                           min_percent=r["min_percent"], max_percent=r["max_percent"])
            for r in cur.fetchall()
        ]

    def create_scale(self, user_id: int, name: str) -> GradeScale:
        """Create a new (empty) grade scale."""
        cur = self._cursor()
        cur.execute("INSERT INTO grade_scales (user_id, name) VALUES (?,?)",
                    (user_id, name))
        self._conn.commit()  # type: ignore[union-attr]
        return GradeScale(id=cur.lastrowid, user_id=user_id, name=name)

    def delete_scale(self, scale_id: int) -> None:
        """Delete a grade scale and its thresholds."""
        cur = self._cursor()
        cur.execute("DELETE FROM grade_scales WHERE id=?", (scale_id,))
        self._conn.commit()  # type: ignore[union-attr]

    def upsert_threshold(self, scale_id: int, letter: str,
                         min_pct: float, max_pct: float) -> GradeThreshold:
        """Insert or replace a grade threshold."""
        cur = self._cursor()
        cur.execute(
            """INSERT OR REPLACE INTO grade_thresholds
               (scale_id, letter, min_percent, max_percent) VALUES (?,?,?,?)""",
            (scale_id, letter, min_pct, max_pct)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return GradeThreshold(id=cur.lastrowid, scale_id=scale_id, letter=letter,
                              min_percent=min_pct, max_percent=max_pct)

    # ------------------------------------------------------------------ #
    #  Classes                                                             #
    # ------------------------------------------------------------------ #

    def create_class(self, user_id: int, name: str, section: str = "",
                     semester: str = "", year: int = 0,
                     grade_scale_id: Optional[int] = None) -> Class_:
        """Create a new class."""
        if year == 0:
            year = datetime.now().year
        cur = self._cursor()
        cur.execute(
            """INSERT INTO classes (user_id, name, section, semester, year, grade_scale_id)
               VALUES (?,?,?,?,?,?)""",
            (user_id, name, section, semester, year, grade_scale_id)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return Class_(id=cur.lastrowid, user_id=user_id, name=name,
                      section=section, semester=semester, year=year,
                      grade_scale_id=grade_scale_id)

    def get_classes_for_user(self, user_id: int) -> List[Class_]:
        """Return all classes for a user."""
        cur = self._cursor()
        cur.execute("SELECT * FROM classes WHERE user_id=? ORDER BY year DESC, name",
                    (user_id,))
        return [Class_(id=r["id"], user_id=r["user_id"], name=r["name"],
                       section=r["section"], semester=r["semester"],
                       year=r["year"], grade_scale_id=r["grade_scale_id"])
                for r in cur.fetchall()]

    def get_class(self, class_id: int) -> Optional[Class_]:
        """Return a single class by id."""
        cur = self._cursor()
        cur.execute("SELECT * FROM classes WHERE id=?", (class_id,))
        r = cur.fetchone()
        if r:
            return Class_(id=r["id"], user_id=r["user_id"], name=r["name"],
                          section=r["section"], semester=r["semester"],
                          year=r["year"], grade_scale_id=r["grade_scale_id"])
        return None

    def update_class(self, class_id: int, **kwargs: Any) -> None:
        """Update class fields."""
        fields = ", ".join(f"{k}=?" for k in kwargs)
        cur = self._cursor()
        cur.execute(f"UPDATE classes SET {fields} WHERE id=?",
                    (*kwargs.values(), class_id))
        self._conn.commit()  # type: ignore[union-attr]

    def delete_class(self, class_id: int) -> None:
        """Delete a class and all its data."""
        cur = self._cursor()
        cur.execute("DELETE FROM classes WHERE id=?", (class_id,))
        self._conn.commit()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    #  Categories                                                          #
    # ------------------------------------------------------------------ #

    def create_category(self, class_id: int, name: str, weight: float,
                        drop_lowest: int = 0) -> Category:
        """Create a new assignment category."""
        cur = self._cursor()
        cur.execute(
            "INSERT INTO categories (class_id, name, weight, drop_lowest) VALUES (?,?,?,?)",
            (class_id, name, weight, drop_lowest)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return Category(id=cur.lastrowid, class_id=class_id, name=name,
                        weight=weight, drop_lowest=drop_lowest)

    def get_categories_for_class(self, class_id: int) -> List[Category]:
        """Return all categories for a class."""
        cur = self._cursor()
        cur.execute("SELECT * FROM categories WHERE class_id=? ORDER BY name",
                    (class_id,))
        return [Category(id=r["id"], class_id=r["class_id"], name=r["name"],
                         weight=r["weight"], drop_lowest=r["drop_lowest"])
                for r in cur.fetchall()]

    def get_category(self, category_id: int) -> Optional[Category]:
        """Return a single category."""
        cur = self._cursor()
        cur.execute("SELECT * FROM categories WHERE id=?", (category_id,))
        r = cur.fetchone()
        if r:
            return Category(id=r["id"], class_id=r["class_id"], name=r["name"],
                            weight=r["weight"], drop_lowest=r["drop_lowest"])
        return None

    def update_category(self, category_id: int, **kwargs: Any) -> None:
        """Update category fields."""
        fields = ", ".join(f"{k}=?" for k in kwargs)
        cur = self._cursor()
        cur.execute(f"UPDATE categories SET {fields} WHERE id=?",
                    (*kwargs.values(), category_id))
        self._conn.commit()  # type: ignore[union-attr]

    def delete_category(self, category_id: int) -> None:
        """Delete a category."""
        cur = self._cursor()
        cur.execute("DELETE FROM categories WHERE id=?", (category_id,))
        self._conn.commit()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    #  Students                                                            #
    # ------------------------------------------------------------------ #

    def create_student(self, class_id: int, name: str,
                       student_id: str = "", email: str = "") -> Student:
        """Create a new student."""
        cur = self._cursor()
        cur.execute(
            "INSERT INTO students (class_id, name, student_id, email) VALUES (?,?,?,?)",
            (class_id, name, student_id, email)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return Student(id=cur.lastrowid, class_id=class_id, name=name,
                       student_id=student_id, email=email)

    def get_students_for_class(self, class_id: int) -> List[Student]:
        """Return all students in a class, ordered by name."""
        cur = self._cursor()
        cur.execute("SELECT * FROM students WHERE class_id=? ORDER BY name",
                    (class_id,))
        return [Student(id=r["id"], class_id=r["class_id"], name=r["name"],
                        student_id=r["student_id"], email=r["email"])
                for r in cur.fetchall()]

    def get_student(self, student_id: int) -> Optional[Student]:
        """Return a single student."""
        cur = self._cursor()
        cur.execute("SELECT * FROM students WHERE id=?", (student_id,))
        r = cur.fetchone()
        if r:
            return Student(id=r["id"], class_id=r["class_id"], name=r["name"],
                           student_id=r["student_id"], email=r["email"])
        return None

    def update_student(self, student_id: int, **kwargs: Any) -> None:
        """Update student fields."""
        fields = ", ".join(f"{k}=?" for k in kwargs)
        cur = self._cursor()
        cur.execute(f"UPDATE students SET {fields} WHERE id=?",
                    (*kwargs.values(), student_id))
        self._conn.commit()  # type: ignore[union-attr]

    def delete_student(self, student_id: int) -> None:
        """Delete a student."""
        cur = self._cursor()
        cur.execute("DELETE FROM students WHERE id=?", (student_id,))
        self._conn.commit()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    #  Assignments                                                         #
    # ------------------------------------------------------------------ #

    def create_assignment(self, category_id: int, name: str,
                          total_points: float, due_date: str = "",
                          description: str = "") -> Assignment:
        """Create a new assignment."""
        cur = self._cursor()
        cur.execute(
            """INSERT INTO assignments (category_id, name, total_points, due_date, description)
               VALUES (?,?,?,?,?)""",
            (category_id, name, total_points, due_date, description)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return Assignment(id=cur.lastrowid, category_id=category_id, name=name,
                          total_points=total_points, due_date=due_date,
                          description=description)

    def get_assignments_for_category(self, category_id: int) -> List[Assignment]:
        """Return all assignments for a category."""
        cur = self._cursor()
        cur.execute(
            "SELECT * FROM assignments WHERE category_id=? ORDER BY due_date, name",
            (category_id,)
        )
        return [Assignment(id=r["id"], category_id=r["category_id"], name=r["name"],
                           total_points=r["total_points"], due_date=r["due_date"],
                           description=r["description"])
                for r in cur.fetchall()]

    def get_assignments_for_class(self, class_id: int) -> List[Assignment]:
        """Return all assignments for all categories in a class."""
        cur = self._cursor()
        cur.execute(
            """SELECT a.* FROM assignments a
               JOIN categories c ON a.category_id = c.id
               WHERE c.class_id=? ORDER BY a.due_date, a.name""",
            (class_id,)
        )
        return [Assignment(id=r["id"], category_id=r["category_id"], name=r["name"],
                           total_points=r["total_points"], due_date=r["due_date"],
                           description=r["description"])
                for r in cur.fetchall()]

    def get_assignment(self, assignment_id: int) -> Optional[Assignment]:
        """Return a single assignment."""
        cur = self._cursor()
        cur.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,))
        r = cur.fetchone()
        if r:
            return Assignment(id=r["id"], category_id=r["category_id"], name=r["name"],
                              total_points=r["total_points"], due_date=r["due_date"],
                              description=r["description"])
        return None

    def update_assignment(self, assignment_id: int, **kwargs: Any) -> None:
        """Update assignment fields."""
        fields = ", ".join(f"{k}=?" for k in kwargs)
        cur = self._cursor()
        cur.execute(f"UPDATE assignments SET {fields} WHERE id=?",
                    (*kwargs.values(), assignment_id))
        self._conn.commit()  # type: ignore[union-attr]

    def delete_assignment(self, assignment_id: int) -> None:
        """Delete an assignment and its grades."""
        cur = self._cursor()
        cur.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))
        self._conn.commit()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    #  Grades                                                              #
    # ------------------------------------------------------------------ #

    def upsert_grade(self, assignment_id: int, student_id: int,
                     points_earned: Optional[float], status: str = "graded") -> Grade:
        """Insert or update a grade record."""
        submitted_at = datetime.now().isoformat()
        cur = self._cursor()
        cur.execute(
            """INSERT INTO grades (assignment_id, student_id, points_earned, status, submitted_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(assignment_id, student_id) DO UPDATE SET
                   points_earned=excluded.points_earned,
                   status=excluded.status,
                   submitted_at=excluded.submitted_at""",
            (assignment_id, student_id, points_earned, status, submitted_at)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return Grade(id=cur.lastrowid, assignment_id=assignment_id,
                     student_id=student_id, points_earned=points_earned,
                     status=status, submitted_at=submitted_at)

    def get_grade(self, assignment_id: int, student_id: int) -> Optional[Grade]:
        """Return a single grade, or None."""
        cur = self._cursor()
        cur.execute(
            "SELECT * FROM grades WHERE assignment_id=? AND student_id=?",
            (assignment_id, student_id)
        )
        r = cur.fetchone()
        if r:
            return Grade(id=r["id"], assignment_id=r["assignment_id"],
                         student_id=r["student_id"],
                         points_earned=r["points_earned"],
                         status=r["status"], submitted_at=r["submitted_at"])
        return None

    def get_grades_for_student(self, student_id: int) -> List[Grade]:
        """Return all grades for a student."""
        cur = self._cursor()
        cur.execute("SELECT * FROM grades WHERE student_id=?", (student_id,))
        return [Grade(id=r["id"], assignment_id=r["assignment_id"],
                      student_id=r["student_id"],
                      points_earned=r["points_earned"],
                      status=r["status"], submitted_at=r["submitted_at"])
                for r in cur.fetchall()]

    def get_grades_for_assignment(self, assignment_id: int) -> List[Grade]:
        """Return all grades for an assignment."""
        cur = self._cursor()
        cur.execute("SELECT * FROM grades WHERE assignment_id=?", (assignment_id,))
        return [Grade(id=r["id"], assignment_id=r["assignment_id"],
                      student_id=r["student_id"],
                      points_earned=r["points_earned"],
                      status=r["status"], submitted_at=r["submitted_at"])
                for r in cur.fetchall()]

    def delete_grade(self, assignment_id: int, student_id: int) -> None:
        """Remove a grade record."""
        cur = self._cursor()
        cur.execute(
            "DELETE FROM grades WHERE assignment_id=? AND student_id=?",
            (assignment_id, student_id)
        )
        self._conn.commit()  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    #  Attendance                                                          #
    # ------------------------------------------------------------------ #

    def upsert_attendance(self, class_id: int, student_id: int,
                          date: str, status: str = "present") -> Attendance:
        """Insert or update an attendance record."""
        cur = self._cursor()
        cur.execute(
            """INSERT INTO attendance (class_id, student_id, date, status)
               VALUES (?,?,?,?)
               ON CONFLICT(class_id, student_id, date) DO UPDATE SET status=excluded.status""",
            (class_id, student_id, date, status)
        )
        self._conn.commit()  # type: ignore[union-attr]
        return Attendance(id=cur.lastrowid, class_id=class_id,
                          student_id=student_id, date=date, status=status)

    def get_attendance_for_class(self, class_id: int,
                                 date: Optional[str] = None) -> List[Attendance]:
        """Return attendance records for a class, optionally filtered by date."""
        cur = self._cursor()
        if date:
            cur.execute(
                "SELECT * FROM attendance WHERE class_id=? AND date=? ORDER BY student_id",
                (class_id, date)
            )
        else:
            cur.execute(
                "SELECT * FROM attendance WHERE class_id=? ORDER BY date, student_id",
                (class_id,)
            )
        return [Attendance(id=r["id"], class_id=r["class_id"],
                           student_id=r["student_id"], date=r["date"],
                           status=r["status"])
                for r in cur.fetchall()]

    def get_attendance_for_student(self, student_id: int) -> List[Attendance]:
        """Return all attendance records for a student."""
        cur = self._cursor()
        cur.execute(
            "SELECT * FROM attendance WHERE student_id=? ORDER BY date",
            (student_id,)
        )
        return [Attendance(id=r["id"], class_id=r["class_id"],
                           student_id=r["student_id"], date=r["date"],
                           status=r["status"])
                for r in cur.fetchall()]

    # ------------------------------------------------------------------ #
    #  Grade Calculations                                                  #
    # ------------------------------------------------------------------ #

    def calculate_student_grade(self, student_id: int, class_id: int) -> Dict[str, Any]:
        """
        Calculate the weighted grade for a student in a class.

        Returns a dict with:
          weighted_percent, category_scores, letter_grade (if scale present)
        """
        categories = self.get_categories_for_class(class_id)
        if not categories:
            return {"weighted_percent": 0.0, "category_scores": {}}

        total_weight_used = 0.0
        weighted_sum = 0.0
        category_scores: Dict[str, Dict] = {}

        for cat in categories:
            assignments = self.get_assignments_for_category(cat.id)  # type: ignore[arg-type]
            if not assignments:
                continue

            scores: List[float] = []
            for asgn in assignments:
                grade = self.get_grade(asgn.id, student_id)  # type: ignore[arg-type]
                if grade and grade.status not in ("excused", "missing") \
                        and grade.points_earned is not None and asgn.total_points > 0:
                    scores.append(grade.points_earned / asgn.total_points * 100)

            if not scores:
                continue

            # Apply drop-lowest
            dl = cat.drop_lowest
            if dl > 0 and len(scores) > dl:
                scores = sorted(scores)[dl:]

            cat_avg = sum(scores) / len(scores)
            weighted_sum += cat_avg * (cat.weight / 100)
            total_weight_used += cat.weight / 100

            category_scores[cat.name] = {
                "average": cat_avg,
                "weight": cat.weight,
                "count": len(scores),
            }

        if total_weight_used == 0:
            weighted_percent = 0.0
        else:
            weighted_percent = weighted_sum / total_weight_used

        return {
            "weighted_percent": weighted_percent,
            "category_scores": category_scores,
        }

    def get_class_statistics(self, class_id: int) -> Dict[str, Any]:
        """
        Compute aggregate statistics for a class.

        Returns average, median, high, low, count, grade_distribution.
        """
        students = self.get_students_for_class(class_id)
        if not students:
            return {
                "average": 0.0, "median": 0.0,
                "high": 0.0, "low": 0.0,
                "count": 0, "grade_distribution": {}
            }

        class_obj = self.get_class(class_id)
        thresholds: List[GradeThreshold] = []
        if class_obj and class_obj.grade_scale_id:
            thresholds = self.get_thresholds_for_scale(class_obj.grade_scale_id)

        percents: List[float] = []
        letter_counts: Dict[str, int] = {}

        for student in students:
            result = self.calculate_student_grade(student.id, class_id)  # type: ignore[arg-type]
            pct = result["weighted_percent"]
            percents.append(pct)

            if thresholds:
                from .utils import calculate_letter_grade
                letter = calculate_letter_grade(pct, thresholds)
                letter_counts[letter] = letter_counts.get(letter, 0) + 1

        if not percents:
            return {
                "average": 0.0, "median": 0.0,
                "high": 0.0, "low": 0.0,
                "count": 0, "grade_distribution": {}
            }

        sorted_p = sorted(percents)
        n = len(sorted_p)
        median = (sorted_p[n // 2 - 1] + sorted_p[n // 2]) / 2 if n % 2 == 0 \
            else sorted_p[n // 2]

        return {
            "average": sum(percents) / n,
            "median": median,
            "high": max(percents),
            "low": min(percents),
            "count": n,
            "grade_distribution": letter_counts,
        }

    # ------------------------------------------------------------------ #
    #  Backup / Restore                                                    #
    # ------------------------------------------------------------------ #

    def backup_database(self, dest_path: str) -> bool:
        """Copy the database file to dest_path."""
        try:
            import shutil
            shutil.copy2(self.db_path, dest_path)
            return True
        except Exception:
            return False

    def restore_database(self, src_path: str) -> bool:
        """Replace the current database with the file at src_path."""
        try:
            import shutil
            self.close()
            shutil.copy2(src_path, self.db_path)
            self._connect()
            self._create_tables()
            return True
        except Exception:
            return False
