"""Animated splash screen for GradeBook Pro."""

import curses
import time
from typing import Optional

from .widgets import safe_addstr, fill_background
from .theme import ThemeManager

APP_NAME = "GradeBook Pro"
VERSION  = "v1.0.0"

ASCII_LOGO = [
    r"  ____               _      ____              _      ",
    r" / ___|_ __ __ _  __| | ___| __ )  ___   ___ | | __ ",
    r"| |  _| '__/ _` |/ _` |/ _ \  _ \ / _ \ / _ \| |/ / ",
    r"| |_| | | | (_| | (_| |  __/ |_) | (_) | (_) |   <  ",
    r" \____|_|  \__,_|\__,_|\___|____/ \___/ \___/|_|\_\ ",
    r"                                              Pro     ",
]

SUBTITLE = "The Terminal Gradebook"


class SplashScreen:
    """Displays an animated splash screen on startup."""

    def __init__(self, win: "curses.window", theme: ThemeManager):
        """Initialize with the main curses window and the active theme."""
        self.win = win
        self.theme = theme

    # ------------------------------------------------------------------ #

    def show(self, duration: float = 1.8) -> None:
        """
        Display the splash screen.

        Shows a typewriter animation of the ASCII logo, then waits for
        *duration* seconds (or a keypress) before returning.
        """
        self.win.nodelay(True)
        try:
            self._render(animated=True)
            deadline = time.time() + duration
            while time.time() < deadline:
                key = self.win.getch()
                if key != -1:
                    break
                time.sleep(0.03)
        finally:
            self.win.nodelay(False)

    # ------------------------------------------------------------------ #

    def _render(self, animated: bool = False) -> None:
        """Render the splash content to the window."""
        h, w = self.win.getmaxyx()

        # Background
        fill_background(self.win, self.theme.normal())

        logo_h = len(ASCII_LOGO)
        logo_w = max(len(line) for line in ASCII_LOGO)
        start_y = max(0, (h - logo_h - 6) // 2)
        start_x = max(0, (w - logo_w) // 2)

        splash_attr = self.theme.splash() | curses.A_BOLD

        for i, line in enumerate(ASCII_LOGO):
            row = start_y + i
            col = max(0, (w - len(line)) // 2)
            if animated:
                # typewriter effect: reveal one character at a time
                for j, ch in enumerate(line):
                    try:
                        if row < h and col + j < w - 1:
                            self.win.addch(row, col + j, ch, splash_attr)
                    except curses.error:
                        pass
                self.win.refresh()
                time.sleep(0.012)
            else:
                safe_addstr(self.win, row, col, line, splash_attr)

        # Subtitle
        sub_row = start_y + logo_h + 1
        sub_col = max(0, (w - len(SUBTITLE)) // 2)
        safe_addstr(self.win, sub_row, sub_col, SUBTITLE,
                    self.theme.title() | curses.A_BOLD)

        # Version
        ver_row = sub_row + 1
        ver_col = max(0, (w - len(VERSION)) // 2)
        safe_addstr(self.win, ver_row, ver_col, VERSION, self.theme.dim())

        # Press-any-key
        prompt = "Press any key to continue..."
        pr_row = ver_row + 2
        pr_col = max(0, (w - len(prompt)) // 2)
        safe_addstr(self.win, pr_row, pr_col, prompt,
                    self.theme.dim() | curses.A_BLINK)

        self.win.refresh()
