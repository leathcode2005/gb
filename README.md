# GradeBook Pro

A full-featured **ncurses Python terminal gradebook application** — pure Python 3,
standard library only (curses, sqlite3, hashlib).

---

## Quick Start

```bash
python main.py
```

Requirements: **Python 3.8+**, standard library only (no pip installs needed).

---

## File Structure

```
gb/
├── main.py                  # Entry point
├── gradebook/
│   ├── __init__.py
│   ├── app.py               # GradebookApp – curses init, screen router, undo stack
│   ├── database.py          # DatabaseManager – SQLite CRUD + grade calculations
│   ├── models.py            # Dataclasses: User, Class_, Category, Student, …
│   ├── auth.py              # AuthManager – register / login / SHA-256 hashing
│   ├── reports.py           # ReportGenerator – text reports + file export
│   ├── utils.py             # Helpers: format_grade, calculate_letter_grade, …
│   └── ui/
│       ├── __init__.py
│       ├── theme.py         # ThemeManager + 4 colour themes
│       ├── widgets.py       # Reusable widgets: Menu, Form, Dialog, Table, …
│       ├── splash.py        # Animated ASCII-art splash screen
│       └── screens.py       # All application screens
```

---

## Features

### User Accounts
- Register / login with SHA-256 hashed passwords stored in SQLite
- Persistent sessions (logout returns to login screen)

### Class Management
- Create, edit, delete classes (name, section, semester, year)
- Per-class grade scale (customisable letter thresholds)

### Weighted Assignment Categories
- Custom categories per class (e.g. Homework 20 %, Quizzes 15 %)
- Validates weights sum to 100 %
- Supports drop-lowest N scores

### Grade Scale
- Percentage ranges mapped to letter grades (A+/A/A-/B+…F)
- Fully editable per class

### Student Management
- Add / edit / remove students (name, student ID, email)
- Per-student grade breakdown with category averages

### Assignment Management
- Assignments within categories (name, max points, due date, description)
- Grade individual students; mark as graded / excused / missing / late

### Grade Calculations
- Weighted average per student
- Class statistics: average, median, high, low
- Per-category averages with drop-lowest support

### Reports
- Individual student report card
- Full class roster with grades
- Class statistics summary
- ASCII grade-distribution histogram
- Export any report to a plain-text file

### Attendance Tracker
- Take daily attendance: Present / Absent / Late / Excused
- Switch between dates; view daily totals

### GPA Calculator
- Add courses with letter grades and credit hours
- Calculates weighted GPA on the 4.0 scale

### Beautiful TUI
- 4 colour themes: **Dark**, **Light**, **Ocean**, **Forest** (switchable live)
- Box-drawing borders, breadcrumb nav bar, bottom status/hint bar
- Scrollable menus, forms with validation, modal confirmation dialogs
- Animated typewriter splash screen
- In-app help screen (press `?` or `F1`)

### Data Safety
- Database backup to any file path
- Database restore from backup
- Graceful error handling — app never crashes on bad input
- Undo stack (up to 50 actions)

---

## Keyboard Reference

| Key | Action |
|-----|--------|
| `↑` / `k` | Move up |
| `↓` / `j` | Move down |
| `Enter` | Select / confirm |
| `Tab` | Next form field |
| `Esc` / `B` | Go back |
| `Q` | Quit / back |
| `A` | Add item |
| `E` | Edit selected |
| `D` | Delete selected |
| `/` | Search / filter |
| `F1` / `?` | Help screen |
| `R` | Reports |
| `G` | Grade entry |
| `P/A/L/E` | Attendance status |

---

## Database

SQLite database stored at `~/.gradebook_pro.db`.  Tables:

- `users` — accounts
- `grade_scales` + `grade_thresholds` — per-user grade scales
- `classes` — courses
- `categories` — weighted assignment categories
- `students` — class enrolments
- `assignments` — tasks within categories
- `grades` — one row per (assignment, student) pair
- `attendance` — daily attendance records

All foreign keys cascade on delete for clean data removal.
