"""
ui.py — KeyTrace
Main application window: 50/50 light-left / dark-right layout matching the mockup.
All keystroke capture is scoped to the Tkinter text widget only.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import (
    count_chars,
    count_words,
    format_elapsed,
    resolve_key_name,
)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C = {
    # Window / chrome
    "win_bg":        "#1e2130",
    "title_bar":     "#1e2130",

    # Left panel (light)
    "left_bg":       "#f0f2f8",
    "card_bg":       "#ffffff",
    "card_border":   "#e2e6f0",
    "text_primary":  "#1a1d2e",
    "text_secondary":"#6b7280",
    "text_muted":    "#9ca3af",

    # Right panel (dark)
    "right_bg":      "#1e2130",
    "right_panel":   "#252839",
    "table_header":  "#1a1d2e",
    "row_alt":       "#2a2d3e",
    "row_hover":     "#2f3347",
    "border_dark":   "#2f3347",

    # Accent
    "blue":          "#3b82f6",
    "blue_dark":     "#2563eb",
    "green":         "#22c55e",
    "green_dark":    "#16a34a",
    "red":           "#ef4444",
    "red_dark":      "#dc2626",
    "amber":         "#f59e0b",
    "slate":         "#64748b",
    "slate_dark":    "#475569",

    # Badges
    "badge_keydown":    "#3b82f6",
    "badge_keyrelease": "#64748b",

    # Status bar
    "status_bar":    "#0f1117",
    "status_text":   "#94a3b8",
}

# ---------------------------------------------------------------------------
# Fonts  (plain tuples — cross-platform safe)
# ---------------------------------------------------------------------------
FONT_TITLE   = ("Segoe UI", 14, "bold")
FONT_HEADING = ("Segoe UI", 11, "bold")
FONT_SUBHEAD = ("Segoe UI",  9, "normal")
FONT_BODY    = ("Segoe UI", 10, "normal")
FONT_SMALL   = ("Segoe UI",  8, "normal")
FONT_MONO    = ("Consolas",  9, "normal")
FONT_MONO_SM = ("Consolas",  8, "normal")
FONT_STAT    = ("Segoe UI", 20, "bold")
FONT_STAT_LB = ("Segoe UI",  8, "bold")
FONT_BTN     = ("Segoe UI", 10, "bold")
FONT_STATUS  = ("Segoe UI",  9, "normal")


# ---------------------------------------------------------------------------
# Helper: rounded-rectangle canvas button
# ---------------------------------------------------------------------------

def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=8, **kwargs):
    """Draw a filled rounded rectangle on *canvas*."""
    pts = [
        x1+r, y1,   x2-r, y1,
        x2, y1,     x2, y1+r,
        x2, y2-r,   x2, y2,
        x2-r, y2,   x1+r, y2,
        x1, y2,     x1, y2-r,
        x1, y1+r,   x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)


# ---------------------------------------------------------------------------
# KeyTrace App
# ---------------------------------------------------------------------------

class KeyTraceApp(tk.Tk):
    """Root window — wires together the left panel, right panel and status bar."""

    # ------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.logger = KeystrokeLogger()
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", self._on_filter_change)

        # All log rows stored for filter re-rendering
        self._all_rows: List[dict] = []

        self._timer_id: str | None = None   # after() handle for clock

        self._setup_window()
        self._build_ui()
        self._update_button_states()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=C["win_bg"])
        self.resizable(True, True)
        self.minsize(900, 580)

        # Center on screen
        self.update_idletasks()
        w, h = 1100, 680
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Top-level layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Title bar row ──────────────────────────────────────────────
        self._build_title_bar()

        # ── Main body (left + right) ───────────────────────────────────
        body = tk.Frame(self, bg=C["win_bg"])
        body.pack(fill=tk.BOTH, expand=True)

        # Left panel — light
        self._left = tk.Frame(body, bg=C["left_bg"])
        self._left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 6), pady=(6, 0))

        # Right panel — dark
        self._right = tk.Frame(body, bg=C["right_bg"])
        self._right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 12), pady=(6, 0))

        self._build_left_panel()
        self._build_right_panel()

        # ── Button bar ─────────────────────────────────────────────────
        self._build_button_bar()

        # ── Status bar ─────────────────────────────────────────────────
        self._build_status_bar()

    # ------------------------------------------------------------------
    # Title bar
    # ------------------------------------------------------------------

    def _build_title_bar(self) -> None:
        bar = tk.Frame(self, bg=C["title_bar"], height=46)
        bar.pack(fill=tk.X, padx=0, pady=0)
        bar.pack_propagate(False)

        # Left: icon + app name
        left = tk.Frame(bar, bg=C["title_bar"])
        left.pack(side=tk.LEFT, padx=16)

        icon_lbl = tk.Label(left, text="⌨", font=("Segoe UI", 14), bg=C["title_bar"], fg="#94a3b8")
        icon_lbl.pack(side=tk.LEFT, padx=(0, 6))

        tk.Label(
            left, text="KeyTrace",
            font=FONT_TITLE, bg=C["title_bar"], fg="#f1f5f9"
        ).pack(side=tk.LEFT)

        # Right: logging-active badge
        right = tk.Frame(bar, bg=C["title_bar"])
        right.pack(side=tk.RIGHT, padx=16)

        self._badge_frame = tk.Frame(right, bg=C["title_bar"])
        self._badge_frame.pack(side=tk.RIGHT)

        self._badge_dot = tk.Label(
            self._badge_frame, text="●", font=("Segoe UI", 9),
            bg=C["title_bar"], fg=C["slate"]
        )
        self._badge_dot.pack(side=tk.LEFT, padx=(0, 4))

        self._badge_lbl = tk.Label(
            self._badge_frame,
            text="Logging Inactive",
            font=("Segoe UI", 9, "bold"),
            bg=C["title_bar"], fg=C["slate"]
        )
        self._badge_lbl.pack(side=tk.LEFT)

        # Thin separator line
        sep = tk.Frame(self, bg="#2f3347", height=1)
        sep.pack(fill=tk.X)

    # ------------------------------------------------------------------
    # LEFT panel
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> None:
        p = self._left

        # ── Typing Area card ──────────────────────────────────────────
        card = self._make_card(p)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Card header
        hdr = tk.Frame(card, bg=C["card_bg"])
        hdr.pack(fill=tk.X, padx=16, pady=(14, 4))

        tk.Label(
            hdr, text="✏  Typing Area",
            font=FONT_HEADING, bg=C["card_bg"], fg=C["text_primary"]
        ).pack(anchor=tk.W)

        tk.Label(
            hdr,
            text="Type into this sandbox to simulate & capture keystrokes in real time.",
            font=FONT_SUBHEAD, bg=C["card_bg"], fg=C["text_secondary"],
            wraplength=340, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(2, 0))

        # Separator
        tk.Frame(card, bg=C["card_border"], height=1).pack(fill=tk.X, padx=16, pady=(8, 10))

        # Stat cards row
        stat_row = tk.Frame(card, bg=C["card_bg"])
        stat_row.pack(fill=tk.X, padx=16, pady=(0, 10))
        stat_row.columnconfigure(0, weight=1)
        stat_row.columnconfigure(1, weight=1)

        self._char_var = tk.StringVar(value="0")
        self._word_var = tk.StringVar(value="0")

        self._char_card = self._make_stat_card(stat_row, "CHARACTERS", self._char_var, "⌨", 0)
        self._word_card = self._make_stat_card(stat_row, "WORDS",      self._word_var, "≡", 1)

        # Text widget (typing sandbox)
        txt_frame = tk.Frame(card, bg=C["card_border"], bd=1, relief=tk.FLAT)
        txt_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))

        self._text_area = tk.Text(
            txt_frame,
            font=("Segoe UI", 10),
            bg=C["card_bg"],
            fg=C["text_primary"],
            insertbackground=C["blue"],
            relief=tk.FLAT,
            bd=8,
            wrap=tk.WORD,
            undo=True,
            selectbackground=C["blue"],
            selectforeground="#ffffff",
            highlightthickness=0,
        )
        self._text_area.pack(fill=tk.BOTH, expand=True)

        # Bind key events
        self._text_area.bind("<Key>",        self._on_key_press)
        self._text_area.bind("<KeyRelease>", self._on_key_release)
        self._text_area.bind("<<Modified>>", self._on_text_modified)

        # Footer disclaimer
        disc = tk.Frame(card, bg=C["card_bg"])
        disc.pack(fill=tk.X, padx=16, pady=(4, 14))

        tk.Label(
            disc,
            text="🛡  Educational Sandbox • Keys logged only within this application window",
            font=FONT_SMALL, bg=C["card_bg"], fg=C["text_muted"],
            wraplength=340, justify=tk.LEFT
        ).pack(anchor=tk.W)

    def _make_card(self, parent) -> tk.Frame:
        """Return a white rounded-style card frame."""
        outer = tk.Frame(parent, bg=C["left_bg"], bd=0)
        card = tk.Frame(
            outer,
            bg=C["card_bg"],
            highlightbackground=C["card_border"],
            highlightthickness=1,
        )
        card.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        return card

    def _make_stat_card(
        self, parent: tk.Frame, label: str, var: tk.StringVar, icon: str, col: int
    ) -> tk.Frame:
        """Return a small statistics card placed in *parent* at column *col*."""
        outer = tk.Frame(
            parent, bg=C["card_border"],
            highlightbackground=C["card_border"],
            highlightthickness=1,
        )
        outer.grid(row=0, column=col, padx=(0 if col else 0, 4 if col == 0 else 0), sticky="nsew")

        inner = tk.Frame(outer, bg=C["card_bg"], padx=10, pady=8)
        inner.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(inner, bg=C["card_bg"])
        top.pack(fill=tk.X)

        tk.Label(
            top, text=label,
            font=FONT_STAT_LB, bg=C["card_bg"], fg=C["text_muted"]
        ).pack(side=tk.LEFT)

        tk.Label(
            top, text=icon,
            font=("Segoe UI", 10), bg=C["card_bg"], fg=C["text_muted"]
        ).pack(side=tk.RIGHT)

        tk.Label(
            inner, textvariable=var,
            font=FONT_STAT, bg=C["card_bg"], fg=C["text_primary"]
        ).pack(anchor=tk.W, pady=(2, 0))

        return outer

    # ------------------------------------------------------------------
    # RIGHT panel
    # ------------------------------------------------------------------

    def _build_right_panel(self) -> None:
        p = self._right

        rcard = tk.Frame(
            p, bg=C["right_panel"],
            highlightbackground=C["border_dark"],
            highlightthickness=1,
        )
        rcard.pack(fill=tk.BOTH, expand=True)

        # ── Header row ────────────────────────────────────────────────
        hdr = tk.Frame(rcard, bg=C["right_panel"])
        hdr.pack(fill=tk.X, padx=16, pady=(14, 6))

        left_hdr = tk.Frame(hdr, bg=C["right_panel"])
        left_hdr.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            left_hdr, text="⌨  Keystroke Log",
            font=FONT_HEADING, bg=C["right_panel"], fg="#f1f5f9"
        ).pack(anchor=tk.W)

        tk.Label(
            left_hdr,
            text="Chronological event stream with instant keycap resolution.",
            font=FONT_SUBHEAD, bg=C["right_panel"], fg="#64748b"
        ).pack(anchor=tk.W, pady=(2, 0))

        # Filter box
        filter_frame = tk.Frame(
            hdr, bg="#1a1d2e",
            highlightbackground=C["border_dark"],
            highlightthickness=1,
        )
        filter_frame.pack(side=tk.RIGHT, padx=(8, 0))

        tk.Label(
            filter_frame, text="🔍", font=("Segoe UI", 9),
            bg="#1a1d2e", fg="#64748b"
        ).pack(side=tk.LEFT, padx=(8, 2), pady=6)

        self._filter_entry = tk.Entry(
            filter_frame,
            textvariable=self._filter_var,
            font=FONT_MONO_SM,
            bg="#1a1d2e",
            fg="#94a3b8",
            insertbackground="#94a3b8",
            relief=tk.FLAT,
            bd=0,
            width=18,
        )
        self._filter_entry.pack(side=tk.LEFT, padx=(0, 8), pady=6)
        self._filter_entry.insert(0, "Filter keystrokes...")
        self._filter_entry.bind("<FocusIn>",  self._filter_focus_in)
        self._filter_entry.bind("<FocusOut>", self._filter_focus_out)

        # ── Column headers ────────────────────────────────────────────
        col_hdr = tk.Frame(rcard, bg=C["table_header"])
        col_hdr.pack(fill=tk.X, padx=16, pady=(4, 0))

        for text, w in [("TIMESTAMP", 130), ("EVENT", 100), ("CAPTURED KEY", 140)]:
            tk.Label(
                col_hdr, text=text,
                font=("Segoe UI", 7, "bold"),
                bg=C["table_header"], fg="#64748b",
                width=0, anchor=tk.W, padx=6, pady=6
            ).pack(side=tk.LEFT, ipadx=4)

        tk.Frame(rcard, bg=C["border_dark"], height=1).pack(fill=tk.X, padx=16)

        # ── Scrollable log list ───────────────────────────────────────
        list_frame = tk.Frame(rcard, bg=C["right_panel"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, width=8)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_canvas = tk.Canvas(
            list_frame,
            bg=C["right_panel"],
            bd=0, highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        self._log_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._log_canvas.yview)

        self._log_inner = tk.Frame(self._log_canvas, bg=C["right_panel"])
        self._log_canvas_window = self._log_canvas.create_window(
            (0, 0), window=self._log_inner, anchor="nw"
        )

        self._log_inner.bind("<Configure>", self._on_log_inner_configure)
        self._log_canvas.bind("<Configure>", self._on_log_canvas_configure)

        # Mouse-wheel scrolling (cross-platform)
        self._log_canvas.bind("<MouseWheel>",       self._on_mousewheel)
        self._log_canvas.bind("<Button-4>",         self._on_mousewheel)
        self._log_canvas.bind("<Button-5>",         self._on_mousewheel)
        self._log_inner.bind("<MouseWheel>",        self._on_mousewheel)

    # ------------------------------------------------------------------
    # Button bar
    # ------------------------------------------------------------------

    def _build_button_bar(self) -> None:
        bar = tk.Frame(self, bg=C["win_bg"], pady=10)
        bar.pack(fill=tk.X, padx=12)

        btn_left = tk.Frame(bar, bg=C["win_bg"])
        btn_left.pack(side=tk.LEFT)

        self._btn_start = self._make_button(
            btn_left, "▶  Start Logging", C["blue"], C["blue_dark"], self._start_logging
        )
        self._btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_stop = self._make_button(
            btn_left, "⏹  Stop Logging", C["slate"], C["slate_dark"], self._stop_logging
        )
        self._btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_save = self._make_button(
            btn_left, "💾  Save Log (.txt)", C["green"], C["green_dark"], self._save_log
        )
        self._btn_save.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_clear = self._make_button(
            btn_left, "🗑  Clear", C["red"], C["red_dark"], self._clear_log,
            outline=True
        )
        self._btn_clear.pack(side=tk.LEFT)

        # Right side — session info
        info_frame = tk.Frame(bar, bg=C["win_bg"])
        info_frame.pack(side=tk.RIGHT, padx=(0, 4))

        # Session timer
        timer_box = tk.Frame(
            info_frame, bg="#252839",
            highlightbackground=C["border_dark"], highlightthickness=1
        )
        timer_box.pack(side=tk.LEFT, padx=(0, 10), ipady=6, ipadx=10)

        tk.Label(
            timer_box, text="⏱", font=("Segoe UI", 10),
            bg="#252839", fg="#64748b"
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Label(
            timer_box, text="Session:",
            font=FONT_STATUS, bg="#252839", fg="#94a3b8"
        ).pack(side=tk.LEFT)

        self._timer_var = tk.StringVar(value="00m 00s")
        tk.Label(
            timer_box, textvariable=self._timer_var,
            font=("Segoe UI", 9, "bold"), bg="#252839", fg="#f1f5f9"
        ).pack(side=tk.LEFT, padx=(4, 0))

        # Logged keys
        keys_box = tk.Frame(
            info_frame, bg="#252839",
            highlightbackground=C["border_dark"], highlightthickness=1
        )
        keys_box.pack(side=tk.LEFT, ipady=6, ipadx=10)

        tk.Label(
            keys_box, text="Logged Keys:",
            font=FONT_STATUS, bg="#252839", fg="#94a3b8"
        ).pack(side=tk.LEFT)

        self._keys_var = tk.StringVar(value="0")
        tk.Label(
            keys_box, textvariable=self._keys_var,
            font=("Segoe UI", 9, "bold"), bg="#252839", fg=C["blue"]
        ).pack(side=tk.LEFT, padx=(4, 0))

    def _make_button(
        self,
        parent: tk.Frame,
        text: str,
        color: str,
        hover_color: str,
        command,
        outline: bool = False,
    ) -> tk.Button:
        """Return a styled flat Tkinter Button."""
        if outline:
            btn = tk.Button(
                parent,
                text=text,
                font=FONT_BTN,
                bg=C["win_bg"],
                fg=color,
                activebackground=C["win_bg"],
                activeforeground=hover_color,
                relief=tk.FLAT,
                bd=0,
                padx=16, pady=8,
                cursor="hand2",
                command=command,
                highlightbackground=color,
                highlightthickness=1,
            )
        else:
            btn = tk.Button(
                parent,
                text=text,
                font=FONT_BTN,
                bg=color,
                fg="#ffffff",
                activebackground=hover_color,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                padx=16, pady=8,
                cursor="hand2",
                command=command,
            )
        return btn

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg=C["status_bar"], height=30)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=C["status_bar"])
        inner.pack(fill=tk.Y, side=tk.LEFT, padx=14)

        tk.Label(
            inner,
            text="🛡  Offline Educational Keylogger  •  Data stored locally only",
            font=FONT_STATUS,
            bg=C["status_bar"],
            fg=C["status_text"],
        ).pack(side=tk.LEFT, pady=5)

    # ------------------------------------------------------------------
    # Event handlers — key capture
    # ------------------------------------------------------------------

    def _on_key_press(self, event: tk.Event) -> None:
        if event.keysym in ("Tab",):
            # Let Tab move focus; don't capture it
            return
        key_name = resolve_key_name(event)
        entry = self.logger.record("KeyDown", key_name)
        if entry:
            self._append_log_row(entry)
            self._keys_var.set(str(self.logger.entry_count))

    def _on_key_release(self, event: tk.Event) -> None:
        key_name = resolve_key_name(event)
        entry = self.logger.record("KeyRelease", key_name)
        if entry:
            self._append_log_row(entry)
            self._keys_var.set(str(self.logger.entry_count))

    def _on_text_modified(self, event: tk.Event) -> None:
        """Update character and word counts whenever the text changes."""
        # Reset the modified flag so we keep getting events
        self._text_area.edit_modified(False)
        text = self._text_area.get("1.0", tk.END)
        self._char_var.set(str(count_chars(text)))
        self._word_var.set(str(count_words(text)))

    # ------------------------------------------------------------------
    # Log row rendering
    # ------------------------------------------------------------------

    def _append_log_row(self, entry: "LogEntry") -> None:
        """Add a new row to the top of the log panel (newest first)."""
        row_data = {
            "timestamp":  entry.timestamp,
            "event_type": entry.event_type,
            "key":        entry.key,
        }
        self._all_rows.insert(0, row_data)
        self._render_log_rows()

    def _render_log_rows(self) -> None:
        """Rebuild the visible log rows (respecting filter)."""
        # Destroy existing rows
        for widget in self._log_inner.winfo_children():
            widget.destroy()

        flt = self._filter_var.get().lower().strip()
        # Ignore placeholder text
        if flt == "filter keystrokes...":
            flt = ""

        visible = [
            r for r in self._all_rows
            if not flt or flt in r["timestamp"].lower()
               or flt in r["event_type"].lower()
               or flt in r["key"].lower()
        ] if flt else self._all_rows

        for i, row in enumerate(visible):
            bg = C["right_panel"] if i % 2 == 0 else C["row_alt"]
            self._build_log_row(self._log_inner, row, bg, i)

    def _build_log_row(self, parent: tk.Frame, row: dict, bg: str, idx: int) -> None:
        """Render a single log table row."""
        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill=tk.X)

        # Left accent bar (blue for KeyDown, grey for KeyRelease)
        accent_color = C["badge_keydown"] if row["event_type"] == "KeyDown" else C["badge_keyrelease"]
        tk.Frame(frame, bg=accent_color, width=3).pack(side=tk.LEFT, fill=tk.Y)

        # Timestamp
        tk.Label(
            frame,
            text=row["timestamp"],
            font=FONT_MONO,
            bg=bg, fg="#94a3b8",
            width=14, anchor=tk.W,
            padx=8, pady=5,
        ).pack(side=tk.LEFT)

        # Event badge
        if row["event_type"] == "KeyDown":
            badge_bg   = C["badge_keydown"]
            badge_fg   = "#ffffff"
        else:
            badge_bg   = C["badge_keyrelease"]
            badge_fg   = "#e2e8f0"

        badge_frame = tk.Frame(frame, bg=badge_bg, padx=6, pady=2)
        badge_frame.pack(side=tk.LEFT, padx=(0, 16), pady=4)
        tk.Label(
            badge_frame,
            text=row["event_type"],
            font=("Segoe UI", 8, "bold"),
            bg=badge_bg, fg=badge_fg,
        ).pack()

        # Key chip
        key_text = f"[{row['key']}]"

        # Special key highlight colours
        special_colours = {
            "Enter":     (C["blue"],  "#ffffff"),
            "Backspace": (C["amber"], "#1a1d2e"),
            "Space":     ("#334155",  "#94a3b8"),
            "Escape":    (C["red"],   "#ffffff"),
            "Tab":       ("#7c3aed",  "#ffffff"),
        }
        chip_bg, chip_fg = special_colours.get(row["key"], ("#2f3347", "#e2e8f0"))

        chip = tk.Frame(frame, bg=chip_bg, padx=6, pady=2)
        chip.pack(side=tk.RIGHT, padx=10, pady=4)
        tk.Label(
            chip,
            text=key_text,
            font=FONT_MONO,
            bg=chip_bg, fg=chip_fg,
        ).pack()

    # ------------------------------------------------------------------
    # Canvas scrolling
    # ------------------------------------------------------------------

    def _on_log_inner_configure(self, event) -> None:
        self._log_canvas.configure(
            scrollregion=self._log_canvas.bbox("all")
        )

    def _on_log_canvas_configure(self, event) -> None:
        self._log_canvas.itemconfig(
            self._log_canvas_window, width=event.width
        )

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.num == 4:
            self._log_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._log_canvas.yview_scroll(1, "units")
        else:
            delta = -1 if event.delta > 0 else 1
            self._log_canvas.yview_scroll(delta, "units")

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _filter_focus_in(self, event) -> None:
        if self._filter_entry.get() == "Filter keystrokes...":
            self._filter_entry.delete(0, tk.END)
            self._filter_entry.config(fg="#e2e8f0")

    def _filter_focus_out(self, event) -> None:
        if not self._filter_entry.get():
            self._filter_entry.insert(0, "Filter keystrokes...")
            self._filter_entry.config(fg="#64748b")

    def _on_filter_change(self, *_) -> None:
        self._render_log_rows()

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------

    def _start_logging(self) -> None:
        self.logger.start()
        self._update_button_states()
        self._update_badge(active=True)
        self._text_area.focus_set()
        self._tick_timer()

    def _stop_logging(self) -> None:
        self.logger.stop()
        self._update_button_states()
        self._update_badge(active=False)
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _save_log(self) -> None:
        if self.logger.entry_count == 0:
            messagebox.showinfo(
                "KeyTrace", "No keystrokes to save yet.\nStart logging and type something first."
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Keystroke Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="keytrace_log.txt",
        )
        if not filepath:
            return  # User cancelled

        try:
            self.logger.save(filepath)
            messagebox.showinfo(
                "KeyTrace", f"Log saved successfully:\n{filepath}"
            )
        except OSError as exc:
            messagebox.showerror("KeyTrace", f"Could not save file:\n{exc}")

    def _clear_log(self) -> None:
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

        self.logger.clear()
        self._all_rows.clear()

        # Clear typing area
        self._text_area.delete("1.0", tk.END)

        # Reset counters
        self._char_var.set("0")
        self._word_var.set("0")
        self._keys_var.set("0")
        self._timer_var.set("00m 00s")

        # Clear log panel
        for widget in self._log_inner.winfo_children():
            widget.destroy()

        self._update_button_states()
        self._update_badge(active=False)

    # ------------------------------------------------------------------
    # UI state helpers
    # ------------------------------------------------------------------

    def _update_button_states(self) -> None:
        active = self.logger.is_active
        self._btn_start.config(state=tk.DISABLED if active else tk.NORMAL)
        self._btn_stop.config( state=tk.NORMAL   if active else tk.DISABLED)

    def _update_badge(self, active: bool) -> None:
        if active:
            self._badge_dot.config(fg=C["green"])
            self._badge_lbl.config(text="Logging Active", fg=C["green"])
        else:
            self._badge_dot.config(fg=C["slate"])
            self._badge_lbl.config(text="Logging Inactive", fg=C["slate"])

    def _tick_timer(self) -> None:
        """Update the session timer label every second."""
        if not self.logger.is_active:
            return
        elapsed = self.logger.session_elapsed_seconds
        self._timer_var.set(format_elapsed(elapsed))
        self._timer_id = self.after(1000, self._tick_timer)
