"""All application screens for GradeBook Pro."""

import curses
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .widgets import (
    safe_addstr, draw_box, fill_background,
    NavBar, StatusBar, Menu, Form, FormField,
    Dialog, Table, ProgressBar, SearchBox,
)
from .theme import ThemeManager

if TYPE_CHECKING:
    from gradebook.app import GradebookApp


# ──────────────────────────────────────────────────────────────────────────────
#  Base Screen
# ──────────────────────────────────────────────────────────────────────────────

class BaseScreen:
    """Base class for all screens."""

    def __init__(self, app: "GradebookApp"):
        self.app = app
        self.win = app.stdscr
        self.theme = app.theme
        self.db = app.db
        self.auth = app.auth
        self._status_msg = ""
        self._status_err = False

    # helpers ----------------------------------------------------------------

    @property
    def h(self) -> int:
        return self.win.getmaxyx()[0]

    @property
    def w(self) -> int:
        return self.win.getmaxyx()[1]

    def set_status(self, msg: str, error: bool = False) -> None:
        self._status_msg = msg
        self._status_err = error

    def _draw_nav(self, crumbs: List[str]) -> None:
        nav = NavBar(self.win, self.theme)
        nav.set_breadcrumbs(crumbs)
        nav.draw()

    def _draw_status(self, hints: str = "") -> None:
        sb = StatusBar(self.win, self.theme)
        sb.set_message(self._status_msg, self._status_err)
        sb.draw(hints)

    def _confirm(self, title: str, message: str) -> bool:
        dlg = Dialog(self.win, self.theme, title, message, "confirm")
        result = dlg.run()
        return bool(result)

    def _info(self, title: str, message: str) -> None:
        dlg = Dialog(self.win, self.theme, title, message, "info")
        dlg.run()
        self.win.getch()

    def _input_dialog(self, title: str, message: str,
                      default: str = "") -> Optional[str]:
        dlg = Dialog(self.win, self.theme, title, message, "input", default)
        return dlg.run()

    def run(self) -> Optional[str]:
        """Run the screen; return a navigation string or None."""
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────────────────────
#  Login Screen
# ──────────────────────────────────────────────────────────────────────────────

class LoginScreen(BaseScreen):
    """Login form screen."""

    def run(self) -> Optional[str]:
        fields = [
            FormField("username", "Username", required=True),
            FormField("password", "Password", required=True, secret=True),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 4, x=self.w // 2 - 22, w=44)

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Login"])

            # Title
            title = "─── Login ───"
            safe_addstr(self.win, self.h // 2 - 6,
                        (self.w - len(title)) // 2,
                        title, self.theme.title() | curses.A_BOLD)

            draw_box(self.win, self.h // 2 - 5, self.w // 2 - 24,
                     10, 48, attr=self.theme.border())
            form.draw()

            hint = "[Tab] Next field  [Enter] Login  [R] Register  [Q] Quit"
            self._draw_status(hint)
            self.win.refresh()

            key = self.win.getch()
            if key in (ord("q"), ord("Q")):
                return "quit"
            if key in (ord("r"), ord("R")):
                return "register"

            done = form.handle_key(key)
            if form.cancelled:
                return "quit"
            if form.submitted:
                vals = form.get_values()
                user = self.auth.login(vals["username"], vals["password"])
                if user:
                    return "dashboard"
                else:
                    self.set_status("Invalid username or password.", error=True)
                    form.submitted = False
                    for f in fields:
                        f.value = ""
                        f.cursor_pos = 0


# ──────────────────────────────────────────────────────────────────────────────
#  Register Screen
# ──────────────────────────────────────────────────────────────────────────────

class RegisterScreen(BaseScreen):
    """User registration screen."""

    def run(self) -> Optional[str]:
        fields = [
            FormField("username", "Username", required=True),
            FormField("password", "Password", required=True, secret=True),
            FormField("confirm",  "Confirm",  required=True, secret=True),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 5, x=self.w // 2 - 22, w=44)

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Register"])

            title = "─── Create Account ───"
            safe_addstr(self.win, self.h // 2 - 7,
                        (self.w - len(title)) // 2,
                        title, self.theme.title() | curses.A_BOLD)

            draw_box(self.win, self.h // 2 - 6, self.w // 2 - 24,
                     12, 48, attr=self.theme.border())
            form.draw()

            self._draw_status("[Tab] Next  [Enter] Register  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            form.handle_key(key)
            if form.cancelled:
                return "login"
            if form.submitted:
                vals = form.get_values()
                if vals["password"] != vals["confirm"]:
                    self.set_status("Passwords do not match.", error=True)
                    form.submitted = False
                    continue
                user = self.auth.register_user(vals["username"], vals["password"])
                if user:
                    self.set_status(f"Account '{user.username}' created! Please log in.")
                    return "login"
                else:
                    self.set_status("Registration failed (username taken or too short).",
                                    error=True)
                    form.submitted = False


# ──────────────────────────────────────────────────────────────────────────────
#  Dashboard
# ──────────────────────────────────────────────────────────────────────────────

class DashboardScreen(BaseScreen):
    """Dashboard with class overview and quick stats."""

    def run(self) -> Optional[str]:
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            user = self.auth.current_user
            self._draw_nav(["GradeBook Pro", f"Dashboard ({user.username})"])

            classes = self.db.get_classes_for_user(user.id)

            title = f"Welcome, {user.username}!"
            safe_addstr(self.win, 2, (self.w - len(title)) // 2,
                        title, self.theme.title() | curses.A_BOLD)

            # Class summary table
            safe_addstr(self.win, 4, 2,
                        "Your Classes:", self.theme.header() | curses.A_BOLD)

            col_y = 5
            cols = [("Class Name", 28), ("Section", 10),
                    ("Semester", 12), ("Students", 9), ("Avg Grade", 10)]
            col_x = 2

            # header
            hdr = ""
            for name, cw in cols:
                hdr += f" {name[:cw-1]:<{cw-1}}"
            safe_addstr(self.win, col_y, col_x,
                        hdr[:self.w - 4], self.theme.header() | curses.A_BOLD)
            safe_addstr(self.win, col_y + 1, col_x,
                        "─" * min(self.w - 4, 74), self.theme.border())

            for i, cls in enumerate(classes[:self.h - 12]):
                row_y = col_y + 2 + i
                students = self.db.get_students_for_class(cls.id)
                stats = self.db.get_class_statistics(cls.id)
                row_data = [
                    cls.name, cls.section or "-",
                    f"{cls.semester} {cls.year}",
                    str(len(students)),
                    f"{stats['average']:.1f}%" if stats['count'] else "N/A",
                ]
                row_str = ""
                for j, (_, cw) in enumerate(cols):
                    cell = row_data[j] if j < len(row_data) else ""
                    row_str += f" {cell[:cw-1]:<{cw-1}}"
                safe_addstr(self.win, row_y, col_x,
                            row_str[:self.w - 4], self.theme.normal())

            if not classes:
                safe_addstr(self.win, col_y + 2, col_x,
                            "No classes yet. Press [C] to create one.",
                            self.theme.dim())

            # Menu
            menu_y = self.h - 8
            safe_addstr(self.win, menu_y, 2,
                        "─" * (self.w - 4), self.theme.border())
            options = [
                ("[C] Classes", "classes"),
                ("[G] GPA Calc", "gpa"),
                ("[S] Settings", "settings"),
                ("[H] Help", "help"),
                ("[L] Logout", "logout"),
                ("[Q] Quit", "quit"),
            ]
            ox = 2
            for label, _ in options:
                safe_addstr(self.win, menu_y + 1, ox,
                            label, self.theme.title() | curses.A_BOLD)
                ox += len(label) + 3

            self._draw_status("[C] Classes  [G] GPA  [S] Settings  [H] Help  [L] Logout  [Q] Quit")
            self.win.refresh()

            key = self.win.getch()
            if key in (ord("q"), ord("Q")):
                return "quit"
            elif key in (ord("l"), ord("L")):
                self.auth.logout()
                return "login"
            elif key in (ord("c"), ord("C")):
                return "classes"
            elif key in (ord("g"), ord("G")):
                return "gpa"
            elif key in (ord("s"), ord("S")):
                return "settings"
            elif key in (ord("h"), ord("H"), curses.KEY_F1):
                return "help"


# ──────────────────────────────────────────────────────────────────────────────
#  Class List Screen
# ──────────────────────────────────────────────────────────────────────────────

class ClassListScreen(BaseScreen):
    """List of all classes with CRUD actions."""

    def run(self) -> Optional[str]:
        user = self.auth.current_user
        search = SearchBox(self.win, self.theme, y=2, x=2, w=40)
        search.active = True

        while True:
            classes = self.db.get_classes_for_user(user.id)
            q = search.query.lower()
            filtered = [c for c in classes
                        if q in c.name.lower() or q in (c.section or "").lower()]

            items = [f"{c.name}  [{c.section}]  {c.semester} {c.year}"
                     for c in filtered]

            menu_h = max(1, self.h - 8)
            menu = Menu(self.win, self.theme, items, y=4, x=2,
                        h=menu_h, w=self.w - 4)

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes"])

            safe_addstr(self.win, 1, 2,
                        f"Classes ({len(filtered)} shown)",
                        self.theme.title() | curses.A_BOLD)
            search.draw()
            menu.draw()
            self._draw_status(
                "[Enter] Open  [A] Add  [E] Edit  [D] Delete  [/] Search  [Esc/B] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "dashboard"
            elif key in (ord("/"),):
                search.active = True
            elif key in (ord("a"), ord("A")):
                result = self._add_class(user.id)
                if result:
                    self.set_status(f"Class '{result.name}' created.")
            elif key in (ord("e"), ord("E")):
                if filtered:
                    cls = filtered[menu.selected]
                    self._edit_class(cls)
                    self.set_status("Class updated.")
            elif key in (ord("d"), ord("D")):
                if filtered:
                    cls = filtered[menu.selected]
                    if self._confirm("Delete Class",
                                     f"Delete '{cls.name}'? This removes all data."):
                        self.db.delete_class(cls.id)
                        self.set_status(f"Class '{cls.name}' deleted.")
            elif key == curses.KEY_F1 or key == ord("?"):
                return "help"
            elif search.active:
                changed = search.handle_key(key)
                if key == 27:
                    search.active = False
            else:
                idx = menu.handle_key(key)
                if idx is not None and filtered:
                    self.app.context["class_id"] = filtered[idx].id
                    return "class_detail"

    def _add_class(self, user_id: int):
        fields = [
            FormField("name",     "Class Name", required=True),
            FormField("section",  "Section"),
            FormField("semester", "Semester"),
            FormField("year",     "Year",
                      value=str(datetime.now().year)),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 5, x=self.w // 2 - 22, w=44)
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            draw_box(self.win, self.h // 2 - 7, self.w // 2 - 24,
                     14, 48, "Add Class", self.theme.border())
            form.draw()
            self._draw_status("[Tab] Next  [Enter] Save  [Esc] Cancel")
            self.win.refresh()
            key = self.win.getch()
            form.handle_key(key)
            if form.cancelled:
                return None
            if form.submitted:
                v = form.get_values()
                try:
                    year = int(v["year"]) if v["year"].strip() else datetime.now().year
                except ValueError:
                    year = datetime.now().year
                scales = self.db.get_scales_for_user(user_id)
                scale_id = scales[0].id if scales else None
                return self.db.create_class(
                    user_id, v["name"], v["section"],
                    v["semester"], year, scale_id)

    def _edit_class(self, cls):
        fields = [
            FormField("name",     "Class Name", value=cls.name,     required=True),
            FormField("section",  "Section",    value=cls.section),
            FormField("semester", "Semester",   value=cls.semester),
            FormField("year",     "Year",       value=str(cls.year)),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 5, x=self.w // 2 - 22, w=44)
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            draw_box(self.win, self.h // 2 - 7, self.w // 2 - 24,
                     14, 48, "Edit Class", self.theme.border())
            form.draw()
            self._draw_status("[Tab] Next  [Enter] Save  [Esc] Cancel")
            self.win.refresh()
            key = self.win.getch()
            form.handle_key(key)
            if form.cancelled:
                return
            if form.submitted:
                v = form.get_values()
                try:
                    year = int(v["year"])
                except ValueError:
                    year = cls.year
                self.db.update_class(
                    cls.id, name=v["name"], section=v["section"],
                    semester=v["semester"], year=year)
                return


# ──────────────────────────────────────────────────────────────────────────────
#  Class Detail Screen
# ──────────────────────────────────────────────────────────────────────────────

class ClassDetailScreen(BaseScreen):
    """Overview of a single class with sub-navigation."""

    def run(self) -> Optional[str]:
        class_id = self.app.context.get("class_id")
        if not class_id:
            return "classes"

        while True:
            cls = self.db.get_class(class_id)
            if not cls:
                return "classes"

            stats = self.db.get_class_statistics(class_id)
            students = self.db.get_students_for_class(class_id)
            categories = self.db.get_categories_for_class(class_id)

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes", cls.name])

            # Info panel
            safe_addstr(self.win, 2, 2,
                        f"Class: {cls.name}  [{cls.section}]  {cls.semester} {cls.year}",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2,
                        f"Students: {len(students)}   "
                        f"Avg: {stats['average']:.1f}%   "
                        f"High: {stats['high']:.1f}%   "
                        f"Low: {stats['low']:.1f}%",
                        self.theme.normal())

            # Category weight bar
            if categories:
                safe_addstr(self.win, 4, 2,
                            "Categories: " + "  ".join(
                                f"{c.name}({c.weight:.0f}%)" for c in categories
                            )[:self.w - 16],
                            self.theme.dim())

            # Menu
            menu_items = [
                "Students",
                "Assignments & Categories",
                "Grade Entry",
                "Attendance",
                "Reports",
                "Grade Scale",
            ]
            menu = Menu(self.win, self.theme, menu_items,
                        y=6, x=4, h=len(menu_items), w=36)

            safe_addstr(self.win, 5, 2, "─" * (self.w - 4), self.theme.border())
            menu.draw()
            safe_addstr(self.win, 6 + len(menu_items), 2,
                        "─" * (self.w - 4), self.theme.border())

            self._draw_status("[Enter] Select  [Esc/B] Back  [R] Reports")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "classes"
            elif key in (ord("r"), ord("R")):
                return "reports"
            elif key == curses.KEY_F1:
                return "help"

            idx = menu.handle_key(key)
            if idx is not None:
                if idx == 0:
                    return "students"
                elif idx == 1:
                    return "categories"
                elif idx == 2:
                    return "grade_entry"
                elif idx == 3:
                    return "attendance"
                elif idx == 4:
                    return "reports"
                elif idx == 5:
                    return "grade_scale"


# ──────────────────────────────────────────────────────────────────────────────
#  Category Screen
# ──────────────────────────────────────────────────────────────────────────────

class CategoryScreen(BaseScreen):
    """Manage weighted categories and their assignments."""

    def run(self) -> Optional[str]:
        class_id = self.app.context.get("class_id")
        if not class_id:
            return "classes"

        while True:
            cls = self.db.get_class(class_id)
            categories = self.db.get_categories_for_class(class_id)
            total_w = sum(c.weight for c in categories)

            items = [
                f"{c.name:<22} {c.weight:5.1f}%  drop-lowest:{c.drop_lowest}"
                for c in categories
            ]
            menu = Menu(self.win, self.theme, items,
                        y=5, x=2, h=max(1, self.h - 10), w=self.w - 4)

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes",
                            cls.name if cls else "?", "Categories"])

            safe_addstr(self.win, 2, 2,
                        f"Categories for: {cls.name if cls else '?'}",
                        self.theme.title() | curses.A_BOLD)

            color = self.theme.success() if abs(total_w - 100) < 0.01 else self.theme.warning()
            safe_addstr(self.win, 3, 2,
                        f"Total weight: {total_w:.1f}%  "
                        f"{'✓ OK' if abs(total_w - 100) < 0.01 else '⚠ Should sum to 100%'}",
                        color)

            safe_addstr(self.win, 4, 2, "─" * (self.w - 4), self.theme.border())
            menu.draw()
            self._draw_status(
                "[A] Add  [E] Edit  [D] Delete  [V] View Assignments  [Esc/B] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "class_detail"
            elif key in (ord("a"), ord("A")):
                self._add_category(class_id)
            elif key in (ord("e"), ord("E")):
                if categories:
                    self._edit_category(categories[menu.selected])
            elif key in (ord("d"), ord("D")):
                if categories:
                    cat = categories[menu.selected]
                    if self._confirm("Delete Category",
                                     f"Delete '{cat.name}' and ALL its assignments?"):
                        self.db.delete_category(cat.id)
                        self.set_status(f"Category '{cat.name}' deleted.")
            elif key in (ord("v"), ord("V")):
                if categories:
                    self.app.context["category_id"] = categories[menu.selected].id
                    return "assignments"
            else:
                menu.handle_key(key)

    def _category_form(self, title: str, name: str = "",
                       weight: str = "", drop: str = "0"):
        fields = [
            FormField("name",   "Category Name", value=name,   required=True),
            FormField("weight", "Weight (%)",     value=weight, required=True),
            FormField("drop",   "Drop Lowest",    value=drop),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 4, x=self.w // 2 - 20, w=40)
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            draw_box(self.win, self.h // 2 - 6, self.w // 2 - 22,
                     12, 44, title, self.theme.border())
            form.draw()
            self._draw_status("[Tab] Next  [Enter] Save  [Esc] Cancel")
            self.win.refresh()
            key = self.win.getch()
            form.handle_key(key)
            if form.cancelled:
                return None
            if form.submitted:
                v = form.get_values()
                try:
                    weight_val = float(v["weight"])
                    drop_val   = int(v["drop"]) if v["drop"].strip() else 0
                    return v["name"], weight_val, drop_val
                except ValueError:
                    self.set_status("Weight must be a number.", error=True)
                    form.submitted = False

    def _add_category(self, class_id: int) -> None:
        result = self._category_form("Add Category")
        if result:
            name, weight, drop = result
            self.db.create_category(class_id, name, weight, drop)
            self.set_status(f"Category '{name}' added.")

    def _edit_category(self, cat) -> None:
        result = self._category_form(
            "Edit Category", cat.name, str(cat.weight), str(cat.drop_lowest))
        if result:
            name, weight, drop = result
            self.db.update_category(cat.id, name=name, weight=weight, drop_lowest=drop)
            self.set_status("Category updated.")


# ──────────────────────────────────────────────────────────────────────────────
#  Student List Screen
# ──────────────────────────────────────────────────────────────────────────────

class StudentListScreen(BaseScreen):
    """List and manage students in a class."""

    def run(self) -> Optional[str]:
        class_id = self.app.context.get("class_id")
        if not class_id:
            return "classes"

        search = SearchBox(self.win, self.theme, y=3, x=2, w=40)

        while True:
            cls = self.db.get_class(class_id)
            all_students = self.db.get_students_for_class(class_id)
            q = search.query.lower()
            students = [s for s in all_students
                        if q in s.name.lower() or q in (s.student_id or "").lower()]

            items = [f"{s.name:<25} {s.student_id:<12} {s.email}"
                     for s in students]
            menu = Menu(self.win, self.theme, items,
                        y=5, x=2, h=max(1, self.h - 9), w=self.w - 4)

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes",
                            cls.name if cls else "?", "Students"])

            safe_addstr(self.win, 2, 2,
                        f"Students in {cls.name if cls else '?'} ({len(students)} shown)",
                        self.theme.title() | curses.A_BOLD)
            search.draw()
            safe_addstr(self.win, 4, 2, "─" * (self.w - 4), self.theme.border())
            menu.draw()
            self._draw_status(
                "[Enter] Detail  [A] Add  [E] Edit  [D] Delete  [/] Search  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "class_detail"
            elif key == ord("/"):
                search.active = True
            elif key in (ord("a"), ord("A")):
                self._add_student(class_id)
            elif key in (ord("e"), ord("E")):
                if students:
                    self._edit_student(students[menu.selected])
            elif key in (ord("d"), ord("D")):
                if students:
                    s = students[menu.selected]
                    if self._confirm("Remove Student",
                                     f"Remove '{s.name}' and all their grades?"):
                        self.db.delete_student(s.id)
                        self.set_status(f"Student '{s.name}' removed.")
            elif search.active:
                search.handle_key(key)
                if key == 27:
                    search.active = False
            else:
                idx = menu.handle_key(key)
                if idx is not None and students:
                    self.app.context["student_id"] = students[idx].id
                    return "student_detail"

    def _student_form(self, title: str, name: str = "",
                      sid: str = "", email: str = ""):
        fields = [
            FormField("name",  "Full Name",  value=name,  required=True),
            FormField("sid",   "Student ID", value=sid),
            FormField("email", "Email",      value=email),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 4, x=self.w // 2 - 22, w=44)
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            draw_box(self.win, self.h // 2 - 6, self.w // 2 - 24,
                     12, 48, title, self.theme.border())
            form.draw()
            self._draw_status("[Tab] Next  [Enter] Save  [Esc] Cancel")
            self.win.refresh()
            key = self.win.getch()
            form.handle_key(key)
            if form.cancelled:
                return None
            if form.submitted:
                return form.get_values()

    def _add_student(self, class_id: int) -> None:
        vals = self._student_form("Add Student")
        if vals:
            self.db.create_student(class_id, vals["name"],
                                   vals["sid"], vals["email"])
            self.set_status(f"Student '{vals['name']}' added.")

    def _edit_student(self, student) -> None:
        vals = self._student_form("Edit Student",
                                  student.name, student.student_id, student.email)
        if vals:
            self.db.update_student(student.id, name=vals["name"],
                                   student_id=vals["sid"], email=vals["email"])
            self.set_status("Student updated.")


# ──────────────────────────────────────────────────────────────────────────────
#  Student Detail Screen
# ──────────────────────────────────────────────────────────────────────────────

class StudentDetailScreen(BaseScreen):
    """Shows grade breakdown for a single student."""

    def run(self) -> Optional[str]:
        student_id = self.app.context.get("student_id")
        class_id   = self.app.context.get("class_id")
        if not student_id or not class_id:
            return "students"

        while True:
            student = self.db.get_student(student_id)
            cls     = self.db.get_class(class_id)
            if not student or not cls:
                return "students"

            result  = self.db.calculate_student_grade(student_id, class_id)
            pct     = result["weighted_percent"]
            thresholds = []
            if cls.grade_scale_id:
                thresholds = self.db.get_thresholds_for_scale(cls.grade_scale_id)
            from gradebook.utils import calculate_letter_grade
            letter = calculate_letter_grade(pct, thresholds) if thresholds else "N/A"

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes",
                            cls.name, "Students", student.name])

            safe_addstr(self.win, 2, 2,
                        f"{student.name}  [{student.student_id}]  {student.email}",
                        self.theme.title() | curses.A_BOLD)

            grade_color = (self.theme.success() if pct >= 70
                           else self.theme.danger())
            safe_addstr(self.win, 3, 2,
                        f"Overall: {pct:.1f}%  ({letter})",
                        grade_color | curses.A_BOLD)

            row = 5
            safe_addstr(self.win, row, 2,
                        "CATEGORY BREAKDOWN", self.theme.header() | curses.A_BOLD)
            row += 1

            for cat_name, info in result["category_scores"].items():
                bar = ProgressBar(self.win, self.theme, row, 4, 30)
                bar.draw(info["average"], 100.0)
                safe_addstr(self.win, row, 36,
                            f"{cat_name:<18}  {info['average']:.1f}%  wt:{info['weight']:.0f}%",
                            self.theme.normal())
                row += 1

            row += 1
            safe_addstr(self.win, row, 2,
                        "ASSIGNMENTS", self.theme.header() | curses.A_BOLD)
            row += 1

            categories = self.db.get_categories_for_class(class_id)
            for cat in categories:
                if row >= self.h - 3:
                    break
                safe_addstr(self.win, row, 2,
                            f"[{cat.name}]", self.theme.title())
                row += 1
                assignments = self.db.get_assignments_for_category(cat.id)
                for asgn in assignments:
                    if row >= self.h - 3:
                        break
                    grade = self.db.get_grade(asgn.id, student_id)
                    if grade and grade.status == "excused":
                        score = "Excused"
                    elif grade and grade.points_earned is not None:
                        score = (f"{grade.points_earned:.1f}/{asgn.total_points:.0f}"
                                 f" ({grade.points_earned/asgn.total_points*100:.1f}%)")
                    else:
                        score = "Not graded"
                    safe_addstr(self.win, row, 4,
                                f"{asgn.name:<30}  {score}",
                                self.theme.normal())
                    row += 1

            self._draw_status("[R] Report  [Esc/B] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "students"
            elif key in (ord("r"), ord("R")):
                return "reports"


# ──────────────────────────────────────────────────────────────────────────────
#  Assignment Screen
# ──────────────────────────────────────────────────────────────────────────────

class AssignmentScreen(BaseScreen):
    """List and manage assignments for a category."""

    def run(self) -> Optional[str]:
        class_id    = self.app.context.get("class_id")
        category_id = self.app.context.get("category_id")
        if not category_id or not class_id:
            return "categories"

        while True:
            cat   = self.db.get_category(category_id)
            cls   = self.db.get_class(class_id)
            asgns = self.db.get_assignments_for_category(category_id)

            items = [
                f"{a.name:<28} {a.total_points:6.1f}pts  {a.due_date}"
                for a in asgns
            ]
            menu = Menu(self.win, self.theme, items,
                        y=5, x=2, h=max(1, self.h - 9), w=self.w - 4)

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes",
                            cls.name if cls else "?",
                            cat.name if cat else "?", "Assignments"])

            safe_addstr(self.win, 2, 2,
                        f"Assignments: {cat.name if cat else '?'} "
                        f"(weight {cat.weight:.1f}%)" if cat else "?",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2,
                        f"Drop lowest: {cat.drop_lowest}" if cat else "",
                        self.theme.dim())
            safe_addstr(self.win, 4, 2, "─" * (self.w - 4), self.theme.border())
            menu.draw()
            self._draw_status("[A] Add  [E] Edit  [D] Delete  [G] Grades  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "categories"
            elif key in (ord("a"), ord("A")):
                self._add_assignment(category_id)
            elif key in (ord("e"), ord("E")):
                if asgns:
                    self._edit_assignment(asgns[menu.selected])
            elif key in (ord("d"), ord("D")):
                if asgns:
                    a = asgns[menu.selected]
                    if self._confirm("Delete Assignment",
                                     f"Delete '{a.name}' and all grades?"):
                        self.db.delete_assignment(a.id)
                        self.set_status(f"'{a.name}' deleted.")
            elif key in (ord("g"), ord("G")):
                if asgns:
                    self.app.context["assignment_id"] = asgns[menu.selected].id
                    return "grade_entry"
            else:
                menu.handle_key(key)

    def _assignment_form(self, title: str, name: str = "",
                         pts: str = "100", due: str = "", desc: str = ""):
        fields = [
            FormField("name", "Assignment", value=name, required=True),
            FormField("pts",  "Max Points", value=pts,  required=True),
            FormField("due",  "Due Date",   value=due),
            FormField("desc", "Description", value=desc),
        ]
        form = Form(self.win, self.theme, fields,
                    y=self.h // 2 - 5, x=self.w // 2 - 22, w=44)
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            draw_box(self.win, self.h // 2 - 7, self.w // 2 - 24,
                     14, 48, title, self.theme.border())
            form.draw()
            self._draw_status("[Tab] Next  [Enter] Save  [Esc] Cancel")
            self.win.refresh()
            key = self.win.getch()
            form.handle_key(key)
            if form.cancelled:
                return None
            if form.submitted:
                v = form.get_values()
                try:
                    pts_val = float(v["pts"])
                    return v["name"], pts_val, v["due"], v["desc"]
                except ValueError:
                    self.set_status("Points must be a number.", error=True)
                    form.submitted = False

    def _add_assignment(self, cat_id: int) -> None:
        result = self._assignment_form("Add Assignment")
        if result:
            name, pts, due, desc = result
            self.db.create_assignment(cat_id, name, pts, due, desc)
            self.set_status(f"Assignment '{name}' added.")

    def _edit_assignment(self, asgn) -> None:
        result = self._assignment_form(
            "Edit Assignment", asgn.name, str(asgn.total_points),
            asgn.due_date, asgn.description)
        if result:
            name, pts, due, desc = result
            self.db.update_assignment(
                asgn.id, name=name, total_points=pts,
                due_date=due, description=desc)
            self.set_status("Assignment updated.")


# ──────────────────────────────────────────────────────────────────────────────
#  Grade Entry Screen
# ──────────────────────────────────────────────────────────────────────────────

class GradeEntryScreen(BaseScreen):
    """
    Quick grade entry for all students on a single assignment,
    or browse all assignments in a class.
    """

    def run(self) -> Optional[str]:
        class_id      = self.app.context.get("class_id")
        assignment_id = self.app.context.get("assignment_id")
        if not class_id:
            return "class_detail"

        # If no assignment specified, let user pick one
        if not assignment_id:
            asgns = self.db.get_assignments_for_class(class_id)
            if not asgns:
                self._info("No Assignments",
                           "No assignments in this class. Add some first.")
                return "class_detail"
            items = [f"{a.name}" for a in asgns]
            menu = Menu(self.win, self.theme, items,
                        y=4, x=2, h=max(1, self.h - 8), w=self.w - 4)
            while True:
                self.win.erase()
                fill_background(self.win, self.theme.normal())
                self._draw_nav(["GradeBook Pro", "Grade Entry – Pick Assignment"])
                safe_addstr(self.win, 2, 2, "Select an assignment:",
                            self.theme.title() | curses.A_BOLD)
                safe_addstr(self.win, 3, 2, "─" * (self.w - 4), self.theme.border())
                menu.draw()
                self._draw_status("[Enter] Select  [Esc] Back")
                self.win.refresh()
                key = self.win.getch()
                if key == 27:
                    return "class_detail"
                idx = menu.handle_key(key)
                if idx is not None:
                    assignment_id = asgns[idx].id
                    self.app.context["assignment_id"] = assignment_id
                    break

        return self._grade_assignment(class_id, assignment_id)

    def _grade_assignment(self, class_id: int,
                          assignment_id: int) -> Optional[str]:
        asgn     = self.db.get_assignment(assignment_id)
        students = self.db.get_students_for_class(class_id)
        cls      = self.db.get_class(class_id)
        if not asgn or not cls:
            return "class_detail"

        sel = 0
        statuses = ["graded", "excused", "missing", "late"]

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes", cls.name,
                            "Grade Entry", asgn.name])

            safe_addstr(self.win, 2, 2,
                        f"Assignment: {asgn.name}  ({asgn.total_points:.0f} pts)",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2, "─" * (self.w - 4), self.theme.border())

            hdr = f" {'Name':<26} {'Points':>8} {'/ Max':>6} {'%':>7} {'Status':<10}"
            safe_addstr(self.win, 4, 2,
                        hdr[:self.w - 4], self.theme.header() | curses.A_BOLD)

            visible = self.h - 9
            offset  = max(0, sel - visible // 2)

            for i in range(visible):
                idx = offset + i
                if idx >= len(students):
                    break
                s     = students[idx]
                grade = self.db.get_grade(asgn.id, s.id)
                if grade and grade.status == "excused":
                    pts_str = "Excused"
                    pct_str = "  N/A"
                elif grade and grade.points_earned is not None:
                    pts_str = f"{grade.points_earned:.1f}"
                    pct_str = f"{grade.points_earned/asgn.total_points*100:.1f}%"
                else:
                    pts_str = "---"
                    pct_str = "  ---"
                status_str = (grade.status if grade else "pending")
                row_str = (f" {s.name:<26} {pts_str:>8} {asgn.total_points:>6.0f}"
                           f" {pct_str:>7} {status_str:<10}")
                attr = (self.theme.selected() | curses.A_BOLD
                        if idx == sel else self.theme.normal())
                safe_addstr(self.win, 5 + i, 2, row_str[:self.w - 4], attr)

            self._draw_status(
                "[↑↓] Navigate  [Enter/G] Grade  [E] Excused  [M] Missing  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "class_detail"
            elif key == curses.KEY_UP and sel > 0:
                sel -= 1
            elif key == curses.KEY_DOWN and sel < len(students) - 1:
                sel += 1
            elif key in (10, 13, ord("g"), ord("G")):
                if students:
                    s = students[sel]
                    grade = self.db.get_grade(asgn.id, s.id)
                    curr  = str(grade.points_earned) if (grade and grade.points_earned is not None) else ""
                    val   = self._input_dialog(
                        "Enter Grade",
                        f"Points for {s.name} (max {asgn.total_points:.0f}):",
                        curr)
                    if val is not None:
                        try:
                            pts = float(val)
                            pts = max(0.0, min(pts, asgn.total_points))
                            self.db.upsert_grade(asgn.id, s.id, pts, "graded")
                        except ValueError:
                            self.set_status("Invalid number.", error=True)
            elif key in (ord("e"), ord("E")):
                if students:
                    self.db.upsert_grade(asgn.id, students[sel].id, None, "excused")
            elif key in (ord("m"), ord("M")):
                if students:
                    self.db.upsert_grade(asgn.id, students[sel].id, None, "missing")


# ──────────────────────────────────────────────────────────────────────────────
#  Report Screen
# ──────────────────────────────────────────────────────────────────────────────

class ReportScreen(BaseScreen):
    """Generate and view / export reports."""

    def run(self) -> Optional[str]:
        from gradebook.reports import ReportGenerator
        class_id   = self.app.context.get("class_id")
        student_id = self.app.context.get("student_id")
        cls        = self.db.get_class(class_id) if class_id else None
        rg         = ReportGenerator(self.db)

        options = ["Class Roster", "Statistics Summary",
                   "Grade Distribution", "Student Report Card",
                   "Export Report to File"]
        menu = Menu(self.win, self.theme, options,
                    y=4, x=2, h=len(options), w=36)
        content = ""

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Reports"])

            safe_addstr(self.win, 2, 2,
                        f"Reports: {cls.name if cls else 'All'}",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2, "─" * (self.w - 4), self.theme.border())
            menu.draw()

            if content:
                # Show preview in right panel
                lines = content.splitlines()
                px = 42
                for i, ln in enumerate(lines[:self.h - 5]):
                    safe_addstr(self.win, 4 + i, px,
                                ln[:self.w - px - 2], self.theme.dim())

            self._draw_status("[Enter] Generate  [X] Export  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "class_detail" if class_id else "dashboard"
            elif key in (ord("x"), ord("X")):
                if content:
                    fname = self._input_dialog("Export", "Filename:", "report.txt")
                    if fname:
                        if rg.export_to_file(content, fname):
                            self.set_status(f"Exported to {fname}")
                        else:
                            self.set_status("Export failed.", error=True)
            else:
                idx = menu.handle_key(key)
                if idx is not None:
                    if idx == 0 and class_id:
                        content = rg.generate_class_roster(class_id)
                    elif idx == 1 and class_id:
                        content = rg.generate_statistics(class_id)
                    elif idx == 2 and class_id:
                        content = rg.generate_distribution_histogram(class_id)
                    elif idx == 3:
                        sid = student_id
                        if not sid and class_id:
                            students = self.db.get_students_for_class(class_id)
                            if students:
                                sid = students[0].id
                        if sid:
                            content = rg.generate_student_report(sid)
                        else:
                            self.set_status("No student selected.", error=True)
                    elif idx == 4:
                        if content:
                            fname = self._input_dialog("Export", "Filename:", "report.txt")
                            if fname:
                                if rg.export_to_file(content, fname):
                                    self.set_status(f"Exported to {fname}")
                                else:
                                    self.set_status("Export failed.", error=True)


# ──────────────────────────────────────────────────────────────────────────────
#  Attendance Screen
# ──────────────────────────────────────────────────────────────────────────────

class AttendanceScreen(BaseScreen):
    """Take / view attendance for a class on a given date."""

    STATUSES = ["present", "absent", "late", "excused"]

    def run(self) -> Optional[str]:
        class_id = self.app.context.get("class_id")
        if not class_id:
            return "class_detail"

        cls      = self.db.get_class(class_id)
        date_str = datetime.now().strftime("%Y-%m-%d")
        sel      = 0

        while True:
            students = self.db.get_students_for_class(class_id)
            records  = {
                r.student_id: r
                for r in self.db.get_attendance_for_class(class_id, date_str)
            }

            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes",
                            cls.name if cls else "?", "Attendance"])

            safe_addstr(self.win, 2, 2,
                        f"Attendance: {cls.name if cls else '?'}  Date: {date_str}",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2,
                        "[D] Change Date  [↑↓] Navigate  "
                        "[P]resent  [A]bsent  [L]ate  [E]xcused  [Esc] Back",
                        self.theme.dim())
            safe_addstr(self.win, 4, 2, "─" * (self.w - 4), self.theme.border())

            visible = self.h - 8
            offset  = max(0, sel - visible // 2)

            for i in range(visible):
                idx = offset + i
                if idx >= len(students):
                    break
                s      = students[idx]
                rec    = records.get(s.id)
                status = rec.status if rec else "---"
                color  = {
                    "present": self.theme.success(),
                    "absent":  self.theme.danger(),
                    "late":    self.theme.warning(),
                    "excused": self.theme.dim(),
                }.get(status, self.theme.normal())
                attr = (self.theme.selected() | curses.A_BOLD
                        if idx == sel else color)
                safe_addstr(self.win, 5 + i, 2,
                            f" {s.name:<30} {status:<10}", attr)

            # Summary
            present = sum(1 for r in records.values() if r.status == "present")
            absent  = sum(1 for r in records.values() if r.status == "absent")
            safe_addstr(self.win, self.h - 3, 2,
                        f"Present: {present}  Absent: {absent}  "
                        f"Total: {len(students)}",
                        self.theme.normal())

            self._draw_status("[P/A/L/E] Set status  [D] Date  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "class_detail"
            elif key == curses.KEY_UP and sel > 0:
                sel -= 1
            elif key == curses.KEY_DOWN and sel < len(students) - 1:
                sel += 1
            elif key in (ord("p"), ord("P")):
                if students:
                    self.db.upsert_attendance(
                        class_id, students[sel].id, date_str, "present")
            elif key in (ord("a"), ord("A")):
                if students:
                    self.db.upsert_attendance(
                        class_id, students[sel].id, date_str, "absent")
            elif key in (ord("l"), ord("L")):
                if students:
                    self.db.upsert_attendance(
                        class_id, students[sel].id, date_str, "late")
            elif key in (ord("e"), ord("E")):
                if students:
                    self.db.upsert_attendance(
                        class_id, students[sel].id, date_str, "excused")
            elif key in (ord("d"), ord("D")):
                new_date = self._input_dialog(
                    "Change Date", "Enter date (YYYY-MM-DD):", date_str)
                if new_date:
                    date_str = new_date.strip()


# ──────────────────────────────────────────────────────────────────────────────
#  GPA Calculator Screen
# ──────────────────────────────────────────────────────────────────────────────

class GPAScreen(BaseScreen):
    """Simple GPA calculator."""

    def run(self) -> Optional[str]:
        from gradebook.utils import calculate_gpa, gpa_points
        entries: List[Dict[str, str]] = []
        sel = 0
        LETTERS = ["A+", "A", "A-", "B+", "B", "B-",
                   "C+", "C", "C-", "D+", "D", "D-", "F"]

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "GPA Calculator"])

            safe_addstr(self.win, 2, 2, "GPA Calculator",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2,
                        "[A] Add Course  [D] Delete  [↑↓] Navigate  [Esc] Back",
                        self.theme.dim())
            safe_addstr(self.win, 4, 2, "─" * (self.w - 4), self.theme.border())

            hdr = f"  {'Course':<25} {'Grade':<8} {'Credits':<8} {'Points':<8}"
            safe_addstr(self.win, 5, 2,
                        hdr[:self.w - 4], self.theme.header() | curses.A_BOLD)

            for i, e in enumerate(entries):
                pts = gpa_points(e["grade"])
                row_str = (f"  {e['name']:<25} {e['grade']:<8}"
                           f" {e['credits']:<8} {pts:.2f}")
                attr = (self.theme.selected() | curses.A_BOLD
                        if i == sel else self.theme.normal())
                safe_addstr(self.win, 6 + i, 2, row_str[:self.w - 4], attr)

            if entries:
                letters = [e["grade"] for e in entries]
                try:
                    credits_list = [float(e["credits"]) for e in entries]
                except ValueError:
                    credits_list = [1.0] * len(entries)
                gpa = calculate_gpa(letters, credits_list)
                safe_addstr(self.win, 6 + len(entries) + 1, 2,
                            f"Cumulative GPA: {gpa:.2f}",
                            self.theme.success() | curses.A_BOLD)

            self._draw_status("[A] Add  [D] Delete  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "dashboard"
            elif key == curses.KEY_UP and sel > 0:
                sel -= 1
            elif key == curses.KEY_DOWN and sel < len(entries) - 1:
                sel += 1
            elif key in (ord("a"), ord("A")):
                name = self._input_dialog("Add Course", "Course name:")
                if name:
                    grade = self._input_dialog("Grade",
                                               "Letter grade (A/B/C…):", "A")
                    if grade and grade.upper() in LETTERS:
                        credits = self._input_dialog("Credits",
                                                     "Credit hours:", "3")
                        entries.append({
                            "name": name,
                            "grade": grade.upper(),
                            "credits": credits or "3",
                        })
            elif key in (ord("d"), ord("D")):
                if entries:
                    entries.pop(sel)
                    sel = max(0, sel - 1)


# ──────────────────────────────────────────────────────────────────────────────
#  Settings / Theme Screen
# ──────────────────────────────────────────────────────────────────────────────

class SettingsScreen(BaseScreen):
    """Application settings – theme selection, backup/restore."""

    def run(self) -> Optional[str]:
        from .theme import THEMES
        theme_names = list(THEMES.keys())
        options = [f"Theme: {n}" for n in theme_names] + [
            "Backup Database",
            "Restore Database",
        ]
        menu = Menu(self.win, self.theme, options,
                    y=4, x=2, h=len(options), w=40)

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Settings"])

            safe_addstr(self.win, 2, 2,
                        f"Settings  (current theme: {self.app.theme.theme_name})",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2, "─" * (self.w - 4), self.theme.border())
            menu.draw()
            self._draw_status("[Enter] Select  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "dashboard"

            idx = menu.handle_key(key)
            if idx is not None:
                if idx < len(theme_names):
                    self.app.theme.set_theme(theme_names[idx])
                    self.set_status(f"Theme changed to {theme_names[idx]}.")
                elif idx == len(theme_names):   # Backup
                    fname = self._input_dialog(
                        "Backup", "Save backup to:", "gradebook_backup.db")
                    if fname:
                        if self.db.backup_database(fname):
                            self.set_status(f"Backup saved to {fname}")
                        else:
                            self.set_status("Backup failed.", error=True)
                elif idx == len(theme_names) + 1:   # Restore
                    fname = self._input_dialog(
                        "Restore", "Restore from file:", "gradebook_backup.db")
                    if fname and os.path.exists(fname):
                        if self._confirm("Restore",
                                         "This will overwrite current data. Continue?"):
                            if self.db.restore_database(fname):
                                self.set_status("Database restored.")
                            else:
                                self.set_status("Restore failed.", error=True)
                    elif fname:
                        self.set_status("File not found.", error=True)


# ──────────────────────────────────────────────────────────────────────────────
#  Help Screen
# ──────────────────────────────────────────────────────────────────────────────

class HelpScreen(BaseScreen):
    """In-app help / keyboard shortcuts."""

    HELP_TEXT = """
  GradeBook Pro – Keyboard Reference
  ════════════════════════════════════════════════════

  Global
  ──────
  F1 / ?      Open this help screen
  Q           Quit / go back
  Esc / B     Go back to previous screen

  Navigation
  ──────────
  ↑ / k       Move up
  ↓ / j       Move down
  Enter       Select / confirm
  Tab         Next form field

  Class Management
  ────────────────
  A           Add new item
  E           Edit selected item
  D           Delete selected item
  /           Search / filter

  Grade Entry
  ───────────
  G / Enter   Enter grade for selected student
  M           Mark as Missing
  E           Mark as Excused

  Attendance
  ──────────
  P           Mark Present
  A           Mark Absent
  L           Mark Late
  E           Mark Excused
  D           Change date

  Reports
  ───────
  R           Open reports
  X           Export report to file

  Themes
  ──────
  Available via Settings screen: Dark, Light, Ocean, Forest

  ════════════════════════════════════════════════════
  Press any key to return.
""".strip().splitlines()

    def run(self) -> Optional[str]:
        offset = 0
        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Help"])

            visible = self.h - 4
            for i in range(visible):
                idx = offset + i
                if idx >= len(self.HELP_TEXT):
                    break
                safe_addstr(self.win, 2 + i, 0,
                            self.HELP_TEXT[idx][:self.w - 1],
                            self.theme.normal())

            self._draw_status("[↑↓] Scroll  [Any other key] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == curses.KEY_UP:
                offset = max(0, offset - 1)
            elif key == curses.KEY_DOWN:
                offset = min(len(self.HELP_TEXT) - visible, offset + 1)
            else:
                return self.app.prev_screen or "dashboard"


# ──────────────────────────────────────────────────────────────────────────────
#  Grade Scale Screen
# ──────────────────────────────────────────────────────────────────────────────

class GradeScaleScreen(BaseScreen):
    """View and edit grade scale thresholds for a class."""

    def run(self) -> Optional[str]:
        class_id = self.app.context.get("class_id")
        if not class_id:
            return "class_detail"

        cls = self.db.get_class(class_id)
        if not cls:
            return "class_detail"

        user = self.auth.current_user
        scales = self.db.get_scales_for_user(user.id)
        if not scales:
            self._info("No Scales", "No grade scales found.")
            return "class_detail"

        # Pick scale to view/edit
        scale = next((s for s in scales if s.id == cls.grade_scale_id), scales[0])
        thresholds = self.db.get_thresholds_for_scale(scale.id)
        sel = 0

        while True:
            self.win.erase()
            fill_background(self.win, self.theme.normal())
            self._draw_nav(["GradeBook Pro", "Classes",
                            cls.name, "Grade Scale"])

            safe_addstr(self.win, 2, 2,
                        f"Grade Scale: {scale.name}",
                        self.theme.title() | curses.A_BOLD)
            safe_addstr(self.win, 3, 2, "─" * (self.w - 4), self.theme.border())

            hdr = f"  {'Letter':<8} {'Min %':>8} {'Max %':>8}"
            safe_addstr(self.win, 4, 2,
                        hdr[:self.w - 4], self.theme.header() | curses.A_BOLD)

            for i, t in enumerate(thresholds):
                row_str = f"  {t.letter:<8} {t.min_percent:>8.1f} {t.max_percent:>8.1f}"
                attr = (self.theme.selected() | curses.A_BOLD
                        if i == sel else self.theme.normal())
                safe_addstr(self.win, 5 + i, 2, row_str[:self.w - 4], attr)

            self._draw_status("[E] Edit selected  [Esc] Back")
            self.win.refresh()

            key = self.win.getch()
            if key == 27 or key in (ord("b"), ord("B")):
                return "class_detail"
            elif key == curses.KEY_UP and sel > 0:
                sel -= 1
            elif key == curses.KEY_DOWN and sel < len(thresholds) - 1:
                sel += 1
            elif key in (ord("e"), ord("E")):
                if thresholds:
                    t = thresholds[sel]
                    mn = self._input_dialog("Min %",
                                            f"Min percent for {t.letter}:",
                                            str(t.min_percent))
                    mx = self._input_dialog("Max %",
                                            f"Max percent for {t.letter}:",
                                            str(t.max_percent))
                    if mn is not None and mx is not None:
                        try:
                            self.db.upsert_threshold(
                                scale.id, t.letter, float(mn), float(mx))
                            self.set_status("Threshold updated.")
                            thresholds = self.db.get_thresholds_for_scale(scale.id)
                        except ValueError:
                            self.set_status("Invalid number.", error=True)
