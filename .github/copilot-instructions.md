# Copilot instructions for GradeBook Pro

## Project shape (read first)
- This is a **single-process ncurses TUI** app with no web/server layer. Entry point is `main.py`, which creates `GradebookApp` in `gradebook/app.py`.
- `GradebookApp` owns shared services (`DatabaseManager`, `AuthManager`, `ThemeManager`) and routes screens by string keys via `_route()`.
- Navigation contract: each screen `run()` returns the next route name (for example `"classes"`, `"class_detail"`, `"quit"`).
- Cross-screen state is stored in `app.context` (for example `class_id`, `student_id`, `category_id`, `assignment_id`). Preserve these keys when adding flows.

## Core boundaries
- `gradebook/database.py`: all SQLite schema + CRUD + grade/stat calculations + backup/restore.
- `gradebook/ui/screens.py`: screen logic and user interaction loops.
- `gradebook/ui/widgets.py`: reusable UI primitives (`Menu`, `Form`, `Dialog`, `SearchBox`, `Table`, `ProgressBar`).
- `gradebook/reports.py`: text report generation and export.
- `gradebook/auth.py`: login/register with SHA-256 hashing, plus default grade scale creation.

## Existing implementation patterns to follow
- New screens should inherit `BaseScreen` (`gradebook/ui/screens.py`) and use `_draw_nav(...)`, `_draw_status(...)`, `_confirm(...)`, `_input_dialog(...)` instead of ad-hoc UI code.
- Typical screen loop pattern: clear/fill background, draw content, call `win.getch()`, handle hotkeys, return route string.
- Use widget-safe drawing helpers (`safe_addstr`, `safe_addch`) to avoid curses boundary exceptions.
- Keep keybindings consistent with current UX (`Esc/B` back, `A/E/D` CRUD, `F1/?` help where applicable).
- Keep data access in `DatabaseManager`; do not place SQL directly in UI screens.

## Data and grading semantics (important)
- Grades are upserted per `(assignment_id, student_id)` using `DatabaseManager.upsert_grade()`; avoid duplicate insert logic.
- Grade statuses are meaningful: `graded`, `pending`, `excused`, `missing`, `late`.
- Grade calculations (`calculate_student_grade`) ignore `excused` and `missing`, and apply category `drop_lowest` before weighted averaging.
- Category weights are user-editable and only validated in UI messaging (not hard-enforced in DB); preserve this behavior unless explicitly changing requirements.

## Runtime and validation workflow
- Run app: `python main.py`
- Environment: Python 3.8+ standard library only (no pip dependencies expected).
- There is no automated test suite in this repo; validate changes by running the TUI flow you touched.
- For non-interactive sanity checks, use: `python -m py_compile main.py gradebook/*.py gradebook/ui/*.py`

## Change-scope guidance for agents
- Prefer minimal, surgical edits in existing modules; this codebase is intentionally monolithic in `screens.py`.
- Do not rename route keys or `app.context` keys without updating all call sites.
- If adding new keyboard actions, update the in-app help text in `HelpScreen.HELP_TEXT`.
- If changing report formats, keep them plain-text and compatible with `ReportGenerator.export_to_file()`.