# SCT_CS_4 — KeyTrace Educational Keylogger

A GUI-based educational keylogger simulator built with Python and Tkinter, developed as **Task 04** of the SkillCraft Technology Cyber Security Internship.

---

## Features

- Capture keystrokes only within the application's typing area
- Real-time keystroke log with timestamps
- Records KeyDown and KeyRelease events
- Live character and word counter
- Session timer and logged key counter
- Save keystroke logs as a `.txt` file
- Start, Stop, Save Log, and Clear controls
- Modern 50/50 light–dark cybersecurity interface
- Offline operation with local data storage only
- Cross-platform: macOS, Windows, Linux

---

## How It Works

This is an **educational keylogger simulator** that listens only to keyboard events inside its own Tkinter text area.

**Workflow:**

1. Start logging
2. Type inside the sandbox
3. Every key event is recorded with a timestamp
4. Save the session as a `.txt` log file

Example log:

```text
14:28:00.490 | KeyDown    | H
14:28:00.612 | KeyDown    | e
14:28:00.750 | KeyDown    | l
14:28:00.912 | KeyDown    | l
14:28:01.104 | KeyDown    | o
14:28:01.220 | KeyDown    | Space
14:28:01.402 | KeyDown    | W
```

---

## Technologies Used

- Python 3
- Tkinter (GUI)
- `datetime` for timestamps
- `pathlib` for cross-platform file handling

---

## Requirements

No external dependencies. Everything used is part of Python's standard library.

> Works on macOS, Windows, and Linux.

---

## How to Run

```bash
python3 keytrace/main.py
```

---

## Usage

1. Click **Start Logging**.
2. Type inside the **Typing Area**.
3. Watch keystrokes appear in the live log.
4. Click **Save Log (.txt)** to export the session.
5. Use **Stop Logging** or **Clear** when finished.

---

## Project Structure

```text
SCT_CS_4/
├── keytrace/
│   ├── main.py      # Entry point
│   ├── ui.py        # Tkinter UI (layout, widgets, event bindings)
│   ├── logger.py    # Keystroke logger (session state, log entries, export)
│   ├── utils.py     # Helpers (timestamps, key names, counters)
│   └── assets/      # Reserved for icons / future assets
├── requirements.txt # No external dependencies
└── README.md        # Project documentation
```

---

## Educational Notice

This project is designed **only for learning purposes**. It captures keystrokes exclusively within its own application window and does **not** monitor system-wide keyboard input.

---

## Internship

**Organisation:** SkillCraft Technology  
**Domain:** Cyber Security  
**Task:** 04 — Educational Keylogger Simulator
