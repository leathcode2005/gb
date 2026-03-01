"""Color theme management for GradeBook Pro."""

import curses
from typing import Dict, Any

# ------------------------------------------------------------------ #
#  Symbolic color-pair IDs                                             #
# ------------------------------------------------------------------ #
PAIR_NORMAL      = 1
PAIR_HEADER      = 2
PAIR_SELECTED    = 3
PAIR_BORDER      = 4
PAIR_TITLE       = 5
PAIR_STATUS      = 6
PAIR_ERROR       = 7
PAIR_SUCCESS     = 8
PAIR_WARNING     = 9
PAIR_DIM         = 10
PAIR_INPUT       = 11
PAIR_INPUT_LABEL = 12
PAIR_HIGHLIGHT   = 13
PAIR_DANGER      = 14
PAIR_SPLASH      = 15

# ------------------------------------------------------------------ #
#  Theme definitions                                                   #
# ------------------------------------------------------------------ #
THEMES: Dict[str, Dict[str, Any]] = {
    "Dark": {
        "bg":            curses.COLOR_BLACK,
        "fg":            curses.COLOR_WHITE,
        "header_bg":     curses.COLOR_BLUE,
        "header_fg":     curses.COLOR_WHITE,
        "selected_bg":   curses.COLOR_CYAN,
        "selected_fg":   curses.COLOR_BLACK,
        "border_fg":     curses.COLOR_CYAN,
        "title_fg":      curses.COLOR_YELLOW,
        "status_bg":     curses.COLOR_BLUE,
        "status_fg":     curses.COLOR_WHITE,
        "error_fg":      curses.COLOR_RED,
        "success_fg":    curses.COLOR_GREEN,
        "warning_fg":    curses.COLOR_YELLOW,
        "dim_fg":        curses.COLOR_WHITE,
        "input_bg":      curses.COLOR_BLACK,
        "input_fg":      curses.COLOR_WHITE,
        "input_lbl_fg":  curses.COLOR_CYAN,
        "highlight_bg":  curses.COLOR_YELLOW,
        "highlight_fg":  curses.COLOR_BLACK,
        "danger_fg":     curses.COLOR_RED,
        "splash_fg":     curses.COLOR_CYAN,
    },
    "Light": {
        "bg":            curses.COLOR_WHITE,
        "fg":            curses.COLOR_BLACK,
        "header_bg":     curses.COLOR_BLUE,
        "header_fg":     curses.COLOR_WHITE,
        "selected_bg":   curses.COLOR_BLUE,
        "selected_fg":   curses.COLOR_WHITE,
        "border_fg":     curses.COLOR_BLUE,
        "title_fg":      curses.COLOR_BLUE,
        "status_bg":     curses.COLOR_BLUE,
        "status_fg":     curses.COLOR_WHITE,
        "error_fg":      curses.COLOR_RED,
        "success_fg":    curses.COLOR_GREEN,
        "warning_fg":    curses.COLOR_YELLOW,
        "dim_fg":        curses.COLOR_BLACK,
        "input_bg":      curses.COLOR_WHITE,
        "input_fg":      curses.COLOR_BLACK,
        "input_lbl_fg":  curses.COLOR_BLUE,
        "highlight_bg":  curses.COLOR_YELLOW,
        "highlight_fg":  curses.COLOR_BLACK,
        "danger_fg":     curses.COLOR_RED,
        "splash_fg":     curses.COLOR_BLUE,
    },
    "Ocean": {
        "bg":            curses.COLOR_BLACK,
        "fg":            curses.COLOR_CYAN,
        "header_bg":     curses.COLOR_BLUE,
        "header_fg":     curses.COLOR_CYAN,
        "selected_bg":   curses.COLOR_BLUE,
        "selected_fg":   curses.COLOR_WHITE,
        "border_fg":     curses.COLOR_BLUE,
        "title_fg":      curses.COLOR_CYAN,
        "status_bg":     curses.COLOR_BLUE,
        "status_fg":     curses.COLOR_WHITE,
        "error_fg":      curses.COLOR_RED,
        "success_fg":    curses.COLOR_GREEN,
        "warning_fg":    curses.COLOR_YELLOW,
        "dim_fg":        curses.COLOR_CYAN,
        "input_bg":      curses.COLOR_BLACK,
        "input_fg":      curses.COLOR_CYAN,
        "input_lbl_fg":  curses.COLOR_BLUE,
        "highlight_bg":  curses.COLOR_CYAN,
        "highlight_fg":  curses.COLOR_BLACK,
        "danger_fg":     curses.COLOR_RED,
        "splash_fg":     curses.COLOR_BLUE,
    },
    "Forest": {
        "bg":            curses.COLOR_BLACK,
        "fg":            curses.COLOR_GREEN,
        "header_bg":     curses.COLOR_GREEN,
        "header_fg":     curses.COLOR_BLACK,
        "selected_bg":   curses.COLOR_GREEN,
        "selected_fg":   curses.COLOR_BLACK,
        "border_fg":     curses.COLOR_GREEN,
        "title_fg":      curses.COLOR_GREEN,
        "status_bg":     curses.COLOR_GREEN,
        "status_fg":     curses.COLOR_BLACK,
        "error_fg":      curses.COLOR_RED,
        "success_fg":    curses.COLOR_GREEN,
        "warning_fg":    curses.COLOR_YELLOW,
        "dim_fg":        curses.COLOR_GREEN,
        "input_bg":      curses.COLOR_BLACK,
        "input_fg":      curses.COLOR_GREEN,
        "input_lbl_fg":  curses.COLOR_GREEN,
        "highlight_bg":  curses.COLOR_GREEN,
        "highlight_fg":  curses.COLOR_BLACK,
        "danger_fg":     curses.COLOR_RED,
        "splash_fg":     curses.COLOR_GREEN,
    },
}


class ThemeManager:
    """Initializes curses color pairs and provides convenient attribute getters."""

    def __init__(self, theme_name: str = "Dark"):
        """Initialize theme manager with the given theme name."""
        self.theme_name = theme_name
        self._initialized = False
        self._has_colors = False

    def initialize(self) -> None:
        """Call after curses.start_color(); sets up all color pairs."""
        try:
            curses.start_color()
        except curses.error:
            pass
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        self._has_colors = curses.has_colors() and curses.COLORS >= 8
        if self._has_colors:
            self._apply_theme(self.theme_name)
        self._initialized = True

    def set_theme(self, theme_name: str) -> None:
        """Switch to a different theme and reinitialize color pairs."""
        if theme_name in THEMES:
            self.theme_name = theme_name
            if self._initialized and self._has_colors:
                self._apply_theme(theme_name)

    def _apply_theme(self, theme_name: str) -> None:
        """Initialize all curses color pairs for the named theme."""
        t = THEMES.get(theme_name, THEMES["Dark"])
        pairs = [
            (PAIR_NORMAL,      t["fg"],          t["bg"]),
            (PAIR_HEADER,      t["header_fg"],   t["header_bg"]),
            (PAIR_SELECTED,    t["selected_fg"],  t["selected_bg"]),
            (PAIR_BORDER,      t["border_fg"],   t["bg"]),
            (PAIR_TITLE,       t["title_fg"],    t["bg"]),
            (PAIR_STATUS,      t["status_fg"],   t["status_bg"]),
            (PAIR_ERROR,       t["error_fg"],    t["bg"]),
            (PAIR_SUCCESS,     t["success_fg"],  t["bg"]),
            (PAIR_WARNING,     t["warning_fg"],  t["bg"]),
            (PAIR_DIM,         t["dim_fg"],      t["bg"]),
            (PAIR_INPUT,       t["input_fg"],    t["input_bg"]),
            (PAIR_INPUT_LABEL, t["input_lbl_fg"], t["bg"]),
            (PAIR_HIGHLIGHT,   t["highlight_fg"], t["highlight_bg"]),
            (PAIR_DANGER,      t["danger_fg"],   t["bg"]),
            (PAIR_SPLASH,      t["splash_fg"],   t["bg"]),
        ]
        max_colors = curses.COLORS if curses.COLORS > 0 else 0
        max_pairs  = curses.COLOR_PAIRS if curses.COLOR_PAIRS > 0 else 0
        for pair_id, fg, bg in pairs:
            if pair_id >= max_pairs:
                continue
            # Clamp color values to what the terminal supports
            safe_fg = fg if 0 <= fg < max_colors else -1
            safe_bg = bg if 0 <= bg < max_colors else -1
            try:
                curses.init_pair(pair_id, safe_fg, safe_bg)
            except (curses.error, ValueError, OverflowError):
                pass

    # ------------------------------------------------------------------ #
    #  Convenience attribute accessors                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def normal()      -> int: return curses.color_pair(PAIR_NORMAL)
    @staticmethod
    def header()      -> int: return curses.color_pair(PAIR_HEADER)
    @staticmethod
    def selected()    -> int: return curses.color_pair(PAIR_SELECTED)
    @staticmethod
    def border()      -> int: return curses.color_pair(PAIR_BORDER)
    @staticmethod
    def title()       -> int: return curses.color_pair(PAIR_TITLE)
    @staticmethod
    def status()      -> int: return curses.color_pair(PAIR_STATUS)
    @staticmethod
    def error()       -> int: return curses.color_pair(PAIR_ERROR)
    @staticmethod
    def success()     -> int: return curses.color_pair(PAIR_SUCCESS)
    @staticmethod
    def warning()     -> int: return curses.color_pair(PAIR_WARNING)
    @staticmethod
    def dim()         -> int: return curses.color_pair(PAIR_DIM)
    @staticmethod
    def input_field() -> int: return curses.color_pair(PAIR_INPUT)
    @staticmethod
    def input_label() -> int: return curses.color_pair(PAIR_INPUT_LABEL)
    @staticmethod
    def highlight()   -> int: return curses.color_pair(PAIR_HIGHLIGHT)
    @staticmethod
    def danger()      -> int: return curses.color_pair(PAIR_DANGER)
    @staticmethod
    def splash()      -> int: return curses.color_pair(PAIR_SPLASH)
