"""
ui.py — KeyTrace
Main application window. Matches the mockup exactly:
  - Light grey window background
  - Left white card: Typing Area + stat cards + text sandbox
  - Right dark navy card: Keystroke Log table (newest first)
  - Button bar on light grey background
  - Dark status bar at bottom
All keystroke capture is scoped to the Tkinter text widget only.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ---------------------------------------------------------------------------
# Colour palette  (matched pixel-by-pixel to the mockup)
# ---------------------------------------------------------------------------
C = {
    # App chrome
    "app_bg":           "#e8eaf2",   # light grey page background
    "titlebar_bg":      "#1c1f2e",   # very dark navy title bar
    "titlebar_fg":      "#f1f5f9",
    "titlebar_sub":     "#94a3b8",

    # Left white card
    "card_bg":          "#ffffff",
    "card_border":      "#e2e6f0",
    "text_primary":     "#111827",
    "text_secondary":   "#6b7280",
    "text_muted":       "#9ca3af",

    # Stat mini-cards
    "stat_bg":          "#ffffff",
    "stat_border":      "#e2e6f0",

    # Text area
    "textarea_bg":      "#ffffff",
    "textarea_border":  "#d1d5db",
    "textarea_cursor":  "#3b82f6",

    # Right dark card
    "log_card_bg":      "#1e2235",
    "log_card_border":  "#2d3148",
    "log_hdr_sub":      "#64748b",
    "col_hdr_bg":       "#191c2a",
    "col_hdr_fg":       "#64748b",
    "row_even":         "#1e2235",
    "row_odd":          "#242840",
    "row_sep":          "#2d3148",
    "ts_fg":            "#94a3b8",

    # Filter box
    "filter_bg":        "#161929",
    "filter_border":    "#2d3148",
    "filter_fg":        "#64748b",

    # Accent colours
    "blue":             "#3b82f6",
    "blue_dark":        "#2563eb",
    "blue_dim":         "#1d4ed8",
    "green":            "#22c55e",
    "green_dark":       "#16a34a",
    "red":              "#ef4444",
    "red_dark":         "#dc2626",
    "amber":            "#f59e0b",
    "slate":            "#64748b",
    "slate_dark":       "#475569",
    "purple":           "#7c3aed",

    # Event badge colours
    "kd_bg":            "#3b82f6",   # KeyDown  badge
    "kd_fg":            "#ffffff",
    "kr_bg":            "#475569",   # KeyRelease badge
    "kr_fg":            "#e2e8f0",

    # Button bar
    "btnbar_bg":        "#e8eaf2",
    "info_box_bg":      "#e8eaf2",
    "info_box_border":  "#d1d5db",
    "info_label_fg":    "#6b7280",
    "info_value_fg":    "#111827",
    "session_value_fg": "#3b82f6",

    # Status bar
    "statusbar_bg":     "#111827",
    "statusbar_fg":     "#94a3b8",
}

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
F = {
    "title":     ("Segoe UI", 13, "bold"),
    "heading":   ("Segoe UI", 12, "bold"),
    "subhead":   ("Segoe UI",  9),
    "body":      ("Segoe UI", 10),
    "small":     ("Segoe UI",  8),
    "stat_lbl":  ("Segoe UI",  8, "bold"),
    "stat_val":  ("Segoe UI", 22, "bold"),
    "col_hdr":   ("Segoe UI",  7, "bold"),
    "mono":      ("Consolas",  9),
    "mono_sm":   ("Consolas",  8),
    "badge":     ("Segoe UI",  8, "bold"),
    "chip":      ("Consolas",  9),
    "btn":       ("Segoe UI", 10, "bold"),
    "status":    ("Segoe UI",  9),
    "badge_dot": ("Segoe UI", 10, "bold"),
}


# ---------------------------------------------------------------------------
# KeyTrace Application
# ---------------------------------------------------------------------------

class KeyTraceApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.logger = KeystrokeLogger()
        self._all_rows: List[dict] = []
        self._timer_id: str | None = None
        self._filter_placeholder = "Filter keystrokes..."
        self._filter_active = False   # True when user is typing in filter

        self._setup_window()
        self._build_ui()
        self._update_button_states()

    # ------------------------------------------------------------------ window
    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=C["app_bg"])
        self.resizable(True, True)
        self.minsize(960, 600)
        self.update_idletasks()
        W, H = 1120, 700
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

    # ------------------------------------------------------------------ root UI
    def _build_ui(self) -> None:
        self._build_titlebar()

        # body sits below title bar, above button bar
        self._body = tk.Frame(self, bg=C["app_bg"])
        self._body.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 0))

        self._build_left_card()
        self._build_right_card()
        self._build_button_bar()
        self._build_status_bar()

    # ------------------------------------------------------------------ title bar
    def _build_titlebar(self) -> None:
        bar = tk.Frame(self, bg=C["titlebar_bg"], height=44)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # left — icon + name
        lf = tk.Frame(bar, bg=C["titlebar_bg"])
        lf.pack(side=tk.LEFT, padx=16, pady=0)

        tk.Label(lf, text="⌨", font=("Segoe UI", 13),
                 bg=C["titlebar_bg"], fg=C["titlebar_sub"]).pack(side=tk.LEFT, padx=(0, 7))
        tk.Label(lf, text="KeyTrace", font=F["title"],
                 bg=C["titlebar_bg"], fg=C["titlebar_fg"]).pack(side=tk.LEFT)

        # right — status badge (green pill when active)
        rf = tk.Frame(bar, bg=C["titlebar_bg"])
        rf.pack(side=tk.RIGHT, padx=16)

        # Pill container
        self._pill = tk.Frame(rf, bg=C["titlebar_bg"],
                              highlightbackground="#2d3148", highlightthickness=1)
        self._pill.pack(side=tk.RIGHT)

        self._pill_dot = tk.Label(self._pill, text="●", font=("Segoe UI", 8),
                                  bg=C["titlebar_bg"], fg=C["slate"])
        self._pill_dot.pack(side=tk.LEFT, padx=(10, 3), pady=6)

        self._pill_lbl = tk.Label(self._pill, text="Logging Inactive",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=C["titlebar_bg"], fg=C["slate"])
        self._pill_lbl.pack(side=tk.LEFT, padx=(0, 10), pady=6)

        # bottom border
        tk.Frame(self, bg="#2a2d3e", height=1).pack(fill=tk.X)

    # ------------------------------------------------------------------ LEFT card
    def _build_left_card(self) -> None:
        # Outer wrapper — fills left 42% of body
        self._left_wrap = tk.Frame(self._body, bg=C["app_bg"])
        self._left_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                             padx=(0, 8), pady=(0, 10))

        # White card with border
        card = tk.Frame(self._left_wrap, bg=C["card_bg"],
                        highlightbackground=C["card_border"], highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)
        self._left_card = card

        # ── heading ──────────────────────────────────────────────────
        hdr = tk.Frame(card, bg=C["card_bg"])
        hdr.pack(fill=tk.X, padx=20, pady=(18, 4))

        title_row = tk.Frame(hdr, bg=C["card_bg"])
        title_row.pack(anchor=tk.W)
        tk.Label(title_row, text="✏", font=("Segoe UI", 11),
                 bg=C["card_bg"], fg=C["text_secondary"]).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(title_row, text="Typing Area", font=F["heading"],
                 bg=C["card_bg"], fg=C["text_primary"]).pack(side=tk.LEFT)

        tk.Label(hdr,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=F["subhead"], bg=C["card_bg"], fg=C["text_secondary"],
                 wraplength=360, justify=tk.LEFT).pack(anchor=tk.W, pady=(3, 0))

        # thin rule
        tk.Frame(card, bg=C["card_border"], height=1).pack(fill=tk.X, padx=20, pady=(12, 10))

        # ── stat cards ───────────────────────────────────────────────
        stat_row = tk.Frame(card, bg=C["card_bg"])
        stat_row.pack(fill=tk.X, padx=20, pady=(0, 12))
        stat_row.columnconfigure(0, weight=1, uniform="stat")
        stat_row.columnconfigure(1, weight=1, uniform="stat")

        self._char_var = tk.StringVar(value="0")
        self._word_var = tk.StringVar(value="0")
        self._make_stat_card(stat_row, "CHARACTERS", self._char_var, "⌨", 0)
        self._make_stat_card(stat_row, "WORDS",      self._word_var, "≡", 1)

        # ── text sandbox ─────────────────────────────────────────────
        txt_wrap = tk.Frame(card, bg=C["textarea_border"], highlightthickness=0)
        txt_wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 6))

        self._text_area = tk.Text(
            txt_wrap,
            font=F["body"],
            bg=C["textarea_bg"],
            fg=C["text_primary"],
            insertbackground=C["textarea_cursor"],
            relief=tk.FLAT, bd=10,
            wrap=tk.WORD, undo=True,
            selectbackground=C["blue"],
            selectforeground="#ffffff",
            highlightthickness=0,
        )
        self._text_area.pack(fill=tk.BOTH, expand=True)

        self._text_area.bind("<Key>",        self._on_key_press)
        self._text_area.bind("<KeyRelease>", self._on_key_release)
        self._text_area.bind("<<Modified>>", self._on_text_modified)

        # ── footer disclaimer ────────────────────────────────────────
        disc = tk.Frame(card, bg=C["card_bg"])
        disc.pack(fill=tk.X, padx=20, pady=(4, 16))

        disc_inner = tk.Frame(disc, bg=C["card_bg"])
        disc_inner.pack(anchor=tk.W)
        tk.Label(disc_inner, text="✓", font=("Segoe UI", 9),
                 bg=C["card_bg"], fg=C["blue"]).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(disc_inner,
                 text="Educational Sandbox • Keys logged only within this application window",
                 font=F["small"], bg=C["card_bg"], fg=C["text_muted"],
                 wraplength=340, justify=tk.LEFT).pack(side=tk.LEFT)

    def _make_stat_card(self, parent, label, var, icon, col):
        pad = (0, 6) if col == 0 else (0, 0)
        outer = tk.Frame(parent, bg=C["stat_border"],
                         highlightbackground=C["stat_border"], highlightthickness=1)
        outer.grid(row=0, column=col, sticky="nsew", padx=pad)

        inner = tk.Frame(outer, bg=C["stat_bg"], padx=12, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(inner, bg=C["stat_bg"])
        top.pack(fill=tk.X)
        tk.Label(top, text=label, font=F["stat_lbl"],
                 bg=C["stat_bg"], fg=C["text_muted"]).pack(side=tk.LEFT)
        tk.Label(top, text=icon, font=("Segoe UI", 10),
                 bg=C["stat_bg"], fg=C["text_muted"]).pack(side=tk.RIGHT)

        tk.Label(inner, textvariable=var, font=F["stat_val"],
                 bg=C["stat_bg"], fg=C["text_primary"]).pack(anchor=tk.W, pady=(2, 0))

    # ------------------------------------------------------------------ RIGHT card
    def _build_right_card(self) -> None:
        self._right_wrap = tk.Frame(self._body, bg=C["app_bg"])
        self._right_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                              padx=(8, 0), pady=(0, 10))

        # Dark rounded card
        card = tk.Frame(self._right_wrap, bg=C["log_card_bg"],
                        highlightbackground=C["log_card_border"], highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)
        self._right_card = card

        # ── log header ───────────────────────────────────────────────
        hdr = tk.Frame(card, bg=C["log_card_bg"])
        hdr.pack(fill=tk.X, padx=18, pady=(16, 8))

        lh = tk.Frame(hdr, bg=C["log_card_bg"])
        lh.pack(side=tk.LEFT)

        title_row = tk.Frame(lh, bg=C["log_card_bg"])
        title_row.pack(anchor=tk.W)
        tk.Label(title_row, text="⌨", font=("Segoe UI", 11),
                 bg=C["log_card_bg"], fg=C["log_hdr_sub"]).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(title_row, text="Keystroke Log", font=F["heading"],
                 bg=C["log_card_bg"], fg="#f1f5f9").pack(side=tk.LEFT)

        tk.Label(lh, text="Chronological event stream with instant keycap resolution.",
                 font=F["subhead"], bg=C["log_card_bg"], fg=C["log_hdr_sub"]).pack(anchor=tk.W, pady=(2, 0))

        # Filter entry (right side of header)
        fbox = tk.Frame(hdr, bg=C["filter_bg"],
                        highlightbackground=C["filter_border"], highlightthickness=1)
        fbox.pack(side=tk.RIGHT)

        tk.Label(fbox, text="🔍", font=("Segoe UI", 9),
                 bg=C["filter_bg"], fg=C["filter_fg"]).pack(side=tk.LEFT, padx=(8, 2), pady=7)

        self._filter_var = tk.StringVar()
        self._filter_entry = tk.Entry(
            fbox, textvariable=self._filter_var,
            font=F["mono_sm"], bg=C["filter_bg"], fg=C["filter_fg"],
            insertbackground="#94a3b8", relief=tk.FLAT, bd=0, width=20,
        )
        self._filter_entry.pack(side=tk.LEFT, padx=(0, 8), pady=7)
        self._filter_entry.insert(0, self._filter_placeholder)
        self._filter_entry.bind("<FocusIn>",  self._filter_focus_in)
        self._filter_entry.bind("<FocusOut>", self._filter_focus_out)
        self._filter_var.trace_add("write", self._on_filter_change)

        # ── column headers ────────────────────────────────────────────
        col_hdr = tk.Frame(card, bg=C["col_hdr_bg"])
        col_hdr.pack(fill=tk.X, padx=0)

        # left spacer (matches accent bar width)
        tk.Frame(col_hdr, bg=C["col_hdr_bg"], width=4).pack(side=tk.LEFT)

        # TIMESTAMP col
        tk.Label(col_hdr, text="TIMESTAMP", font=F["col_hdr"],
                 bg=C["col_hdr_bg"], fg=C["col_hdr_fg"],
                 anchor=tk.W, padx=14, pady=8, width=14).pack(side=tk.LEFT)

        # EVENT col
        tk.Label(col_hdr, text="EVENT", font=F["col_hdr"],
                 bg=C["col_hdr_bg"], fg=C["col_hdr_fg"],
                 anchor=tk.W, padx=0, pady=8, width=14).pack(side=tk.LEFT)

        # CAPTURED KEY (right-aligned)
        tk.Label(col_hdr, text="CAPTURED KEY", font=F["col_hdr"],
                 bg=C["col_hdr_bg"], fg=C["col_hdr_fg"],
                 anchor=tk.E, padx=14, pady=8).pack(side=tk.RIGHT)

        # divider
        tk.Frame(card, bg=C["log_card_border"], height=1).pack(fill=tk.X)

        # ── scrollable rows ───────────────────────────────────────────
        list_frame = tk.Frame(card, bg=C["log_card_bg"])
        list_frame.pack(fill=tk.BOTH, expand=True)

        vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL, width=7)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_canvas = tk.Canvas(list_frame, bg=C["log_card_bg"],
                                     bd=0, highlightthickness=0,
                                     yscrollcommand=vsb.set)
        self._log_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.config(command=self._log_canvas.yview)

        self._log_inner = tk.Frame(self._log_canvas, bg=C["log_card_bg"])
        self._cw = self._log_canvas.create_window((0, 0), window=self._log_inner, anchor="nw")

        self._log_inner.bind("<Configure>", lambda e: self._log_canvas.configure(
            scrollregion=self._log_canvas.bbox("all")))
        self._log_canvas.bind("<Configure>", lambda e: self._log_canvas.itemconfig(
            self._cw, width=e.width))

        for w in (self._log_canvas, self._log_inner):
            w.bind("<MouseWheel>", self._on_scroll)
            w.bind("<Button-4>",   self._on_scroll)
            w.bind("<Button-5>",   self._on_scroll)

    # ------------------------------------------------------------------ button bar
    def _build_button_bar(self) -> None:
        bar = tk.Frame(self, bg=C["btnbar_bg"])
        bar.pack(fill=tk.X, padx=14, pady=(4, 8))

        # Left buttons
        bl = tk.Frame(bar, bg=C["btnbar_bg"])
        bl.pack(side=tk.LEFT)

        self._btn_start = self._btn(bl, "▶  Start Logging", C["blue"],   C["blue_dark"],  self._start_logging)
        self._btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_stop  = self._btn(bl, "⏹  Stop Logging",  C["slate"],  C["slate_dark"], self._stop_logging)
        self._btn_stop.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_save  = self._btn(bl, "⬇  Save Log (.txt)", C["green"], C["green_dark"], self._save_log)
        self._btn_save.pack(side=tk.LEFT, padx=(0, 8))

        self._btn_clear = self._btn(bl, "🗑  Clear", C["red"], C["red_dark"], self._clear_log, outline=True)
        self._btn_clear.pack(side=tk.LEFT)

        # Right info boxes
        br = tk.Frame(bar, bg=C["btnbar_bg"])
        br.pack(side=tk.RIGHT)

        # Session timer box
        tb = tk.Frame(br, bg=C["btnbar_bg"],
                      highlightbackground=C["info_box_border"], highlightthickness=1)
        tb.pack(side=tk.LEFT, padx=(0, 10), ipady=7, ipadx=12)

        tk.Label(tb, text="⏱  Session:", font=F["status"],
                 bg=C["btnbar_bg"], fg=C["info_label_fg"]).pack(side=tk.LEFT, padx=(0, 4))
        self._timer_var = tk.StringVar(value="00m 00s")
        tk.Label(tb, textvariable=self._timer_var,
                 font=("Segoe UI", 9, "bold"),
                 bg=C["btnbar_bg"], fg=C["info_value_fg"]).pack(side=tk.LEFT)

        # Logged keys box
        kb = tk.Frame(br, bg=C["btnbar_bg"],
                      highlightbackground=C["info_box_border"], highlightthickness=1)
        kb.pack(side=tk.LEFT, ipady=7, ipadx=12)

        tk.Label(kb, text="Logged Keys:", font=F["status"],
                 bg=C["btnbar_bg"], fg=C["info_label_fg"]).pack(side=tk.LEFT, padx=(0, 4))
        self._keys_var = tk.StringVar(value="0")
        tk.Label(kb, textvariable=self._keys_var,
                 font=("Segoe UI", 9, "bold"),
                 bg=C["btnbar_bg"], fg=C["session_value_fg"]).pack(side=tk.LEFT)

    def _btn(self, parent, text, color, hover, cmd, outline=False):
        common = dict(
            text=text, font=F["btn"],
            relief=tk.FLAT, bd=0,
            padx=18, pady=9,
            cursor="hand2", command=cmd,
        )
        if outline:
            b = tk.Button(parent, bg=C["btnbar_bg"], fg=color,
                          activebackground=C["btnbar_bg"], activeforeground=hover,
                          highlightbackground=color, highlightthickness=1, **common)
        else:
            b = tk.Button(parent, bg=color, fg="#ffffff",
                          activebackground=hover, activeforeground="#ffffff", **common)
        return b

    # ------------------------------------------------------------------ status bar
    def _build_status_bar(self) -> None:
        bar = tk.Frame(self, bg=C["statusbar_bg"], height=30)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=C["statusbar_bg"])
        inner.pack(side=tk.LEFT, fill=tk.Y, padx=14)

        tk.Label(inner,
                 text="🛡  Offline Educational Keylogger  •  Data stored locally only",
                 font=F["status"], bg=C["statusbar_bg"], fg=C["statusbar_fg"]
                 ).pack(side=tk.LEFT, pady=6)

    # ------------------------------------------------------------------ key events
    def _on_key_press(self, event: tk.Event) -> None:
        key = resolve_key_name(event)
        entry = self.logger.record("KeyDown", key)
        if entry:
            self._push_row(entry)
            self._keys_var.set(str(self.logger.entry_count))

    def _on_key_release(self, event: tk.Event) -> None:
        key = resolve_key_name(event)
        entry = self.logger.record("KeyRelease", key)
        if entry:
            self._push_row(entry)
            self._keys_var.set(str(self.logger.entry_count))

    def _on_text_modified(self, event: tk.Event) -> None:
        self._text_area.edit_modified(False)
        text = self._text_area.get("1.0", tk.END)
        self._char_var.set(str(count_chars(text)))
        self._word_var.set(str(count_words(text)))

    # ------------------------------------------------------------------ log rows
    def _push_row(self, entry: LogEntry) -> None:
        self._all_rows.insert(0, {
            "timestamp":  entry.timestamp,
            "event_type": entry.event_type,
            "key":        entry.key,
        })
        self._render_rows()

    def _render_rows(self) -> None:
        for w in self._log_inner.winfo_children():
            w.destroy()

        flt = self._filter_var.get().strip().lower()
        if flt == self._filter_placeholder.lower() or not self._filter_active:
            flt = ""

        rows = [
            r for r in self._all_rows
            if not flt
               or flt in r["timestamp"].lower()
               or flt in r["event_type"].lower()
               or flt in r["key"].lower()
        ]

        for i, row in enumerate(rows):
            self._draw_row(row, i)

    def _draw_row(self, row: dict, idx: int) -> None:
        bg = C["row_even"] if idx % 2 == 0 else C["row_odd"]

        frame = tk.Frame(self._log_inner, bg=bg)
        frame.pack(fill=tk.X)

        # Thin left accent bar
        accent = C["kd_bg"] if row["event_type"] == "KeyDown" else C["kr_bg"]
        tk.Frame(frame, bg=accent, width=4).pack(side=tk.LEFT, fill=tk.Y)

        # Timestamp
        tk.Label(frame, text=row["timestamp"], font=F["mono"],
                 bg=bg, fg=C["ts_fg"], anchor=tk.W,
                 padx=12, pady=6, width=13).pack(side=tk.LEFT)

        # Event badge
        if row["event_type"] == "KeyDown":
            b_bg, b_fg = C["kd_bg"], C["kd_fg"]
        else:
            b_bg, b_fg = C["kr_bg"], C["kr_fg"]

        badge = tk.Frame(frame, bg=b_bg, padx=7, pady=3)
        badge.pack(side=tk.LEFT, padx=(4, 0), pady=4)
        tk.Label(badge, text=row["event_type"], font=F["badge"],
                 bg=b_bg, fg=b_fg).pack()

        # Key chip (right-aligned)
        key_text = f"[{row['key']}]"
        SPECIAL = {
            "Enter":     (C["blue"],   "#ffffff"),
            "Backspace": (C["amber"],  "#111827"),
            "Space":     ("#334155",   "#94a3b8"),
            "Escape":    (C["red"],    "#ffffff"),
            "Tab":       (C["purple"], "#ffffff"),
            "CapsLock":  ("#1e3a5f",   "#93c5fd"),
        }
        chip_bg, chip_fg = SPECIAL.get(row["key"], ("#2d3148", "#e2e8f0"))

        chip = tk.Frame(frame, bg=chip_bg, padx=7, pady=3)
        chip.pack(side=tk.RIGHT, padx=12, pady=4)
        tk.Label(chip, text=key_text, font=F["chip"],
                 bg=chip_bg, fg=chip_fg).pack()

        # thin row separator
        tk.Frame(self._log_inner, bg=C["row_sep"], height=1).pack(fill=tk.X)

    # ------------------------------------------------------------------ scrolling
    def _on_scroll(self, event: tk.Event) -> None:
        if event.num == 4:
            self._log_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._log_canvas.yview_scroll(1, "units")
        else:
            self._log_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ------------------------------------------------------------------ filter
    def _filter_focus_in(self, _event) -> None:
        if self._filter_entry.get() == self._filter_placeholder:
            self._filter_entry.delete(0, tk.END)
            self._filter_entry.config(fg="#e2e8f0")
        self._filter_active = True

    def _filter_focus_out(self, _event) -> None:
        self._filter_active = False
        if not self._filter_entry.get():
            self._filter_entry.insert(0, self._filter_placeholder)
            self._filter_entry.config(fg=C["filter_fg"])
        self._render_rows()

    def _on_filter_change(self, *_) -> None:
        if self._filter_active:
            self._render_rows()

    # ------------------------------------------------------------------ actions
    def _start_logging(self) -> None:
        self.logger.start()
        self._update_button_states()
        self._set_badge(active=True)
        self._text_area.focus_set()
        self._tick()

    def _stop_logging(self) -> None:
        self.logger.stop()
        self._update_button_states()
        self._set_badge(active=False)
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _save_log(self) -> None:
        if self.logger.entry_count == 0:
            messagebox.showinfo("KeyTrace",
                "No keystrokes to save yet.\nStart logging and type something first.")
            return
        fp = filedialog.asksaveasfilename(
            title="Save Keystroke Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="keytrace_log.txt",
        )
        if not fp:
            return
        try:
            self.logger.save(fp)
            messagebox.showinfo("KeyTrace", f"Log saved successfully:\n{fp}")
        except OSError as e:
            messagebox.showerror("KeyTrace", f"Could not save file:\n{e}")

    def _clear_log(self) -> None:
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self.logger.clear()
        self._all_rows.clear()
        self._text_area.delete("1.0", tk.END)
        self._char_var.set("0")
        self._word_var.set("0")
        self._keys_var.set("0")
        self._timer_var.set("00m 00s")
        for w in self._log_inner.winfo_children():
            w.destroy()
        self._update_button_states()
        self._set_badge(active=False)

    # ------------------------------------------------------------------ helpers
    def _update_button_states(self) -> None:
        active = self.logger.is_active
        self._btn_start.config(state=tk.DISABLED if active  else tk.NORMAL)
        self._btn_stop.config( state=tk.NORMAL   if active  else tk.DISABLED)

    def _set_badge(self, active: bool) -> None:
        if active:
            self._pill.config(highlightbackground="#1a4731")
            self._pill_dot.config(fg=C["green"])
            self._pill_lbl.config(text="Logging Active", fg=C["green"])
        else:
            self._pill.config(highlightbackground="#2d3148")
            self._pill_dot.config(fg=C["slate"])
            self._pill_lbl.config(text="Logging Inactive", fg=C["slate"])

    def _tick(self) -> None:
        if not self.logger.is_active:
            return
        self._timer_var.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
