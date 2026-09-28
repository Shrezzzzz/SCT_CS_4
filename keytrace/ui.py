"""
ui.py — KeyTrace  (v4 — grid-only, cross-platform reliable)

Layout engine: pure grid + pack, no place(), no Canvas RoundFrame.
Fixed 1120 × 720 window (scales well on all monitors without needing
a 4K display).  All colours, fonts and proportions match the mockup.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ── palette ──────────────────────────────────────────────────────────────────
P = {
    "win":            "#DCE2EC",
    "navbar":         "#2D3647",
    "footer":         "#2D3647",
    "left_bg":        "#F8FAFD",
    "left_border":    "#C8D3E2",
    "right_bg":       "#18263C",
    "right_border":   "#2B3D57",
    "card_bg":        "#FFFFFF",
    "card_border":    "#C9D5E6",
    "ta_border":      "#AFC3DD",
    "notice_bg":      "#EEF4FB",
    "notice_border":  "#C8D9F0",
    "action_bg":      "#EEF2F7",
    "action_border":  "#CAD4E3",
    "session_border": "#D1DAE7",
    "divider":        "#D6DFEB",
    "right_div":      "#314560",
    "col_hdr_bg":     "#0E1B31",
    "col_hdr_fg":     "#A9BCD8",
    "search_bg":      "#102038",
    "search_border":  "#35527A",
    "row_alt":        "#1B2D45",
    "ts_fg":          "#8EA4C7",
    "txt_dark":       "#1C2A44",
    "txt_gray":       "#61718D",
    "txt_white":      "#FFFFFF",
    "txt_light":      "#8EA4C7",
    "blue":           "#2E64F0",
    "blue_h":         "#2456D8",
    "green":          "#16A34A",
    "green_h":        "#128C3E",
    "slate":          "#5C6C84",
    "slate_h":        "#4E5C71",
    "red_fg":         "#EF4444",
    "red_h":          "#DC2626",
    "char_blue":      "#2C64F0",
    "badge_fg":       "#38E38F",
    "badge_bg":       "#113D34",
    "badge_border":   "#1ED38A",
    "kd_bg":          "#1E4EA8",
    "kd_fg":          "#BFD8FF",
    "kr_bg":          "#37475D",
    "kr_fg":          "#CED7E5",
    "bs_bg":          "#47320C",
    "bs_fg":          "#FFC857",
    "bs_bdr":         "#F59E0B",
    "chip_bg":        "#1E3050",
    "chip_fg":        "#BFD8FF",
    "chip_bdr":       "#2E4A6E",
    "accent":         "#3B82F6",
    "tl_red":         "#FF5F57",
    "tl_yellow":      "#FEBC2E",
    "tl_green":       "#28C840",
}

SF = "Segoe UI"
MF = "Consolas"

PH = "Filter keystrokes..."   # placeholder text


# ─────────────────────────────────────────────────────────────────────────────

class KeyTraceApp(tk.Tk):

    W, H = 1120, 720   # fixed window size

    def __init__(self) -> None:
        super().__init__()
        self.logger       = KeystrokeLogger()
        self._rows: List[dict] = []
        self._timer_id    = None
        self._flt_active  = False   # True only while filter entry has focus

        self._setup_window()
        self._build()
        self._set_btn_states()

    # ── window setup ─────────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=P["win"])
        self.resizable(False, False)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

    # ── top-level scaffold ───────────────────────────────────────────────────
    def _build(self) -> None:
        # Pack order: footer → action bar → navbar → body
        # (footer + action bar first so they are never pushed out)
        self._build_footer()
        self._build_action_bar()
        self._build_navbar()
        self._build_body()

    # ─────────────────────────────────────────────────────────────────────────
    #  NAVBAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_navbar(self) -> None:
        nav = tk.Frame(self, bg=P["navbar"], height=58)
        nav.pack(side=tk.TOP, fill=tk.X)
        nav.pack_propagate(False)

        # ── left ──────────────────────────────────
        lf = tk.Frame(nav, bg=P["navbar"])
        lf.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 0))

        # traffic lights via canvas circles
        tlc = tk.Canvas(lf, bg=P["navbar"], width=66, height=14,
                        bd=0, highlightthickness=0)
        tlc.pack(side=tk.LEFT, padx=(0, 14), pady=22)
        for i, col in enumerate((P["tl_red"], P["tl_yellow"], P["tl_green"])):
            cx = 7 + i * 22
            tlc.create_oval(cx-6, 1, cx+6, 13, fill=col, outline=col)

        tk.Label(lf, text="⌨", font=(SF, 13),
                 bg=P["navbar"], fg="#9AAFC8").pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(lf, text="KeyTrace", font=(SF, 16, "bold"),
                 bg=P["navbar"], fg=P["txt_white"]).pack(side=tk.LEFT)

        # ── right: badge ──────────────────────────
        rf = tk.Frame(nav, bg=P["navbar"])
        rf.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 20))

        # badge: outer border frame → inner fill frame
        self._badge_frame = tk.Frame(rf, bg=P["badge_border"], padx=1, pady=1)
        self._badge_frame.pack(side=tk.RIGHT, pady=13)

        self._badge_inner = tk.Frame(self._badge_frame, bg=P["badge_bg"])
        self._badge_inner.pack()

        self._badge_dot = tk.Label(
            self._badge_inner, text="●", font=(SF, 9),
            bg=P["badge_bg"], fg=P["badge_fg"])
        self._badge_dot.pack(side=tk.LEFT, padx=(14, 4), pady=7)

        self._badge_lbl = tk.Label(
            self._badge_inner, text="Logging Inactive",
            font=(SF, 12, "bold"), bg=P["badge_bg"], fg="#7ABFA0")
        self._badge_lbl.pack(side=tk.LEFT, padx=(0, 14), pady=7)

        # bottom separator line
        tk.Frame(self, bg="#252D3D", height=1).pack(side=tk.TOP, fill=tk.X)

    # ─────────────────────────────────────────────────────────────────────────
    #  BODY  (left 42 % + right 58 %)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_body(self) -> None:
        body = tk.Frame(self, bg=P["win"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                  padx=14, pady=(10, 0))

        # Two columns: left 42 %, right 58 %
        body.columnconfigure(0, weight=42)
        body.columnconfigure(1, weight=58)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    # ─────────────────────────────────────────────────────────────────────────
    #  LEFT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, body: tk.Frame) -> None:
        # Outer frame = border colour
        outer = tk.Frame(body, bg=P["left_border"])
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))

        # Inner = panel colour
        inner = tk.Frame(outer, bg=P["left_bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(4, weight=1)   # text area row expands

        # ── heading ──────────────────────────────────
        hrow = tk.Frame(inner, bg=P["left_bg"])
        hrow.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 0))

        tk.Label(hrow, text="✏", font=(SF, 12),
                 bg=P["left_bg"], fg=P["blue"]).pack(side=tk.LEFT, padx=(0, 7))
        tk.Label(hrow, text="Typing Area", font=(SF, 18, "bold"),
                 bg=P["left_bg"], fg=P["txt_dark"]).pack(side=tk.LEFT)

        tk.Label(inner,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=(SF, 11), bg=P["left_bg"], fg=P["txt_gray"],
                 wraplength=360, justify=tk.LEFT
                 ).grid(row=1, column=0, sticky="w", padx=22, pady=(4, 0))

        # divider
        tk.Frame(inner, bg=P["divider"], height=1).grid(
            row=2, column=0, sticky="ew", padx=22, pady=(12, 0))

        # ── stat cards ────────────────────────────────
        sc_row = tk.Frame(inner, bg=P["left_bg"])
        sc_row.grid(row=3, column=0, sticky="ew", padx=22, pady=(12, 0))
        sc_row.columnconfigure(0, weight=1, uniform="sc")
        sc_row.columnconfigure(1, weight=1, uniform="sc")
        sc_row.columnconfigure(2, weight=1, uniform="sc")

        self._char_var = tk.StringVar(value="0")
        self._word_var = tk.StringVar(value="0")

        self._stat_card(sc_row, "CHARACTERS", self._char_var, P["char_blue"], 0)
        self._stat_card(sc_row, "WORDS",      self._word_var, P["txt_dark"],  1)
        self._stat_card(sc_row, "CAPTURE RATE", tk.StringVar(value="—"),
                        P["txt_gray"], 2)

        # ── typing text area ──────────────────────────
        ta_outer = tk.Frame(inner, bg=P["ta_border"])
        ta_outer.grid(row=4, column=0, sticky="nsew", padx=22, pady=(12, 0))
        ta_outer.columnconfigure(0, weight=1)
        ta_outer.rowconfigure(0, weight=1)

        self._ta = tk.Text(
            ta_outer,
            font=(SF, 13),
            bg=P["card_bg"], fg="#1E293B",
            insertbackground=P["blue"],
            relief=tk.FLAT, bd=14,
            wrap=tk.WORD, undo=True,
            selectbackground=P["blue"],
            selectforeground="#FFFFFF",
            highlightthickness=0,
        )
        self._ta.grid(row=0, column=0, sticky="nsew")

        self._ta.bind("<Key>",        self._on_key_press)
        self._ta.bind("<KeyRelease>", self._on_key_release)
        self._ta.bind("<<Modified>>", self._on_modified)

        # ── educational notice ────────────────────────
        notice = tk.Frame(inner, bg=P["notice_border"])
        notice.grid(row=5, column=0, sticky="ew", padx=22, pady=(12, 20))

        ni = tk.Frame(notice, bg=P["notice_bg"])
        ni.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        nr = tk.Frame(ni, bg=P["notice_bg"])
        nr.pack(fill=tk.X, padx=14, pady=10)

        tk.Label(nr, text="🛡", font=(SF, 14),
                 bg=P["notice_bg"], fg=P["blue"]).pack(side=tk.LEFT, padx=(0, 8))

        nt = tk.Frame(nr, bg=P["notice_bg"])
        nt.pack(side=tk.LEFT)
        tk.Label(nt, text="Educational Sandbox", font=(SF, 11, "bold"),
                 bg=P["notice_bg"], fg=P["txt_dark"]).pack(anchor=tk.W)
        tk.Label(nt, text="Keys logged only within this application window",
                 font=(SF, 11), bg=P["notice_bg"], fg=P["txt_gray"]).pack(anchor=tk.W)

    def _stat_card(self, parent, label, var, val_fg, col):
        pad = (0, 6) if col < 2 else (0, 0)
        outer = tk.Frame(parent, bg=P["card_border"])
        outer.grid(row=0, column=col, sticky="nsew", padx=pad)

        inner = tk.Frame(outer, bg=P["card_bg"], height=76)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner.pack_propagate(False)

        top = tk.Frame(inner, bg=P["card_bg"])
        top.pack(fill=tk.X, padx=12, pady=(8, 0))
        tk.Label(top, text=label, font=(SF, 9, "bold"),
                 bg=P["card_bg"], fg=P["txt_gray"]).pack(side=tk.LEFT)

        tk.Label(inner, textvariable=var, font=(SF, 22, "bold"),
                 bg=P["card_bg"], fg=val_fg).pack(anchor=tk.W, padx=12)

    # ─────────────────────────────────────────────────────────────────────────
    #  RIGHT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, body: tk.Frame) -> None:
        outer = tk.Frame(body, bg=P["right_border"])
        outer.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 10))

        card = tk.Frame(outer, bg=P["right_bg"])
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)   # log rows expand

        # ── header ────────────────────────────────────
        hdr = tk.Frame(card, bg=P["right_bg"])
        hdr.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        # left: icon + title + subtitle
        lh = tk.Frame(hdr, bg=P["right_bg"])
        lh.grid(row=0, column=0, sticky="w")

        tr = tk.Frame(lh, bg=P["right_bg"])
        tr.pack(anchor=tk.W)
        tk.Label(tr, text="⌨", font=(SF, 14),
                 bg=P["right_bg"], fg="#4A7FA5").pack(side=tk.LEFT, padx=(0, 7))
        tk.Label(tr, text="Keystroke Log", font=(SF, 18, "bold"),
                 bg=P["right_bg"], fg=P["txt_white"]).pack(side=tk.LEFT)

        tk.Label(lh,
                 text="Chronological event stream with instant keycap resolution.",
                 font=(SF, 11), bg=P["right_bg"], fg=P["txt_light"]
                 ).pack(anchor=tk.W, pady=(3, 0))

        # right: search box
        sb = tk.Frame(hdr, bg=P["search_border"])
        sb.grid(row=0, column=1, sticky="e")

        si = tk.Frame(sb, bg=P["search_bg"])
        si.pack(padx=1, pady=1)

        tk.Label(si, text="🔍", font=(SF, 10),
                 bg=P["search_bg"], fg="#5A7499").pack(side=tk.LEFT, padx=(8, 3), pady=8)

        self._fvar = tk.StringVar()
        self._fentry = tk.Entry(
            si, textvariable=self._fvar,
            font=(MF, 10), bg=P["search_bg"], fg="#7E97BA",
            insertbackground="#8899BB", relief=tk.FLAT, bd=0, width=16,
        )
        self._fentry.pack(side=tk.LEFT, padx=(0, 10), pady=8)
        self._fentry.insert(0, PH)
        self._fentry.bind("<FocusIn>",  self._flt_in)
        self._fentry.bind("<FocusOut>", self._flt_out)
        self._fvar.trace_add("write", self._flt_changed)

        # ── divider ────────────────────────────────────
        tk.Frame(card, bg=P["right_div"], height=1).grid(
            row=1, column=0, sticky="ew", pady=(14, 0))

        # ── column headers ─────────────────────────────
        ch = tk.Frame(card, bg=P["col_hdr_bg"], height=40)
        ch.grid(row=2, column=0, sticky="ew")
        ch.pack_propagate(False)
        ch.columnconfigure(0, weight=34, uniform="col")
        ch.columnconfigure(1, weight=28, uniform="col")
        ch.columnconfigure(2, weight=38, uniform="col")

        tk.Label(ch, text="TIMESTAMP", font=(SF, 9, "bold"),
                 bg=P["col_hdr_bg"], fg=P["col_hdr_fg"],
                 anchor=tk.W, padx=20).grid(row=0, column=0, sticky="nsew")
        tk.Label(ch, text="EVENT", font=(SF, 9, "bold"),
                 bg=P["col_hdr_bg"], fg=P["col_hdr_fg"],
                 anchor=tk.W).grid(row=0, column=1, sticky="nsew")
        tk.Label(ch, text="CAPTURED KEY", font=(SF, 9, "bold"),
                 bg=P["col_hdr_bg"], fg=P["col_hdr_fg"],
                 anchor=tk.E, padx=20).grid(row=0, column=2, sticky="nsew")

        # ── scrollable log list ────────────────────────
        lf = tk.Frame(card, bg=P["right_bg"])
        lf.grid(row=3, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)

        vsb = tk.Scrollbar(lf, orient=tk.VERTICAL, width=6)
        vsb.grid(row=0, column=1, sticky="ns")

        self._cv = tk.Canvas(lf, bg=P["right_bg"],
                             bd=0, highlightthickness=0,
                             yscrollcommand=vsb.set)
        self._cv.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._cv.yview)

        self._log_f = tk.Frame(self._cv, bg=P["right_bg"])
        self._cwin  = self._cv.create_window((0, 0), window=self._log_f, anchor="nw")

        self._log_f.bind("<Configure>",
            lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.bind("<Configure>",
            lambda e: self._cv.itemconfig(self._cwin, width=e.width))

        for w in (self._cv, self._log_f):
            w.bind("<MouseWheel>", self._scroll)
            w.bind("<Button-4>",   self._scroll)
            w.bind("<Button-5>",   self._scroll)

    # ─────────────────────────────────────────────────────────────────────────
    #  ACTION BAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_action_bar(self) -> None:
        bar = tk.Frame(self, bg=P["action_bg"], height=78)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        tk.Frame(bar, bg=P["action_border"], height=1).pack(fill=tk.X, side=tk.TOP)

        row = tk.Frame(bar, bg=P["action_bg"])
        row.pack(fill=tk.BOTH, expand=True, padx=18)

        # Left buttons
        bl = tk.Frame(row, bg=P["action_bg"])
        bl.pack(side=tk.LEFT, fill=tk.Y)

        self._btn_start = self._btn(
            bl, "▶  Start Logging", P["blue"],  P["blue_h"],  self._cmd_start)
        self._btn_start.pack(side=tk.LEFT, padx=(0, 10), pady=16)

        self._btn_stop = self._btn(
            bl, "⏹  Stop Logging",  P["slate"], P["slate_h"], self._cmd_stop)
        self._btn_stop.pack(side=tk.LEFT, padx=(0, 10), pady=16)

        self._btn_save = self._btn(
            bl, "⬇  Save Log (.txt)", P["green"], P["green_h"], self._cmd_save)
        self._btn_save.pack(side=tk.LEFT, padx=(0, 10), pady=16)

        self._btn_clear = self._btn(
            bl, "🗑  Clear", "#FFFFFF", "#FEE2E2", self._cmd_clear, outline=True)
        self._btn_clear.pack(side=tk.LEFT, pady=16)

        # Right session card
        sc = tk.Frame(row, bg=P["session_border"])
        sc.pack(side=tk.RIGHT, pady=16)

        sci = tk.Frame(sc, bg=P["card_bg"])
        sci.pack(padx=1, pady=1)

        sr = tk.Frame(sci, bg=P["card_bg"])
        sr.pack(fill=tk.X, padx=16, pady=(10, 4))
        tk.Label(sr, text="⏱  Session:", font=(SF, 12),
                 bg=P["card_bg"], fg=P["txt_gray"]).pack(side=tk.LEFT, padx=(0, 6))
        self._tvar = tk.StringVar(value="00m 00s")
        tk.Label(sr, textvariable=self._tvar, font=(MF, 12, "bold"),
                 bg=P["card_bg"], fg=P["txt_dark"]).pack(side=tk.LEFT)

        tk.Frame(sci, bg=P["session_border"], height=1).pack(fill=tk.X, padx=16)

        kr = tk.Frame(sci, bg=P["card_bg"])
        kr.pack(fill=tk.X, padx=16, pady=(4, 10))
        tk.Label(kr, text="Logged Keys:", font=(SF, 12),
                 bg=P["card_bg"], fg=P["txt_gray"]).pack(side=tk.LEFT, padx=(0, 6))
        self._kvar = tk.StringVar(value="0")
        tk.Label(kr, textvariable=self._kvar, font=(MF, 12, "bold"),
                 bg=P["card_bg"], fg=P["blue"]).pack(side=tk.LEFT)

    def _btn(self, parent, text, bg, hover, cmd, outline=False):
        kw = dict(text=text, font=(SF, 13, "bold"),
                  relief=tk.FLAT, bd=0, padx=18, pady=10,
                  cursor="hand2", command=cmd)
        if outline:
            b = tk.Button(parent, bg="#FFFFFF", fg=P["red_fg"],
                          activebackground="#FEE2E2", activeforeground=P["red_h"],
                          highlightbackground=P["red_fg"], highlightthickness=1, **kw)
        else:
            b = tk.Button(parent, bg=bg, fg="#FFFFFF",
                          activebackground=hover, activeforeground="#FFFFFF", **kw)
        return b

    # ─────────────────────────────────────────────────────────────────────────
    #  FOOTER
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self) -> None:
        bar = tk.Frame(self, bg=P["footer"], height=46)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=P["footer"])
        inner.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        tk.Label(inner, text="🛡", font=(SF, 13),
                 bg=P["footer"], fg=P["badge_fg"]).pack(side=tk.LEFT, padx=(0, 8), pady=12)
        tk.Label(inner,
                 text="Offline Educational Keylogger  •  Data stored locally only",
                 font=(SF, 12), bg=P["footer"], fg="#A8B8CC").pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────────────────
    #  KEY CAPTURE
    # ─────────────────────────────────────────────────────────────────────────
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

    def _on_modified(self, _e) -> None:
        self._ta.edit_modified(False)
        t = self._ta.get("1.0", tk.END)
        self._char_var.set(str(count_chars(t)))
        self._word_var.set(str(count_words(t)))

    # ─────────────────────────────────────────────────────────────────────────
    #  LOG ROWS
    # ─────────────────────────────────────────────────────────────────────────
    def _push(self, entry: LogEntry) -> None:
        self._rows.insert(0, {
            "ts": entry.timestamp, "ev": entry.event_type, "key": entry.key})
        self._redraw()

    def _redraw(self) -> None:
        for w in self._log_f.winfo_children():
            w.destroy()

        flt = ""
        if self._flt_active:
            raw = self._fvar.get().strip()
            if raw != PH:
                flt = raw.lower()

        rows = [r for r in self._rows
                if not flt or flt in r["ts"].lower()
                or flt in r["ev"].lower() or flt in r["key"].lower()]

        for i, r in enumerate(rows):
            self._draw_row(r, i, newest=(i == 0))

    def _draw_row(self, row: dict, idx: int, newest: bool) -> None:
        bg = P["right_bg"] if idx % 2 == 0 else P["row_alt"]

        f = tk.Frame(self._log_f, bg=bg, height=48)
        f.pack(fill=tk.X)
        f.pack_propagate(False)
        f.columnconfigure(0, weight=34, uniform="rc")
        f.columnconfigure(1, weight=28, uniform="rc")
        f.columnconfigure(2, weight=38, uniform="rc")

        # left accent bar (only on newest row)
        ac = P["accent"] if newest else bg
        tk.Frame(f, bg=ac, width=3).pack(side=tk.LEFT, fill=tk.Y)

        # timestamp
        tk.Label(f, text=row["ts"], font=(MF, 12),
                 bg=bg, fg=P["ts_fg"], anchor=tk.W,
                 padx=18, pady=0).pack(side=tk.LEFT, fill=tk.Y)

        # event badge
        self._event_badge(f, row["ev"], row["key"]).pack(
            side=tk.LEFT, padx=(4, 0), pady=10)

        # key chip
        self._key_chip(f, row["key"]).pack(
            side=tk.RIGHT, padx=(0, 18), pady=10)

        # row divider
        tk.Frame(self._log_f, bg=P["right_div"], height=1).pack(fill=tk.X)

    def _event_badge(self, parent, ev: str, key: str) -> tk.Frame:
        if key == "Backspace":
            bg, fg, bdr = P["bs_bg"], P["bs_fg"], P["bs_bdr"]
        elif ev == "KeyDown":
            bg, fg, bdr = P["kd_bg"], P["kd_fg"], P["kd_bg"]
        else:
            bg, fg, bdr = P["kr_bg"], P["kr_fg"], P["kr_bg"]

        outer = tk.Frame(parent, bg=bdr)
        tk.Frame(outer, bg=bg, padx=1, pady=1).pack()
        inner = tk.Frame(outer, bg=bg)
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=ev, font=(SF, 10, "bold"),
                 bg=bg, fg=fg, padx=8, pady=2).pack()
        return outer

    _KL = {   # key → display label
        "Enter":     "Enter ↵",
        "Space":     "Space ␣",
        "Backspace": "Backspace ⌫",
        "Tab":       "Tab ⇥",
        "Escape":    "Esc",
        "Shift_L":   "Shift_L ⇧",
        "Shift_R":   "Shift_R ⇧",
        "Control_L": "Ctrl_L",
        "Control_R": "Ctrl_R",
        "Alt_L":     "Alt_L",
        "Alt_R":     "Alt_R",
        "CapsLock":  "CapsLock ⇪",
        "Delete":    "Del ⌦",
        "Up":        "↑", "Down": "↓", "Left": "←", "Right": "→",
    }

    _CS = {   # key → (bg, fg, border)
        "Enter":     ("#1E4EA8", "#BFD8FF", "#3B82F6"),
        "Space":     ("#1B3A5C", "#8CB8E8", "#2E5F8A"),
        "Backspace": ("#47320C", "#FFC857", "#F59E0B"),
        "Escape":    ("#5C1A1A", "#FCA5A5", "#EF4444"),
        "Tab":       ("#2E1F5C", "#C4B5FD", "#7C3AED"),
        "Shift_L":   ("#1E3A4A", "#93C5D0", "#2D7D9A"),
        "Shift_R":   ("#1E3A4A", "#93C5D0", "#2D7D9A"),
        "CapsLock":  ("#1E3A4A", "#93C5D0", "#2D7D9A"),
    }

    def _key_chip(self, parent, key: str) -> tk.Frame:
        label   = self._KL.get(key, key if len(key) > 1 else key.upper())
        display = f"[{label}]"
        bg, fg, bdr = self._CS.get(key, (P["chip_bg"], P["chip_fg"], P["chip_bdr"]))

        outer = tk.Frame(parent, bg=bdr)
        inner = tk.Frame(outer, bg=bg)
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=display, font=(MF, 11),
                 bg=bg, fg=fg, padx=7, pady=2).pack()
        return outer

    # ─────────────────────────────────────────────────────────────────────────
    #  SCROLL / FILTER
    # ─────────────────────────────────────────────────────────────────────────
    def _scroll(self, event: tk.Event) -> None:
        if   event.num == 4: self._cv.yview_scroll(-1, "units")
        elif event.num == 5: self._cv.yview_scroll( 1, "units")
        else: self._cv.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _flt_in(self, _e) -> None:
        self._flt_active = True
        if self._fentry.get() == PH:
            self._fentry.delete(0, tk.END)
            self._fentry.config(fg="#C8D8EE")

    def _flt_out(self, _e) -> None:
        self._flt_active = False
        if not self._fentry.get().strip():
            self._fentry.insert(0, PH)
            self._fentry.config(fg="#7E97BA")
        self._redraw()

    def _flt_changed(self, *_) -> None:
        if self._flt_active:
            self._redraw()

    # ─────────────────────────────────────────────────────────────────────────
    #  COMMANDS
    # ─────────────────────────────────────────────────────────────────────────
    def _cmd_start(self) -> None:
        self.logger.start()
        self._set_btn_states()
        self._set_badge(True)
        self._ta.focus_set()
        self._tick()

    def _cmd_stop(self) -> None:
        self.logger.stop()
        self._set_btn_states()
        self._set_badge(False)
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
        except OSError as exc:
            messagebox.showerror("KeyTrace", f"Could not save:\n{exc}")

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
        for w in self._log_f.winfo_children():
            w.destroy()
        self._set_btn_states()
        self._set_badge(False)

    def _set_btn_states(self) -> None:
        active = self.logger.is_active
        self._btn_start.config(state=tk.DISABLED if active else tk.NORMAL)
        self._btn_stop.config( state=tk.NORMAL   if active else tk.DISABLED)

    def _set_badge(self, active: bool) -> None:
        if active:
            self._badge_frame.config(bg=P["badge_border"])
            self._badge_inner.config(bg=P["badge_bg"])
            self._badge_dot.config(fg=P["badge_fg"], bg=P["badge_bg"])
            self._badge_lbl.config(text="Logging Active",
                                   fg=P["badge_fg"], bg=P["badge_bg"])
        else:
            self._badge_frame.config(bg="#3A4A5C")
            self._badge_inner.config(bg="#1E2A38")
            self._badge_dot.config(fg="#6B7E95", bg="#1E2A38")
            self._badge_lbl.config(text="Logging Inactive",
                                   fg="#6B7E95", bg="#1E2A38")

    def _tick(self) -> None:
        if not self.logger.is_active:
            return
        self._tvar.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
