# SCT_CS_4 — KeyTrace Educational Keylogger

A GUI-based educational keylogger simulator built with Python and Tkinter, developed as **Task 04** of the SkillCraft Technology Cyber Security Internship.

---

## Features

- Capture keystrokes only within the application's typing area
- Real-time keystroke log with millisecond timestamps
- Records KeyDown and KeyRelease events for every key
- Live character and word counter
- Session timer and logged key counter
- Save keystroke logs as a `.txt` file
- Start, Stop, Save Log, and Clear controls
- Filter / search the live keystroke log
- Modern dark/light split cybersecurity interface
- Rounded-panel UI with canvas-drawn elements
- Offline operation — data stored locally only
- Cross-platform: macOS, Windows, Linux

---

## How It Works

This is an **educational keylogger simulator** that listens only to keyboard events inside its own Tkinter text area. No system-wide hooks, no background processes, no network access.

**Workflow:**

1. Click **Start Logging**
2. Type inside the **Typing Area** sandbox
3. Every key event (KeyDown + KeyRelease) is recorded with a timestamp
4. Watch keystrokes stream into the **Keystroke Log** panel in real time
5. Use the **Filter** box to search the log
6. Click **Save Log (.txt)** to export the session

Example log output:

```text
KeyTrace Educational Log
========================

Session Started: 03-10-2026 19:45

14:28:00.490 | KeyDown     | h
14:28:00.612 | KeyDown     | e
14:28:00.750 | KeyDown     | l
14:28:00.912 | KeyDown     | l
14:28:01.104 | KeyDown     | o
14:28:01.220 | KeyDown     | Space
14:28:01.402 | KeyDown     | Enter ↵
```

---

## Technologies Used

- Python 3.9+
- Tkinter (GUI)
- `datetime` — timestamps
- `pathlib` — cross-platform file handling

---

## Requirements

No external dependencies. Everything used is part of Python's standard library.

> Works on macOS, Windows, and Linux.

---

## How to Run

```bash
python3 keytrace/main.py
```

If Tkinter is not installed:

```bash
# macOS (Homebrew)
brew install python-tk

# Ubuntu / Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

---

## Project Structure

```text
SCT_CS_4/
├── keytrace/
│   ├── main.py      # Entry point
│   ├── ui.py        # Full Tkinter UI — layout, panels, widgets, event bindings
│   ├── logger.py    # KeystrokeLogger — session state, log entries, .txt export
│   ├── utils.py     # Helpers — timestamps, key name resolution, counters
│   └── assets/      # Reserved for future icons
├── requirements.txt # No external dependencies
└── README.md
```

---

## UI Overview

| Section | Description |
|---|---|
| **Navbar** | Dark bar with keyboard icon, KeyTrace title, Logging Active/Inactive badge |
| **Left panel** | White card — Typing Area heading, Characters + Words stat cards, typing sandbox, Educational Sandbox notice |
| **Right panel** | Dark navy card — Live Keystroke Log with timestamp, event badge (KeyDown/KeyRelease), captured key chip, filter search box |
| **Action bar** | Start Logging, Stop Logging, Save Log (.txt), Clear buttons + Session timer + Logged Keys counter |
| **Footer** | "Offline Educational Keylogger • Data stored locally only" |

---

## Educational Notice

This project is designed **only for learning purposes**. It captures keystrokes exclusively within its own application window and does **not** monitor system-wide keyboard input. No data is sent anywhere.

---

## Internship

**Organisation:** SkillCraft Technology  
**Domain:** Cyber Security  
**Task:** 04 — Educational Keylogger Simulator
