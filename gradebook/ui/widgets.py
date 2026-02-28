"""Reusable ncurses UI widgets for GradeBook Pro."""

import curses
import curses.textpad
from typing import List, Optional, Tuple, Callable, Any, Dict

from .theme import ThemeManager

# ------------------------------------------------------------------ #
#  Box-drawing characters                                              #
# ------------------------------------------------------------------ #
HORIZONTAL   = "─"
VERTICAL     = "│"
TOP_LEFT     = "┌"
TOP_RIGHT    = "┐"
BOTTOM_LEFT  = "└"
BOTTOM_RIGHT = "┘"
T_RIGHT      = "├"
T_LEFT       = "┤"
T_DOWN       = "┬"
T_UP         = "┴"
CROSS        = "┼"


# ------------------------------------------------------------------ #
#  Low-level helpers                                                   #
# ------------------------------------------------------------------ #

def safe_addstr(win: "curses.window", y: int, x: int,
                text: str, attr: int = 0) -> None:
    """Add a string to *win* clipping at window edges; never raises."""
    try:
        max_y, max_x = win.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            max_len = max_x - x
            win.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass


def safe_addch(win: "curses.window", y: int, x: int,
               ch: str, attr: int = 0) -> None:
    """Add a single character without raising."""
    try:
        max_y, max_x = win.getmaxyx()
        if 0 <= y < max_y and 0 <= x < max_x:
            win.addch(y, x, ch, attr)
    except curses.error:
        pass


def draw_box(win: "curses.window", y: int, x: int,
             h: int, w: int,
             title: Optional[str] = None,
             attr: int = 0) -> None:
    """Draw a Unicode box at position (y, x) with given height and width."""
    # Top border
    safe_addstr(win, y, x, TOP_LEFT + HORIZONTAL * (w - 2) + TOP_RIGHT, attr)
    # Side borders
    for row in range(1, h - 1):
        safe_addch(win, y + row, x, VERTICAL, attr)
        safe_addch(win, y + row, x + w - 1, VERTICAL, attr)
    # Bottom border
    safe_addstr(win, y + h - 1, x,
                BOTTOM_LEFT + HORIZONTAL * (w - 2) + BOTTOM_RIGHT, attr)
    # Title
    if title:
        from gradebook.utils import truncate_text
        t = f" {truncate_text(title, w - 4)} "
        tx = x + (w - len(t)) // 2
        safe_addstr(win, y, tx, t, attr)


def fill_background(win: "curses.window", attr: int = 0) -> None:
    """Fill the entire window with spaces using the given attribute."""
    h, w = win.getmaxyx()
    for row in range(h):
        safe_addstr(win, row, 0, " " * w, attr)


# ------------------------------------------------------------------ #
#  NavBar                                                              #
# ------------------------------------------------------------------ #

class NavBar:
    """Top breadcrumb navigation bar."""

    def __init__(self, win: "curses.window", theme: ThemeManager):
        self.win = win
        self.theme = theme
        self.breadcrumbs: List[str] = ["Home"]

    def set_breadcrumbs(self, crumbs: List[str]) -> None:
        self.breadcrumbs = crumbs

    def draw(self) -> None:
        """Render the nav-bar on row 0."""
        _, w = self.win.getmaxyx()
        crumb_str = " > ".join(self.breadcrumbs)
        text = f"  {crumb_str}"
        safe_addstr(self.win, 0, 0, " " * w, self.theme.header())
        safe_addstr(self.win, 0, 0, text, self.theme.header() | curses.A_BOLD)


# ------------------------------------------------------------------ #
#  StatusBar                                                           #
# ------------------------------------------------------------------ #

class StatusBar:
    """Bottom status bar showing hints / messages."""

    def __init__(self, win: "curses.window", theme: ThemeManager):
        self.win = win
        self.theme = theme
        self._message = ""
        self._is_error = False

    def set_message(self, msg: str, is_error: bool = False) -> None:
        self._message = msg
        self._is_error = is_error

    def draw(self, hints: str = "") -> None:
        """Render the status bar on the last row."""
        h, w = self.win.getmaxyx()
        row = h - 1
        safe_addstr(self.win, row, 0, " " * (w - 1), self.theme.status())
        if self._message:
            attr = (self.theme.error() if self._is_error else self.theme.status()) | curses.A_BOLD
            safe_addstr(self.win, row, 1, self._message[:w - 2], attr)
        elif hints:
            safe_addstr(self.win, row, 1, hints[:w - 2], self.theme.status())


# ------------------------------------------------------------------ #
#  Menu                                                                #
# ------------------------------------------------------------------ #

class Menu:
    """Scrollable, highlighted menu."""

    def __init__(self, win: "curses.window", theme: ThemeManager,
                 items: List[str], y: int, x: int, h: int, w: int):
        self.win = win
        self.theme = theme
        self.items = items
        self.y = y
        self.x = x
        self.h = h
        self.w = w
        self.selected = 0
        self.offset = 0

    def set_items(self, items: List[str]) -> None:
        self.items = items
        self.selected = min(self.selected, max(0, len(items) - 1))
        self.offset = 0

    def draw(self) -> None:
        """Render visible menu items."""
        for i in range(self.h):
            idx = self.offset + i
            if idx >= len(self.items):
                safe_addstr(self.win, self.y + i, self.x, " " * self.w,
                            self.theme.normal())
                continue
            text = self.items[idx]
            padded = f" {text} "[:self.w].ljust(self.w)
            if idx == self.selected:
                safe_addstr(self.win, self.y + i, self.x, padded,
                            self.theme.selected() | curses.A_BOLD)
            else:
                safe_addstr(self.win, self.y + i, self.x, padded,
                            self.theme.normal())

    def handle_key(self, key: int) -> Optional[int]:
        """
        Process a key event.

        Returns the selected index on ENTER, or None otherwise.
        """
        if key in (curses.KEY_UP, ord("k")):
            if self.selected > 0:
                self.selected -= 1
                if self.selected < self.offset:
                    self.offset = self.selected
        elif key in (curses.KEY_DOWN, ord("j")):
            if self.selected < len(self.items) - 1:
                self.selected += 1
                if self.selected >= self.offset + self.h:
                    self.offset = self.selected - self.h + 1
        elif key in (curses.KEY_PPAGE,):
            self.selected = max(0, self.selected - self.h)
            self.offset = max(0, self.offset - self.h)
        elif key in (curses.KEY_NPAGE,):
            self.selected = min(len(self.items) - 1, self.selected + self.h)
            self.offset = min(max(0, len(self.items) - self.h),
                              self.offset + self.h)
        elif key in (curses.KEY_HOME,):
            self.selected = 0
            self.offset = 0
        elif key in (curses.KEY_END,):
            self.selected = len(self.items) - 1
            self.offset = max(0, len(self.items) - self.h)
        elif key in (10, 13, curses.KEY_ENTER):
            if self.items:
                return self.selected
        return None


# ------------------------------------------------------------------ #
#  SearchBox                                                           #
# ------------------------------------------------------------------ #

class SearchBox:
    """Inline search / filter widget."""

    def __init__(self, win: "curses.window", theme: ThemeManager,
                 y: int, x: int, w: int):
        self.win = win
        self.theme = theme
        self.y = y
        self.x = x
        self.w = w
        self.query = ""
        self.active = False

    def draw(self) -> None:
        label = "Search: "
        max_len = self.w - len(label)
        text = f"{label}{self.query[-max_len:]}"
        attr = self.theme.input_field() if self.active else self.theme.dim()
        safe_addstr(self.win, self.y, self.x, text.ljust(self.w)[:self.w], attr)

    def handle_key(self, key: int) -> bool:
        """Process a keystroke. Returns True if the query changed."""
        if key in (curses.KEY_BACKSPACE, 127, 8):
            if self.query:
                self.query = self.query[:-1]
                return True
        elif key == 27:  # ESC clears
            self.query = ""
            return True
        elif 32 <= key < 127:
            self.query += chr(key)
            return True
        return False


# ------------------------------------------------------------------ #
#  Form                                                                #
# ------------------------------------------------------------------ #

class FormField:
    """A single labelled field inside a Form."""

    def __init__(self, name: str, label: str, value: str = "",
                 required: bool = False, secret: bool = False,
                 validator: Optional[Callable[[str], bool]] = None,
                 max_len: int = 80):
        self.name = name
        self.label = label
        self.value = value
        self.required = required
        self.secret = secret
        self.validator = validator
        self.max_len = max_len
        self.error: str = ""
        self.cursor_pos: int = len(value)

    def insert_char(self, ch: str) -> None:
        if len(self.value) < self.max_len:
            self.value = (self.value[:self.cursor_pos] + ch +
                          self.value[self.cursor_pos:])
            self.cursor_pos += 1

    def delete_char(self) -> None:
        if self.cursor_pos > 0:
            self.value = (self.value[:self.cursor_pos - 1] +
                          self.value[self.cursor_pos:])
            self.cursor_pos -= 1

    def delete_forward(self) -> None:
        if self.cursor_pos < len(self.value):
            self.value = (self.value[:self.cursor_pos] +
                          self.value[self.cursor_pos + 1:])

    def validate(self) -> bool:
        if self.required and not self.value.strip():
            self.error = f"{self.label} is required"
            return False
        if self.validator and not self.validator(self.value):
            self.error = f"{self.label} is invalid"
            return False
        self.error = ""
        return True


class Form:
    """Multi-field form with cursor navigation and validation."""

    def __init__(self, win: "curses.window", theme: ThemeManager,
                 fields: List[FormField], y: int, x: int, w: int):
        self.win = win
        self.theme = theme
        self.fields = fields
        self.y = y
        self.x = x
        self.w = w
        self.current = 0
        self.submitted = False
        self.cancelled = False

    def draw(self) -> None:
        """Render all form fields."""
        label_w = max((len(f.label) for f in self.fields), default=10) + 2
        input_w = self.w - label_w - 4

        for i, field in enumerate(self.fields):
            row = self.y + i * 2
            is_active = i == self.current

            # Label
            safe_addstr(self.win, row, self.x,
                        f"{field.label:>{label_w}}: ",
                        self.theme.input_label() | (curses.A_BOLD if is_active else 0))

            # Input
            display = "*" * len(field.value) if field.secret else field.value
            padded = display[-input_w:].ljust(input_w)[:input_w]
            attr = self.theme.input_field()
            if is_active:
                attr |= curses.A_UNDERLINE
            safe_addstr(self.win, row, self.x + label_w + 2, padded, attr)

            # Cursor
            if is_active:
                cur_col = min(field.cursor_pos, input_w - 1)
                display_offset = max(0, len(display) - input_w)
                visible_pos = field.cursor_pos - display_offset
                if 0 <= visible_pos < input_w:
                    ch = display[field.cursor_pos] if field.cursor_pos < len(display) else " "
                    safe_addch(self.win, row,
                                self.x + label_w + 2 + visible_pos,
                                ch,
                                self.theme.input_field() | curses.A_REVERSE)

            # Error
            if field.error:
                safe_addstr(self.win, row + 1,
                            self.x + label_w + 2,
                            field.error[:input_w],
                            self.theme.error())

    def handle_key(self, key: int) -> bool:
        """
        Process keystrokes.

        Returns True if the form was submitted or cancelled (check
        self.submitted and self.cancelled).
        """
        field = self.fields[self.current]

        if key in (9, curses.KEY_DOWN):         # Tab / Down -> next field
            self.current = (self.current + 1) % len(self.fields)
        elif key == curses.KEY_UP:              # Up -> prev field
            self.current = (self.current - 1) % len(self.fields)
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            field.delete_char()
        elif key == curses.KEY_DC:
            field.delete_forward()
        elif key == curses.KEY_LEFT:
            field.cursor_pos = max(0, field.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            field.cursor_pos = min(len(field.value), field.cursor_pos + 1)
        elif key == curses.KEY_HOME:
            field.cursor_pos = 0
        elif key == curses.KEY_END:
            field.cursor_pos = len(field.value)
        elif key in (10, 13):                   # Enter -> validate + submit
            all_valid = all(f.validate() for f in self.fields)
            if all_valid:
                self.submitted = True
                return True
        elif key == 27:                         # ESC -> cancel
            self.cancelled = True
            return True
        elif 32 <= key < 256:
            field.insert_char(chr(key))

        return False

    def get_values(self) -> Dict[str, str]:
        """Return a dict of field_name -> value."""
        return {f.name: f.value for f in self.fields}


# ------------------------------------------------------------------ #
#  Dialog                                                              #
# ------------------------------------------------------------------ #

class Dialog:
    """Modal dialog (yes/no confirmation, info, or single-input prompt)."""

    def __init__(self, win: "curses.window", theme: ThemeManager,
                 title: str, message: str,
                 dialog_type: str = "info",   # info | confirm | input
                 default: str = ""):
        self.win = win
        self.theme = theme
        self.title = title
        self.message = message
        self.dialog_type = dialog_type
        self.result: Optional[bool] = None
        self.input_value: str = default
        self._cursor = len(default)

    def run(self) -> Any:
        """
        Block and process input until the dialog is dismissed.

        Returns True/False for confirm, input string for input, None for info.
        """
        h, w = self.win.getmaxyx()
        dw = min(60, w - 4)
        dh = 7 if self.dialog_type == "input" else 6
        dy = (h - dh) // 2
        dx = (w - dw) // 2

        self.win.keypad(True)
        while True:
            self._draw(dy, dx, dh, dw)
            self.win.refresh()
            key = self.win.getch()

            if self.dialog_type == "info":
                return None

            elif self.dialog_type == "confirm":
                if key in (ord("y"), ord("Y"), 10, 13):
                    return True
                elif key in (ord("n"), ord("N"), 27):
                    return False

            elif self.dialog_type == "input":
                if key in (10, 13):
                    return self.input_value
                elif key == 27:
                    return None
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    if self._cursor > 0:
                        self.input_value = (self.input_value[:self._cursor - 1] +
                                            self.input_value[self._cursor:])
                        self._cursor -= 1
                elif 32 <= key < 256:
                    ch = chr(key)
                    self.input_value = (self.input_value[:self._cursor] + ch +
                                        self.input_value[self._cursor:])
                    self._cursor += 1

    def _draw(self, dy: int, dx: int, dh: int, dw: int) -> None:
        """Render the dialog box."""
        draw_box(self.win, dy, dx, dh, dw,
                 title=self.title, attr=self.theme.border() | curses.A_BOLD)

        # Message (word-wrap naively)
        msg_lines = []
        words = self.message.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 <= dw - 4:
                line = (line + " " + word).strip()
            else:
                msg_lines.append(line)
                line = word
        if line:
            msg_lines.append(line)

        for i, ml in enumerate(msg_lines[:dh - 4]):
            safe_addstr(self.win, dy + 1 + i, dx + 2,
                        ml[:dw - 4], self.theme.normal())

        if self.dialog_type == "confirm":
            hint = "[Y]es  [N]o"
            safe_addstr(self.win, dy + dh - 2, dx + (dw - len(hint)) // 2,
                        hint, self.theme.warning() | curses.A_BOLD)

        elif self.dialog_type == "input":
            safe_addstr(self.win, dy + dh - 3, dx + 2,
                        "Value: ", self.theme.input_label())
            val_display = self.input_value[-(dw - 12):]
            safe_addstr(self.win, dy + dh - 3, dx + 9,
                        val_display.ljust(dw - 11)[:dw - 11],
                        self.theme.input_field() | curses.A_UNDERLINE)
            hint = "[Enter] Confirm  [Esc] Cancel"
            safe_addstr(self.win, dy + dh - 2, dx + (dw - len(hint)) // 2,
                        hint, self.theme.dim())

        elif self.dialog_type == "info":
            hint = "[Any key] OK"
            safe_addstr(self.win, dy + dh - 2, dx + (dw - len(hint)) // 2,
                        hint, self.theme.dim())


# ------------------------------------------------------------------ #
#  Table                                                               #
# ------------------------------------------------------------------ #

class Table:
    """Scrollable table with column headers."""

    def __init__(self, win: "curses.window", theme: ThemeManager,
                 columns: List[Tuple[str, int]],   # (header, width)
                 rows: List[List[str]],
                 y: int, x: int, h: int, w: int):
        self.win = win
        self.theme = theme
        self.columns = columns
        self.rows = rows
        self.y = y
        self.x = x
        self.h = h
        self.w = w
        self.selected = 0
        self.offset = 0

    def set_rows(self, rows: List[List[str]]) -> None:
        self.rows = rows
        self.selected = min(self.selected, max(0, len(rows) - 1))
        self.offset = 0

    def draw(self) -> None:
        """Render the table."""
        # Header row
        col_x = self.x
        header_str = ""
        for col_name, col_w in self.columns:
            header_str += f" {col_name[:col_w - 1]:<{col_w - 1}}"
        safe_addstr(self.win, self.y, self.x,
                    header_str[:self.w].ljust(self.w)[:self.w],
                    self.theme.header() | curses.A_BOLD)

        # Data rows
        for i in range(self.h - 1):
            idx = self.offset + i
            row_y = self.y + 1 + i
            if idx >= len(self.rows):
                safe_addstr(self.win, row_y, self.x, " " * self.w,
                            self.theme.normal())
                continue
            row = self.rows[idx]
            row_str = ""
            for j, (_, col_w) in enumerate(self.columns):
                cell = row[j] if j < len(row) else ""
                row_str += f" {cell[:col_w - 1]:<{col_w - 1}}"
            padded = row_str[:self.w].ljust(self.w)[:self.w]
            attr = (self.theme.selected() | curses.A_BOLD
                    if idx == self.selected else self.theme.normal())
            safe_addstr(self.win, row_y, self.x, padded, attr)

    def handle_key(self, key: int) -> Optional[int]:
        """Returns selected row index on Enter, None otherwise."""
        visible = self.h - 1
        if key in (curses.KEY_UP, ord("k")):
            if self.selected > 0:
                self.selected -= 1
                if self.selected < self.offset:
                    self.offset = self.selected
        elif key in (curses.KEY_DOWN, ord("j")):
            if self.selected < len(self.rows) - 1:
                self.selected += 1
                if self.selected >= self.offset + visible:
                    self.offset = self.selected - visible + 1
        elif key in (curses.KEY_HOME,):
            self.selected = 0
            self.offset = 0
        elif key in (curses.KEY_END,):
            self.selected = len(self.rows) - 1
            self.offset = max(0, len(self.rows) - visible)
        elif key in (10, 13, curses.KEY_ENTER):
            if self.rows:
                return self.selected
        return None


# ------------------------------------------------------------------ #
#  ProgressBar                                                         #
# ------------------------------------------------------------------ #

class ProgressBar:
    """Horizontal progress bar for displaying percentages."""

    def __init__(self, win: "curses.window", theme: ThemeManager,
                 y: int, x: int, w: int):
        self.win = win
        self.theme = theme
        self.y = y
        self.x = x
        self.w = w

    def draw(self, value: float, max_value: float = 100.0,
             label: str = "") -> None:
        """Draw the progress bar for value/max_value."""
        pct = min(1.0, value / max_value) if max_value else 0.0
        filled = int(pct * (self.w - 2))
        bar = "█" * filled + "░" * (self.w - 2 - filled)
        text = f"[{bar}]"
        if label:
            text = f"{label} {text}"
        safe_addstr(self.win, self.y, self.x, text[:self.w],
                    self.theme.normal())
