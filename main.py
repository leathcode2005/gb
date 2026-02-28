#!/usr/bin/env python3
"""GradeBook Pro – entry point."""

import curses
from gradebook.app import GradebookApp


def main() -> None:
    """Create and run the GradeBook Pro application."""
    app = GradebookApp()
    app.run()


if __name__ == "__main__":
    main()
