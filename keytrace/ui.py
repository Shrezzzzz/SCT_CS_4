"""
ui.py — KeyTrace
Pixel-accurate recreation of the mockup.
Uses grid-based layout to guarantee the 45/55 left/right split
and correct vertical proportions at any window size.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ── Palette ──────────────────────────────────────────────────────────────────
C = {
    # chrome / window
    "win":          "#e6e9f4",   # light blue-grey page background
    "titlebar":     "#1b1e2d",   # near-black navy title bar
    "title_fg":     "#f0f4ff",
    "title_sub":    "#8899bb",

    # left white card
    "card":         "#ffffff",
    "card_border":  "#dde1ef",
    "txt1":         "#111827",
    "txt2":         "#6b7280",
    "txt3":         "#9ca3af",

    # stat mini-cards
    "stat":         "#ffffff",
    "stat_border":  "#dde1ef",

    # typing area
    "ta_bg":        "#ffffff",
    "ta_border":    "#d1d5db",
    "ta_cursor":    "#3b82f6",

    # right dark card
    "log":          "#1e2235",
    "log_border":   "#2b2f45",
    "colhdr":       "#181b29",
    "colhdr_fg":    "#5a6380",
    "row_even":     "#1e2235",
    "row_odd":      "#232740",
    "row_div":      "#282c40",
    "ts_fg":        "#8896b0",

    # filter box
    "filt":         "#161929",
    "filt_border":  "#2b2f45",
    "filt_ph":      "#5a6380",

    # accents
    "blue":         "#3b82f6",
    "blue_h":       "#2563eb",
    "green":        "#22c55e",
    "green_h":      "#16a34a",
    "red":          "#ef4444",
    "red_h":        "#dc2626",
    "amber":        "#f59e0b",
    "slate":        "#64748b",
    "slate_h":      "#475569",
    "purple":       "#7c3aed",

    # badges
    "kd":           "#3b82f6",
    "kd_fg":        "#ffffff",
    "kr":           "#475569",
    "kr_fg":        "#e2e8f0",

    # button bar
    "btnbar":       "#e6e9f4",
    "ibox_border":  "#c8ccd8",

    # status bar
    "sb":           "#111827",
    "sb_fg":        "#8899aa",
}

F = {
    "appname":  ("Segoe UI", 13, "bold"),
    "heading":  ("Segoe UI", 12, "bold"),
    "sub":      ("Segoe UI",  9),
    "body":     ("Segoe UI", 10),
    "small":    ("Segoe UI",  8),
    "stat_lbl": ("Segoe UI",  8, "bold"),
    "stat_val": ("Segoe UI", 24, "bold"),
    "colhdr":   ("Segoe UI",  7, "bold"),
    "mono":     ("Consolas",  9),
    "mono_sm":  ("Consolas",  8),
    "badge":    ("Segoe UI",  8, "bold"),
    "chip":     ("Consolas",  9),
    "btn":      ("Segoe UI", 10, "bold"),
    "status":   ("Segoe UI",  9),
}

PLACEHOLDER = "Filter keystrokes..."


class KeyTraceApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.logger = KeystrokeLogger()
        self._rows: List[dict] = []
        self._timer_id: str | None = None
        self._filter_has_focus = False

        self._setup_window()
        self._build()
        self._update_btn_states()

    # ── window ───────────────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=C["win"])
        self.resizable(True, True)
        self.minsize(900, 580)
        self.update_idletasks()
        W, H = 1120, 700
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

    # ── root scaffold ─────────────────────────────────────────────────────────
    def _build(self) -> None:
        # status bar pinned to bottom first so it never gets pushed out
        self._build_statusbar()
        # button bar above status bar
        self._build_btnbar()
        # title bar at top
        self._build_titlebar()
        # body fills remaining space
        self._build_body()

    # ── title bar ─────────────────────────────────────────────────────────────
    def _build_titlebar(self) -> None:
        bar = tk.Frame(self, bg=C["titlebar"], height=44)
        bar.pack(side=tk.TOP, fill=tk.X)
        bar.pack_propagate(False)

        lf = tk.Frame(bar, bg=C["titlebar"])
        lf.pack(side=tk.LEFT, padx=16, fill=tk.Y)
        tk.Label(lf, text="⌨", font=("Segoe UI", 12),
                 bg=C["titlebar"], fg=C["title_sub"]).pack(side=tk.LEFT, padx=(0, 7), pady=11)
        tk.Label(lf, text="KeyTrace", font=F["appname"],
                 bg=C["titlebar"], fg=C["title_fg"]).pack(side=tk.LEFT)

        rf = tk.Frame(bar, bg=C["titlebar"])
        rf.pack(side=tk.RIGHT, padx=16, fill=tk.Y)

        self._pill = tk.Frame(rf, bg=C["titlebar"],
                              highlightbackground="#2d3148", highlightthickness=1)
        self._pill.pack(side=tk.RIGHT, pady=9)

        self._pill_dot = tk.Label(self._pill, text="●", font=("Segoe UI", 8),
                                  bg=C["titlebar"], fg=C["slate"])
        self._pill_dot.pack(side=tk.LEFT, padx=(10, 3), pady=5)

        self._pill_lbl = tk.Label(self._pill, text="Logging Inactive",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=C["titlebar"], fg=C["slate"])
        self._pill_lbl.pack(side=tk.LEFT, padx=(0, 10), pady=5)

        tk.Frame(self, bg="#252838", height=1).pack(side=tk.TOP, fill=tk.X)

    # ── body (left + right side by side) ─────────────────────────────────────
    def _build_body(self) -> None:
        body = tk.Frame(self, bg=C["win"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=14, pady=(10, 0))

        # Configure columns: left 44%, right 56%
        body.columnconfigure(0, weight=44)
        body.columnconfigure(1, weight=56)
        body.rowconfigure(0, weight=1)

        # Left white card
        self._build_left(body)
        # Right dark card
        self._build_right(body)

    # ── LEFT card ─────────────────────────────────────────────────────────────
    def _build_left(self, parent: tk.Frame) -> None:
        outer = tk.Frame(parent, bg=C["win"])
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        card = tk.Frame(outer, bg=C["card"],
                        highlightbackground=C["card_border"], highlightthickness=1)
        card.grid(row=0, column=0, sticky="nsew")
        # Card internal layout: heading, rule, stats, textarea, footer
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)   # textarea row expands

        # ── heading ──────────────────────────────
        hdr = tk.Frame(card, bg=C["card"])
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))

        title_row = tk.Frame(hdr, bg=C["card"])
        title_row.pack(anchor=tk.W)
        tk.Label(title_row, text="✏", font=("Segoe UI", 10),
                 bg=C["card"], fg=C["txt2"]).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(title_row, text="Typing Area", font=F["heading"],
                 bg=C["card"], fg=C["txt1"]).pack(side=tk.LEFT)

        tk.Label(hdr,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=F["sub"], bg=C["card"], fg=C["txt2"],
                 wraplength=340, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))

        # ── rule ─────────────────────────────────
        tk.Frame(card, bg=C["card_border"], height=1).grid(
            row=1, column=0, sticky="ew", padx=20, pady=(12, 0))

        # ── stat cards ───────────────────────────
        stat_frame = tk.Frame(card, bg=C["card"])
        stat_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 10))
        stat_frame.columnconfigure(0, weight=1, uniform="s")
        stat_frame.columnconfigure(1, weight=1, uniform="s")

        self._char_var = tk.StringVar(value="0")
        self._word_var = tk.StringVar(value="0")
        self._stat_card(stat_frame, "CHARACTERS", self._char_var, "⌨", 0)
        self._stat_card(stat_frame, "WORDS",      self._word_var, "≡", 1)

        # ── text sandbox ─────────────────────────
        ta_wrap = tk.Frame(card, bg=C["ta_border"], highlightthickness=0)
        ta_wrap.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 6))
        ta_wrap.rowconfigure(0, weight=1)
        ta_wrap.columnconfigure(0, weight=1)

        self._ta = tk.Text(
            ta_wrap, font=F["body"],
            bg=C["ta_bg"], fg=C["txt1"],
            insertbackground=C["ta_cursor"],
            relief=tk.FLAT, bd=10,
            wrap=tk.WORD, undo=True,
            selectbackground=C["blue"], selectforeground="#fff",
            highlightthickness=0,
        )
        self._ta.grid(row=0, column=0, sticky="nsew")

        # vertical scrollbar for text area
        ta_sb = tk.Scrollbar(ta_wrap, orient=tk.VERTICAL, command=self._ta.yview, width=7)
        ta_sb.grid(row=0, column=1, sticky="ns")
        self._ta.config(yscrollcommand=ta_sb.set)

        self._ta.bind("<Key>",        self._on_key_press)
        self._ta.bind("<KeyRelease>", self._on_key_release)
        self._ta.bind("<<Modified>>", self._on_modified)

        # ── footer ───────────────────────────────
        foot = tk.Frame(card, bg=C["card"])
        foot.grid(row=4, column=0, sticky="ew", padx=20, pady=(4, 16))

        fi = tk.Frame(foot, bg=C["card"])
        fi.pack(anchor=tk.W)
        tk.Label(fi, text="✓", font=("Segoe UI", 9),
                 bg=C["card"], fg=C["blue"]).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(fi,
                 text="Educational Sandbox  •  Keys logged only within this application window",
                 font=F["small"], bg=C["card"], fg=C["txt3"],
                 wraplength=340, justify=tk.LEFT).pack(side=tk.LEFT)

    def _stat_card(self, parent, label, var, icon, col):
        pad_r = 6 if col == 0 else 0
        f = tk.Frame(parent, bg=C["stat_border"],
                     highlightbackground=C["stat_border"], highlightthickness=1)
        f.grid(row=0, column=col, sticky="nsew", padx=(0, pad_r))

        inner = tk.Frame(f, bg=C["stat"], padx=12, pady=8)
        inner.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(inner, bg=C["stat"])
        top.pack(fill=tk.X)
        tk.Label(top, text=label, font=F["stat_lbl"],
                 bg=C["stat"], fg=C["txt3"]).pack(side=tk.LEFT)
        tk.Label(top, text=icon, font=("Segoe UI", 10),
                 bg=C["stat"], fg=C["txt3"]).pack(side=tk.RIGHT)

        tk.Label(inner, textvariable=var, font=F["stat_val"],
                 bg=C["stat"], fg=C["txt1"]).pack(anchor=tk.W, pady=(2, 0))

    # ── RIGHT card ────────────────────────────────────────────────────────────
    def _build_right(self, parent: tk.Frame) -> None:
        outer = tk.Frame(parent, bg=C["win"])
        outer.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 10))
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        card = tk.Frame(outer, bg=C["log"],
                        highlightbackground=C["log_border"], highlightthickness=1)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)   # log list expands

        # ── log header ───────────────────────────
        hdr = tk.Frame(card, bg=C["log"])
        hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        hdr.columnconfigure(0, weight=1)

        lh = tk.Frame(hdr, bg=C["log"])
        lh.grid(row=0, column=0, sticky="w")

        title_row = tk.Frame(lh, bg=C["log"])
        title_row.pack(anchor=tk.W)
        tk.Label(title_row, text="⌨", font=("Segoe UI", 11),
                 bg=C["log"], fg=C["title_sub"]).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(title_row, text="Keystroke Log", font=F["heading"],
                 bg=C["log"], fg="#f0f4ff").pack(side=tk.LEFT)

        tk.Label(lh, text="Chronological event stream with instant keycap resolution.",
                 font=F["sub"], bg=C["log"], fg=C["colhdr_fg"]).pack(anchor=tk.W, pady=(2, 0))

        # filter box (right side of header row)
        fbox = tk.Frame(hdr, bg=C["filt"],
                        highlightbackground=C["filt_border"], highlightthickness=1)
        fbox.grid(row=0, column=1, sticky="e", padx=(8, 0))

        tk.Label(fbox, text="🔍", font=("Segoe UI", 9),
                 bg=C["filt"], fg=C["filt_ph"]).pack(side=tk.LEFT, padx=(8, 2), pady=7)

        self._fvar = tk.StringVar()
        self._fentry = tk.Entry(fbox, textvariable=self._fvar,
                                font=F["mono_sm"], bg=C["filt"], fg=C["filt_ph"],
                                insertbackground="#aab", relief=tk.FLAT, bd=0, width=18)
        self._fentry.pack(side=tk.LEFT, padx=(0, 8), pady=7)
        self._fentry.insert(0, PLACEHOLDER)
        self._fentry.bind("<FocusIn>",  self._filt_in)
        self._fentry.bind("<FocusOut>", self._filt_out)
        self._fvar.trace_add("write", self._filt_changed)

        # ── column headers ───────────────────────
        ch = tk.Frame(card, bg=C["colhdr"])
        ch.grid(row=1, column=0, sticky="ew")

        tk.Frame(ch, bg=C["colhdr"], width=4).pack(side=tk.LEFT, fill=tk.Y)   # accent spacer

        tk.Label(ch, text="TIMESTAMP", font=F["colhdr"],
                 bg=C["colhdr"], fg=C["colhdr_fg"],
                 anchor=tk.W, padx=12, pady=8, width=14).pack(side=tk.LEFT)

        tk.Label(ch, text="EVENT", font=F["colhdr"],
                 bg=C["colhdr"], fg=C["colhdr_fg"],
                 anchor=tk.W, padx=0, pady=8, width=13).pack(side=tk.LEFT)

        tk.Label(ch, text="CAPTURED KEY", font=F["colhdr"],
                 bg=C["colhdr"], fg=C["colhdr_fg"],
                 anchor=tk.E, padx=14, pady=8).pack(side=tk.RIGHT)

        # ── divider ──────────────────────────────
        tk.Frame(card, bg=C["log_border"], height=1).grid(row=2, column=0, sticky="ew")

        # ── scrollable row area ───────────────────
        list_frame = tk.Frame(card, bg=C["log"])
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        vsb = tk.Scrollbar(list_frame, orient=tk.VERTICAL, width=7)
        vsb.grid(row=0, column=1, sticky="ns")

        self._canvas = tk.Canvas(list_frame, bg=C["log"],
                                 bd=0, highlightthickness=0,
                                 yscrollcommand=vsb.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._canvas.yview)

        self._inner = tk.Frame(self._canvas, bg=C["log"])
        self._cwin  = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._cwin, width=e.width))

        for w in (self._canvas, self._inner):
            w.bind("<MouseWheel>", self._scroll)
            w.bind("<Button-4>",   self._scroll)
            w.bind("<Button-5>",   self._scroll)

    # ── button bar ────────────────────────────────────────────────────────────
    def _build_btnbar(self) -> None:
        bar = tk.Frame(self, bg=C["btnbar"], height=56)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=C["btnbar"])
        inner.pack(fill=tk.BOTH, expand=True, padx=14)

        # left buttons
        bl = tk.Frame(inner, bg=C["btnbar"])
        bl.pack(side=tk.LEFT, fill=tk.Y)

        def _vpack(btn): btn.pack(side=tk.LEFT, padx=(0, 8), pady=10)

        self._btn_start = self._mk_btn(bl, "▶  Start Logging",   C["blue"],  C["blue_h"],  self._cmd_start)
        self._btn_stop  = self._mk_btn(bl, "⏹  Stop Logging",    C["slate"], C["slate_h"], self._cmd_stop)
        self._btn_save  = self._mk_btn(bl, "⬇  Save Log (.txt)", C["green"], C["green_h"], self._cmd_save)
        self._btn_clear = self._mk_btn(bl, "🗑  Clear",           C["red"],   C["red_h"],   self._cmd_clear, outline=True)
        for b in (self._btn_start, self._btn_stop, self._btn_save):
            _vpack(b)
        self._btn_clear.pack(side=tk.LEFT, pady=10)

        # right info boxes
        br = tk.Frame(inner, bg=C["btnbar"])
        br.pack(side=tk.RIGHT, fill=tk.Y)

        # ⏱ Session box
        sb_box = tk.Frame(br, bg=C["btnbar"],
                          highlightbackground=C["ibox_border"], highlightthickness=1)
        sb_box.pack(side=tk.LEFT, padx=(0, 10), pady=12, ipady=6, ipadx=12)

        tk.Label(sb_box, text="⏱  Session:", font=F["status"],
                 bg=C["btnbar"], fg=C["txt2"]).pack(side=tk.LEFT, padx=(0, 4))
        self._tvar = tk.StringVar(value="00m 00s")
        tk.Label(sb_box, textvariable=self._tvar,
                 font=("Segoe UI", 9, "bold"),
                 bg=C["btnbar"], fg=C["txt1"]).pack(side=tk.LEFT)

        # divider
        tk.Frame(br, bg=C["ibox_border"], width=1).pack(side=tk.LEFT, fill=tk.Y, pady=16)

        # Logged Keys box
        kb_box = tk.Frame(br, bg=C["btnbar"],
                          highlightbackground=C["ibox_border"], highlightthickness=1)
        kb_box.pack(side=tk.LEFT, padx=(10, 0), pady=12, ipady=6, ipadx=12)

        tk.Label(kb_box, text="Logged Keys:", font=F["status"],
                 bg=C["btnbar"], fg=C["txt2"]).pack(side=tk.LEFT, padx=(0, 4))
        self._kvar = tk.StringVar(value="0")
        tk.Label(kb_box, textvariable=self._kvar,
                 font=("Segoe UI", 9, "bold"),
                 bg=C["btnbar"], fg=C["blue"]).pack(side=tk.LEFT)

    def _mk_btn(self, parent, text, color, hover, cmd, outline=False):
        kw = dict(text=text, font=F["btn"], relief=tk.FLAT, bd=0,
                  padx=16, pady=8, cursor="hand2", command=cmd)
        if outline:
            return tk.Button(parent, bg=C["btnbar"], fg=color,
                             activebackground=C["btnbar"], activeforeground=hover,
                             highlightbackground=color, highlightthickness=1, **kw)
        return tk.Button(parent, bg=color, fg="#fff",
                         activebackground=hover, activeforeground="#fff", **kw)

    # ── status bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg=C["sb"], height=28)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        tk.Label(bar,
                 text="🛡  Offline Educational Keylogger  •  Data stored locally only",
                 font=F["status"], bg=C["sb"], fg=C["sb_fg"]
                 ).pack(side=tk.LEFT, padx=14, pady=5)

    # ── key capture ───────────────────────────────────────────────────────────
    def _on_key_press(self, event: tk.Event) -> None:
        key   = resolve_key_name(event)
        entry = self.logger.record("KeyDown", key)
        if entry:
            self._push(entry)
            self._kvar.set(str(self.logger.entry_count))

    def _on_key_release(self, event: tk.Event) -> None:
        key   = resolve_key_name(event)
        entry = self.logger.record("KeyRelease", key)
        if entry:
            self._push(entry)
            self._kvar.set(str(self.logger.entry_count))

    def _on_modified(self, _event) -> None:
        self._ta.edit_modified(False)
        t = self._ta.get("1.0", tk.END)
        self._char_var.set(str(count_chars(t)))
        self._word_var.set(str(count_words(t)))

    # ── log rendering ─────────────────────────────────────────────────────────
    def _push(self, entry: LogEntry) -> None:
        self._rows.insert(0, {"ts": entry.timestamp,
                               "ev": entry.event_type,
                               "key": entry.key})
        self._redraw()

    def _redraw(self) -> None:
        for w in self._inner.winfo_children():
            w.destroy()

        flt = ""
        if self._filter_has_focus or self._fentry.get() != PLACEHOLDER:
            flt = self._fvar.get().strip().lower()
            if flt == PLACEHOLDER.lower():
                flt = ""

        rows = [r for r in self._rows
                if not flt or flt in r["ts"].lower()
                or flt in r["ev"].lower()
                or flt in r["key"].lower()]

        for i, r in enumerate(rows):
            self._draw_row(r, i)

    def _draw_row(self, row: dict, idx: int) -> None:
        bg = C["row_even"] if idx % 2 == 0 else C["row_odd"]

        frame = tk.Frame(self._inner, bg=bg)
        frame.pack(fill=tk.X)

        # left accent bar
        ac = C["kd"] if row["ev"] == "KeyDown" else C["kr"]
        tk.Frame(frame, bg=ac, width=4).pack(side=tk.LEFT, fill=tk.Y)

        # timestamp
        tk.Label(frame, text=row["ts"], font=F["mono"],
                 bg=bg, fg=C["ts_fg"],
                 anchor=tk.W, padx=12, pady=6, width=13).pack(side=tk.LEFT)

        # event badge
        b_bg = C["kd"] if row["ev"] == "KeyDown" else C["kr"]
        b_fg = C["kd_fg"] if row["ev"] == "KeyDown" else C["kr_fg"]
        badge = tk.Frame(frame, bg=b_bg, padx=7, pady=2)
        badge.pack(side=tk.LEFT, padx=(4, 0), pady=5)
        tk.Label(badge, text=row["ev"], font=F["badge"],
                 bg=b_bg, fg=b_fg).pack()

        # key chip (right-aligned)
        SPECIAL = {
            "Enter":     (C["blue"],   "#fff"),
            "Backspace": (C["amber"],  "#111"),
            "Space":     ("#334155",   "#94a3b8"),
            "Escape":    (C["red"],    "#fff"),
            "Tab":       (C["purple"], "#fff"),
        }
        chip_bg, chip_fg = SPECIAL.get(row["key"], ("#2b2f45", "#dde3f0"))
        chip = tk.Frame(frame, bg=chip_bg, padx=7, pady=2)
        chip.pack(side=tk.RIGHT, padx=12, pady=5)
        tk.Label(chip, text=f"[{row['key']}]", font=F["chip"],
                 bg=chip_bg, fg=chip_fg).pack()

        # row divider
        tk.Frame(self._inner, bg=C["row_div"], height=1).pack(fill=tk.X)

    # ── scroll ────────────────────────────────────────────────────────────────
    def _scroll(self, event: tk.Event) -> None:
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ── filter ────────────────────────────────────────────────────────────────
    def _filt_in(self, _e) -> None:
        self._filter_has_focus = True
        if self._fentry.get() == PLACEHOLDER:
            self._fentry.delete(0, tk.END)
            self._fentry.config(fg="#c8d4e8")

    def _filt_out(self, _e) -> None:
        self._filter_has_focus = False
        if not self._fentry.get():
            self._fentry.insert(0, PLACEHOLDER)
            self._fentry.config(fg=C["filt_ph"])
        self._redraw()

    def _filt_changed(self, *_) -> None:
        if self._filter_has_focus:
            self._redraw()

    # ── button commands ───────────────────────────────────────────────────────
    def _cmd_start(self) -> None:
        self.logger.start()
        self._update_btn_states()
        self._set_pill(True)
        self._ta.focus_set()
        self._tick()

    def _cmd_stop(self) -> None:
        self.logger.stop()
        self._update_btn_states()
        self._set_pill(False)
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _cmd_save(self) -> None:
        if self.logger.entry_count == 0:
            messagebox.showinfo("KeyTrace",
                "No keystrokes yet.\nStart logging and type something first.")
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
            messagebox.showinfo("KeyTrace", f"Saved:\n{fp}")
        except OSError as e:
            messagebox.showerror("KeyTrace", f"Could not save:\n{e}")

    def _cmd_clear(self) -> None:
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self.logger.clear()
        self._rows.clear()
        self._ta.delete("1.0", tk.END)
        self._char_var.set("0")
        self._word_var.set("0")
        self._kvar.set("0")
        self._tvar.set("00m 00s")
        for w in self._inner.winfo_children():
            w.destroy()
        self._update_btn_states()
        self._set_pill(False)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _update_btn_states(self) -> None:
        active = self.logger.is_active
        self._btn_start.config(state=tk.DISABLED if active else tk.NORMAL)
        self._btn_stop.config( state=tk.NORMAL   if active else tk.DISABLED)

    def _set_pill(self, active: bool) -> None:
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
        self._tvar.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
