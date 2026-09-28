"""
main.py — KeyTrace
Entry point. Launches the KeyTrace educational keylogger simulator.

Usage
-----
    python3 main.py

Requirements: Python 3.9+ with Tkinter (included in standard CPython distributions).
No third-party packages required.
"""

import sys

# Guard against missing Tkinter (some minimal Linux installs omit it)
try:
    import tkinter as _tk  # noqa: F401
except ImportError:
    print(
        "ERROR: Tkinter is not available in this Python installation.\n"
        "Install it via your package manager, e.g.:\n"
        "  Ubuntu/Debian : sudo apt-get install python3-tk\n"
        "  Fedora        : sudo dnf install python3-tkinter\n"
        "  macOS (brew)  : brew install python-tk\n"
    )
    sys.exit(1)

from ui import KeyTraceApp  # noqa: E402  (import after guard)


def main() -> None:
    """Create and run the KeyTrace application."""
    app = KeyTraceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
