"""Main application controller for GradeBook Pro."""

import curses
import os
import sys
from typing import Optional, Dict, Any, List

from .database import DatabaseManager
from .auth import AuthManager
from .ui.theme import ThemeManager
from .ui.splash import SplashScreen
from .ui.screens import (
    LoginScreen, RegisterScreen, DashboardScreen,
    ClassListScreen, ClassDetailScreen, CategoryScreen,
    StudentListScreen, StudentDetailScreen, AssignmentScreen,
    GradeEntryScreen, ReportScreen, SettingsScreen, HelpScreen,
    GPAScreen, AttendanceScreen, GradeScaleScreen,
)
from .models import UndoAction
from gradebook import __version__ as VERSION


class GradebookApp:
    """
    Top-level application class.

    Owns the curses window, the database, authentication, theme, and
    the screen-routing table.  Call :meth:`run` to start.
    """

    VERSION = VERSION

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the application (does not start curses yet)."""
        self.db = DatabaseManager(*([db_path] if db_path else []))
        self.auth = AuthManager(self.db)
        self.theme = ThemeManager("Dark")

        self.stdscr: Optional["curses.window"] = None
        self.context: Dict[str, Any] = {}       # shared state between screens
        self.prev_screen: Optional[str] = None
        self._undo_stack: List[UndoAction] = []
        self._running = False

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Start the application using curses.wrapper for clean teardown."""
        # Ensure TERM is set so curses can find color capabilities
        os.environ.setdefault("TERM", "xterm-256color")
        try:
            curses.wrapper(self._main)
        except KeyboardInterrupt:
            pass
        finally:
            self.db.close()

    # ------------------------------------------------------------------ #
    #  curses main loop                                                    #
    # ------------------------------------------------------------------ #

    def _main(self, stdscr: "curses.window") -> None:
        """Called by curses.wrapper; owns the event loop."""
        self.stdscr = stdscr

        # Initialise terminal
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)

        # Colours
        self.theme.initialize()

        # Splash
        try:
            SplashScreen(stdscr, self.theme).show()
        except Exception:
            pass

        # Start at the login screen
        current = "login"
        self._running = True

        while self._running:
            try:
                stdscr.clear()
                stdscr.refresh()
                current = self._route(current) or "login"
            except curses.error:
                # Terminal was resized – just redraw
                stdscr.clear()
                stdscr.refresh()
            except Exception as exc:
                # Never crash on bad input
                self._show_error(str(exc))
                current = current or "login"

    # ------------------------------------------------------------------ #
    #  Screen router                                                       #
    # ------------------------------------------------------------------ #

    def _route(self, screen_name: str) -> str:
        """Instantiate the requested screen and run it; return next screen name."""
        self.prev_screen = screen_name

        routes = {
            "login":         LoginScreen,
            "register":      RegisterScreen,
            "dashboard":     DashboardScreen,
            "classes":       ClassListScreen,
            "class_detail":  ClassDetailScreen,
            "categories":    CategoryScreen,
            "assignments":   AssignmentScreen,
            "students":      StudentListScreen,
            "student_detail":StudentDetailScreen,
            "grade_entry":   GradeEntryScreen,
            "reports":       ReportScreen,
            "attendance":    AttendanceScreen,
            "settings":      SettingsScreen,
            "help":          HelpScreen,
            "gpa":           GPAScreen,
            "grade_scale":   GradeScaleScreen,
        }

        if screen_name == "quit":
            self._running = False
            return "quit"

        # Require login for protected screens
        protected = {
            "dashboard", "classes", "class_detail", "categories",
            "assignments", "students", "student_detail", "grade_entry",
            "reports", "attendance", "settings", "gpa", "grade_scale",
        }
        if screen_name in protected and not self.auth.is_logged_in():
            return "login"

        screen_cls = routes.get(screen_name)
        if screen_cls is None:
            return "login"

        screen = screen_cls(self)
        next_screen = screen.run()
        return next_screen or "login"

    # ------------------------------------------------------------------ #
    #  Undo                                                                #
    # ------------------------------------------------------------------ #

    def push_undo(self, action: UndoAction) -> None:
        """Push an action onto the undo stack (max 50 entries)."""
        self._undo_stack.append(action)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def pop_undo(self) -> Optional[UndoAction]:
        """Pop the most recent undoable action."""
        if self._undo_stack:
            return self._undo_stack.pop()
        return None

    # ------------------------------------------------------------------ #
    #  Error display                                                       #
    # ------------------------------------------------------------------ #

    def _show_error(self, message: str) -> None:
        """Display an unhandled error in a simple overlay and wait for a key."""
        if self.stdscr is None:
            return
        try:
            h, w = self.stdscr.getmaxyx()
            msg = f" ERROR: {message[:w - 12]} "
            row = h // 2
            col = max(0, (w - len(msg)) // 2)
            self.stdscr.addstr(row, col, msg,
                               curses.color_pair(7) | curses.A_BOLD)
            self.stdscr.addstr(row + 1,
                               max(0, (w - 24) // 2),
                               " Press any key to continue ",
                               curses.A_DIM)
            self.stdscr.refresh()
            self.stdscr.getch()
        except curses.error:
            pass
