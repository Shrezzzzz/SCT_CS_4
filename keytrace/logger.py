"""
logger.py — KeyTrace
KeystrokeLogger: manages session state, log entries, and .txt export.
No system-wide hooks — only processes events forwarded from the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from utils import get_timestamp, get_session_start_label


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    """A single keystroke event record."""
    timestamp: str          # HH:MM:SS.mmm
    event_type: str         # "KeyDown" or "KeyRelease"
    key: str                # Human-readable key label


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

class KeystrokeLogger:
    """
    Manages keystroke log entries and session metadata.

    Usage
    -----
    logger = KeystrokeLogger()
    logger.start()
    logger.record("KeyDown", "h")
    logger.stop()
    logger.save("/path/to/file.txt")
    """

    def __init__(self) -> None:
        self._entries: List[LogEntry] = []
        self._active: bool = False
        self._session_start: datetime | None = None
        self._session_start_label: str = ""

    # ------------------------------------------------------------------
    # Session control
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin a logging session (idempotent if already active)."""
        if not self._active:
            self._active = True
            self._session_start = datetime.now()
            self._session_start_label = get_session_start_label()

    def stop(self) -> None:
        """Pause logging (entries are preserved)."""
        self._active = False

    def clear(self) -> None:
        """Wipe all entries and reset session."""
        self._entries.clear()
        self._active = False
        self._session_start = None
        self._session_start_label = ""

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, event_type: str, key: str) -> LogEntry | None:
        """
        Record a keystroke if the session is active.

        Parameters
        ----------
        event_type : "KeyDown" or "KeyRelease"
        key        : Human-readable key label (from utils.resolve_key_name)

        Returns the new LogEntry, or None if logging is paused.
        """
        if not self._active:
            return None
        entry = LogEntry(
            timestamp=get_timestamp(),
            event_type=event_type,
            key=key,
        )
        self._entries.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> List[LogEntry]:
        """Read-only view of all recorded entries."""
        return list(self._entries)

    @property
    def session_elapsed_seconds(self) -> int:
        """Seconds elapsed since session start (0 if not started)."""
        if self._session_start is None:
            return 0
        return int((datetime.now() - self._session_start).total_seconds())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def build_log_text(self) -> str:
        """Return the full log content as a formatted string."""
        lines: list[str] = [
            "KeyTrace Educational Log",
            "========================",
            "",
            f"Session Started: {self._session_start_label}",
            "",
        ]
        for entry in self._entries:
            # Pad event_type to 10 chars for alignment
            etype = entry.event_type.ljust(10)
            lines.append(f"{entry.timestamp} | {etype} | {entry.key}")

        lines.append("")
        lines.append(f"Total keystrokes logged: {len(self._entries)}")
        return "\n".join(lines)

    def save(self, filepath: str | Path) -> None:
        """
        Write the log to *filepath* as UTF-8 text.

        Raises
        ------
        OSError  if the file cannot be written.
        """
        path = Path(filepath)
        path.write_text(self.build_log_text(), encoding="utf-8")
