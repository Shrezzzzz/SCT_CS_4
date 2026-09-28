"""
utils.py — KeyTrace
Utility helpers: timestamp formatting, key name resolution, session timer formatting.
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# Timestamp
# ---------------------------------------------------------------------------

def get_timestamp() -> str:
    """Return current time as HH:MM:SS.mmm string."""
    now = datetime.now()
    return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


def get_session_start_label() -> str:
    """Return a human-readable session start string: DD-MM-YYYY HH:MM."""
    return datetime.now().strftime("%d-%m-%Y %H:%M")


# ---------------------------------------------------------------------------
# Key name resolution
# ---------------------------------------------------------------------------

# Map Tkinter keysym strings to friendly display names
_KEY_DISPLAY_MAP: dict[str, str] = {
    "space":        "Space",
    "Return":       "Enter",
    "BackSpace":    "Backspace",
    "Tab":          "Tab",
    "Escape":       "Escape",
    "Delete":       "Delete",
    "Up":           "Up",
    "Down":         "Down",
    "Left":         "Left",
    "Right":        "Right",
    "Home":         "Home",
    "End":          "End",
    "Prior":        "PageUp",
    "Next":         "PageDown",
    "Insert":       "Insert",
    "F1":  "F1",  "F2":  "F2",  "F3":  "F3",  "F4":  "F4",
    "F5":  "F5",  "F6":  "F6",  "F7":  "F7",  "F8":  "F8",
    "F9":  "F9",  "F10": "F10", "F11": "F11", "F12": "F12",
    "Shift_L":   "Shift_L",
    "Shift_R":   "Shift_R",
    "Control_L": "Ctrl_L",
    "Control_R": "Ctrl_R",
    "Alt_L":     "Alt_L",
    "Alt_R":     "Alt_R",
    "Meta_L":    "Cmd_L",
    "Meta_R":    "Cmd_R",
    "Super_L":   "Super_L",
    "Super_R":   "Super_R",
    "Caps_Lock": "CapsLock",
    "Num_Lock":  "NumLock",
    "comma":     ",",
    "period":    ".",
    "slash":     "/",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "bracketleft":  "[",
    "bracketright": "]",
    "minus":     "-",
    "equal":     "=",
    "grave":     "`",
    "exclam":       "!",
    "at":           "@",
    "numbersign":   "#",
    "dollar":       "$",
    "percent":      "%",
    "asciicircum":  "^",
    "ampersand":    "&",
    "asterisk":     "*",
    "parenleft":    "(",
    "parenright":   ")",
    "underscore":   "_",
    "plus":         "+",
    "braceleft":    "{",
    "braceright":   "}",
    "bar":          "|",
    "colon":        ":",
    "quotedbl":     '"',
    "less":         "<",
    "greater":      ">",
    "question":     "?",
    "asciitilde":   "~",
}


def resolve_key_name(event) -> str:
    """
    Convert a Tkinter key event to a clean, human-readable key label.

    Priority:
    1. Map known keysym strings (e.g. 'Return' → 'Enter').
    2. Single printable char  → return the char itself.
    3. Fallback: return the raw keysym.
    """
    keysym: str = event.keysym or ""

    # Direct lookup in display map
    if keysym in _KEY_DISPLAY_MAP:
        return _KEY_DISPLAY_MAP[keysym]

    # Single printable character
    char: str = event.char or ""
    if char and char.isprintable() and len(char) == 1:
        return char

    # Fallback to raw keysym (strip trailing _L/_R duplicates if desired)
    return keysym if keysym else "Unknown"


# ---------------------------------------------------------------------------
# Session timer
# ---------------------------------------------------------------------------

def format_elapsed(seconds: int) -> str:
    """Format integer seconds as  MM:SS  or  HHh MMm SSs  when ≥ 1 h."""
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m:02d}m {s:02d}s"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}h {m:02d}m {s:02d}s"


# ---------------------------------------------------------------------------
# Word / character counting
# ---------------------------------------------------------------------------

def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in *text*."""
    return len(text.split()) if text.strip() else 0


def count_chars(text: str) -> int:
    """Return character count excluding trailing newline added by Tkinter Text."""
    # Tkinter Text always appends a trailing '\n'; strip it for the display count.
    return len(text.rstrip("\n"))
