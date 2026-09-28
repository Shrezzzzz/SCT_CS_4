"""
ui.py — KeyTrace  (final)
Single source of truth: the attached reference image.
1366 × 768, non-resizable, pure Tkinter + stdlib.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ── Palette (exact) ──────────────────────────────────────────────────────────
BG      = "#E9EEF5"   # window background
NAVBAR  = "#27344A"   # nav bar + footer
RPANEL  = "#16243A"   # right panel
WHITE   = "#FFFFFF"
BORDER  = "#D6E0EC"
DIVIDER = "#DCE6F2"
BLUE    = "#2563EB"
GREEN   = "#16A34A"
RED     = "#EF4444"
TXT1    = "#1F2937"   # primary text
TXT2    = "#64748B"   # secondary text

# right-panel specifics
RROW1   = "#16243A"   # even rows
RROW2   = "#1A2942"   # odd rows  (subtle)
RCOL_BG = "#0E1B2F"   # column header
RCOL_FG = "#8FA4C0"   # column header text
RTS     = "#7A94B4"   # timestamp
RDIV    = "#243451"   # row divider
SFLD    = "#102038"   # search field bg
SFLD_B  = "#35527A"   # search field border

# badges
KD_BG   = "#1D4ED8";  KD_FG = "#BFDBFE"   # KeyDown
KR_BG   = "#374151";  KR_FG = "#D1D5DB"   # KeyRelease
BS_BG   = "#78350F";  BS_FG = "#FDE68A"   # Backspace (amber)
EN_BG   = "#1D4ED8";  EN_FG = "#FFFFFF"   # Enter (bright blue)

# key chips (defaults + specials)
CHIP_BG = "#1E3A5F";  CHIP_FG = "#93C5FD"; CHIP_BD = "#2E5A8A"
CHIP_SPECIAL = {
    "Enter":     ("#1D4ED8", "#FFFFFF",  "#3B82F6"),
    "Space":     ("#1E3A5F", "#93C5FD",  "#2E5A8A"),
    "Backspace": ("#78350F", "#FDE68A",  "#D97706"),
    "Escape":    ("#7F1D1D", "#FCA5A5",  "#DC2626"),
    "Tab":       ("#3B0764", "#DDD6FE",  "#7C3AED"),
    "Shift_L":   ("#164E63", "#A5F3FC",  "#0891B2"),
    "Shift_R":   ("#164E63", "#A5F3FC",  "#0891B2"),
    "CapsLock":  ("#164E63", "#A5F3FC",  "#0891B2"),
}

KEY_LABEL = {
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
    "Up": "↑", "Down": "↓", "Left": "←", "Right": "→",
}

SF  = "Segoe UI"    # system sans-serif
MF  = "Consolas"    # monospace
PH  = "Filter keystrokes..."

IS_MAC = sys.platform == "darwin"


# ─────────────────────────────────────────────────────────────────────────────

class KeyTraceApp(tk.Tk):

    W, H = 1366, 768

    def __init__(self) -> None:
        super().__init__()
        self.logger      = KeystrokeLogger()
        self._rows: List[dict] = []
        self._timer_id   = None
        self._flt_on     = False   # filter entry has focus

        self._setup_window()
        self._build()
        self._refresh_btn_states()

    # ── window ───────────────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

    # ── build order: footer → action bar → navbar → body ─────────────────────
    def _build(self) -> None:
        self._build_footer()
        self._build_action_bar()
        self._build_navbar()
        self._build_body()

    # ─────────────────────────────────────────────────────────────────────────
    #  NAVBAR  (56 px)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_navbar(self) -> None:
        nav = tk.Frame(self, bg=NAVBAR, height=56)
        nav.pack(side=tk.TOP, fill=tk.X)
        nav.pack_propagate(False)

        # left ──────────────────────
        lf = tk.Frame(nav, bg=NAVBAR)
        lf.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 0))

        # traffic light circles — deferred so canvas has real size
        tl = tk.Canvas(lf, bg=NAVBAR, width=58, height=56,
                       bd=0, highlightthickness=0)
        tl.pack(side=tk.LEFT, padx=(0, 14))

        def _draw_tl():
            for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
                cx = 7 + i * 20
                tl.create_oval(cx-6, 22, cx+6, 34, fill=c, outline=c)

        self.after(10, _draw_tl)

        tk.Label(lf, text="⌨", font=(SF, 13),
                 bg=NAVBAR, fg="#8FA4C0").pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(lf, text="KeyTrace", font=(SF, 16, "bold"),
                 bg=NAVBAR, fg=WHITE).pack(side=tk.LEFT)

        # right ─────────────────────
        rf = tk.Frame(nav, bg=NAVBAR)
        rf.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 16))

        self._badge_f = tk.Frame(rf, bg="#334155", padx=1, pady=1)
        self._badge_f.pack(side=tk.RIGHT, pady=13)

        self._badge_i = tk.Frame(self._badge_f, bg="#1E293B")
        self._badge_i.pack()

        self._dot = tk.Label(self._badge_i, text="●", font=(SF, 8),
                             bg="#1E293B", fg="#64748B")
        self._dot.pack(side=tk.LEFT, padx=(12, 3), pady=7)

        self._badge_t = tk.Label(self._badge_i, text="Logging Inactive",
                                 font=(SF, 11, "bold"),
                                 bg="#1E293B", fg="#64748B")
        self._badge_t.pack(side=tk.LEFT, padx=(0, 12), pady=7)

        tk.Frame(self, bg="#1E2B3D", height=1).pack(side=tk.TOP, fill=tk.X)

    # ─────────────────────────────────────────────────────────────────────────
    #  BODY
    # ─────────────────────────────────────────────────────────────────────────
    def _build_body(self) -> None:
        body = tk.Frame(self, bg=BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=16, pady=(10, 0))
        # Fixed pixel split: left ~42%, right ~58%
        # Use minsize so left never crowds right panel
        body.columnconfigure(0, weight=42, minsize=420)
        body.columnconfigure(1, weight=58, minsize=560)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    # ─────────────────────────────────────────────────────────────────────────
    #  LEFT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, body: tk.Frame) -> None:
        # border wrapper → white card
        wrap = tk.Frame(body, bg=BORDER)
        wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 12))

        card = tk.Frame(wrap, bg=WHITE)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        card.columnconfigure(0, weight=1)
        # rows: heading=0, subtitle=1, divider=2, stats=3, textarea=4, notice=5
        card.rowconfigure(4, weight=1, minsize=180)   # textarea expands, minimum 180px

        # ── A. Heading ───────────────────────────────
        hrow = tk.Frame(card, bg=WHITE)
        hrow.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 0))

        tk.Label(hrow, text="✏", font=(SF, 11),
                 bg=WHITE, fg=BLUE).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(hrow, text="Typing Area", font=(SF, 15, "bold"),
                 bg=WHITE, fg=TXT1).pack(side=tk.LEFT)

        tk.Label(card,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=(SF, 11), bg=WHITE, fg=TXT2,
                 wraplength=340, justify=tk.LEFT
                 ).grid(row=1, column=0, sticky="w", padx=24, pady=(4, 0))

        tk.Frame(card, bg=DIVIDER, height=1).grid(
            row=2, column=0, sticky="ew", padx=24, pady=(14, 0))

        # ── B. Statistics ────────────────────────────
        sr = tk.Frame(card, bg=WHITE)
        sr.grid(row=3, column=0, sticky="ew", padx=24, pady=(12, 0))
        sr.columnconfigure(0, weight=1, uniform="s")
        sr.columnconfigure(1, weight=1, uniform="s")

        self._cvar = tk.StringVar(value="0")
        self._wvar = tk.StringVar(value="0")
        self._stat(sr, "CHARACTERS", self._cvar, BLUE,  0)
        self._stat(sr, "WORDS",      self._wvar, TXT1,  1)

        # ── C. Typing text box ───────────────────────
        ta_wrap = tk.Frame(card, bg=BORDER)
        ta_wrap.grid(row=4, column=0, sticky="nsew", padx=24, pady=(12, 0))
        ta_wrap.columnconfigure(0, weight=1)
        ta_wrap.rowconfigure(0, weight=1)

        self._ta = tk.Text(
            ta_wrap, font=(SF, 13), bg=WHITE, fg=TXT1,
            insertbackground=BLUE,
            relief=tk.FLAT, bd=14, wrap=tk.WORD, undo=True,
            selectbackground=BLUE, selectforeground=WHITE,
            highlightthickness=0,
        )
        self._ta.grid(row=0, column=0, sticky="nsew")
        self._ta.bind("<Key>",        self._on_kp)
        self._ta.bind("<KeyRelease>", self._on_kr)
        self._ta.bind("<<Modified>>", self._on_mod)

        # ── D. Educational notice ────────────────────
        notice_wrap = tk.Frame(card, bg="#D6E6FF")
        notice_wrap.grid(row=5, column=0, sticky="ew", padx=24, pady=(12, 22))

        notice = tk.Frame(notice_wrap, bg="#F3F8FF")
        notice.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        nr = tk.Frame(notice, bg="#F3F8FF")
        nr.pack(fill=tk.X, padx=14, pady=12)

        tk.Label(nr, text="🛡", font=(SF, 13),
                 bg="#F3F8FF", fg=BLUE).pack(side=tk.LEFT, padx=(0, 8))
        nt = tk.Frame(nr, bg="#F3F8FF")
        nt.pack(side=tk.LEFT)
        tk.Label(nt, text="Educational Sandbox", font=(SF, 11, "bold"),
                 bg="#F3F8FF", fg=TXT1).pack(anchor=tk.W)
        tk.Label(nt, text="Keys logged only within this application window",
                 font=(SF, 10), bg="#F3F8FF", fg=TXT2).pack(anchor=tk.W)

    def _stat(self, parent, label, var, vfg, col):
        pad = (0, 8) if col == 0 else (0, 0)
        f = tk.Frame(parent, bg=BORDER)
        f.grid(row=0, column=col, sticky="nsew", padx=pad)

        inner = tk.Frame(f, bg=WHITE, height=84)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner.pack_propagate(False)

        top = tk.Frame(inner, bg=WHITE)
        top.pack(fill=tk.X, padx=12, pady=(10, 0))
        tk.Label(top, text=label, font=(SF, 9, "bold"),
                 bg=WHITE, fg=TXT2).pack(side=tk.LEFT)

        tk.Label(inner, textvariable=var, font=(SF, 26, "bold"),
                 bg=WHITE, fg=vfg).pack(anchor=tk.W, padx=12, pady=(2, 0))

    # ─────────────────────────────────────────────────────────────────────────
    #  RIGHT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, body: tk.Frame) -> None:
        wrap = tk.Frame(body, bg="#0E1B30")
        wrap.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 12))

        card = tk.Frame(wrap, bg=RPANEL)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        # ── Header ───────────────────────────────────
        # Use a single row: [title+subtitle expands] [search stays right]
        hdr = tk.Frame(card, bg=RPANEL)
        hdr.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)   # title side expands
        hdr.columnconfigure(1, weight=0)   # search stays fixed width

        # Left: icon + title on row 0, subtitle on row 1
        lh = tk.Frame(hdr, bg=RPANEL)
        lh.grid(row=0, column=0, sticky="w", rowspan=2)

        tr = tk.Frame(lh, bg=RPANEL)
        tr.pack(anchor=tk.W)

        # small green terminal icon badge
        ib = tk.Frame(tr, bg="#0D6E4F")
        ib.pack(side=tk.LEFT, padx=(0, 8))
        ii = tk.Frame(ib, bg="#0A5C42")
        ii.pack(padx=1, pady=1)
        tk.Label(ii, text=">_", font=(MF, 9, "bold"),
                 bg="#0A5C42", fg="#34D399", padx=3, pady=1).pack()

        tk.Label(tr, text="Live Keystroke Log", font=(SF, 16, "bold"),
                 bg=RPANEL, fg=WHITE).pack(side=tk.LEFT)

        tk.Label(lh,
                 text="Chronological event stream with instant keycap resolution.",
                 font=(SF, 11), bg=RPANEL, fg="#7A94B4"
                 ).pack(anchor=tk.W, pady=(3, 0))

        # Right: search box — on row 0 col 1, anchored NE so it sits top-right
        sf = tk.Frame(hdr, bg=SFLD_B)
        sf.grid(row=0, column=1, sticky="ne", rowspan=2, padx=(12, 0))
        si = tk.Frame(sf, bg=SFLD)
        si.pack(padx=1, pady=1)

        tk.Label(si, text="🔍", font=(SF, 9),
                 bg=SFLD, fg="#5A7499").pack(side=tk.LEFT, padx=(8, 2), pady=8)

        self._fvar = tk.StringVar()
        self._fe = tk.Entry(si, textvariable=self._fvar,
                            font=(MF, 10), bg=SFLD, fg="#7E97BA",
                            insertbackground="#8899BB",
                            relief=tk.FLAT, bd=0, width=17,
                            highlightthickness=0)
        self._fe.pack(side=tk.LEFT, padx=(0, 8), pady=8)
        self._fe.insert(0, PH)
        self._fe.bind("<FocusIn>",  self._fi)
        self._fe.bind("<FocusOut>", self._fo)
        self._fvar.trace_add("write", self._fc)

        # ── Divider ───────────────────────────────────
        tk.Frame(card, bg=RDIV, height=1).grid(
            row=1, column=0, sticky="ew", pady=(16, 0))

        # ── Column headers ────────────────────────────
        ch = tk.Frame(card, bg=RCOL_BG, height=42)
        ch.grid(row=2, column=0, sticky="ew")
        ch.pack_propagate(False)
        ch.columnconfigure(0, weight=34, uniform="c")
        ch.columnconfigure(1, weight=28, uniform="c")
        ch.columnconfigure(2, weight=38, uniform="c")

        for col, txt, anc, px in [
            (0, "TIMESTAMP",   tk.W, 20),
            (1, "EVENT",       tk.W,  0),
            (2, "CAPTURED KEY",tk.E, 20),
        ]:
            tk.Label(ch, text=txt, font=(SF, 9, "bold"),
                     bg=RCOL_BG, fg=RCOL_FG,
                     anchor=anc, padx=px
                     ).grid(row=0, column=col, sticky="nsew")

        # ── Scrollable rows ────────────────────────────
        lf = tk.Frame(card, bg=RPANEL)
        lf.grid(row=3, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)

        vsb = tk.Scrollbar(lf, orient=tk.VERTICAL, width=5)
        vsb.grid(row=0, column=1, sticky="ns")

        self._cv = tk.Canvas(lf, bg=RPANEL, bd=0,
                             highlightthickness=0,
                             yscrollcommand=vsb.set)
        self._cv.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._cv.yview)

        self._lf = tk.Frame(self._cv, bg=RPANEL)
        self._cw = self._cv.create_window((0, 0), window=self._lf, anchor="nw")

        self._lf.bind("<Configure>",
            lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")))
        self._cv.bind("<Configure>",
            lambda e: self._cv.itemconfig(self._cw, width=e.width))

        for w in (self._cv, self._lf):
            w.bind("<MouseWheel>", self._scroll)
            w.bind("<Button-4>",   self._scroll)
            w.bind("<Button-5>",   self._scroll)

    # ─────────────────────────────────────────────────────────────────────────
    #  ACTION BAR  (72 px)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_action_bar(self) -> None:
        bar = tk.Frame(self, bg="#EEF3F8", height=72)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        tk.Frame(bar, bg=BORDER, height=1).pack(fill=tk.X, side=tk.TOP)

        row = tk.Frame(bar, bg="#EEF3F8")
        row.pack(fill=tk.BOTH, expand=True, padx=20)

        # left buttons
        bl = tk.Frame(row, bg="#EEF3F8")
        bl.pack(side=tk.LEFT, fill=tk.Y)

        self._bs = self._mkbtn(bl, "▶  Start Logging",    BLUE,  "#1D4ED8", self._start)
        self._bs.pack(side=tk.LEFT, padx=(0, 10), pady=14)

        self._bx = self._mkbtn(bl, "⏸  Stop Logging",   "#5C6B7E", "#4B5A6D", self._stop)
        self._bx.pack(side=tk.LEFT, padx=(0, 10), pady=14)

        self._bv = self._mkbtn(bl, "⬇  Save Log (.txt)", GREEN, "#15803D", self._save)
        self._bv.pack(side=tk.LEFT, padx=(0, 10), pady=14)

        self._bc = self._mkbtn(bl, "🗑  Clear", WHITE, "#FEE2E2",
                               self._clear, outline=True)
        self._bc.pack(side=tk.LEFT, pady=14)

        # right session card
        sc = tk.Frame(row, bg=BORDER)
        sc.pack(side=tk.RIGHT, pady=14)

        sci = tk.Frame(sc, bg=WHITE)
        sci.pack(padx=1, pady=1)

        left_sc = tk.Frame(sci, bg=WHITE)
        left_sc.pack(side=tk.LEFT, padx=(14, 10), pady=10)

        tk.Label(left_sc, text="⏱", font=(SF, 11),
                 bg=WHITE, fg=TXT2).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(left_sc, text="Session:", font=(SF, 11),
                 bg=WHITE, fg=TXT2).pack(side=tk.LEFT, padx=(0, 4))
        self._tv = tk.StringVar(value="00m 00s")
        tk.Label(left_sc, textvariable=self._tv,
                 font=(MF, 11, "bold"), bg=WHITE, fg=TXT1).pack(side=tk.LEFT)

        tk.Frame(sci, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=8)

        right_sc = tk.Frame(sci, bg=WHITE)
        right_sc.pack(side=tk.LEFT, padx=(10, 14), pady=10)

        tk.Label(right_sc, text="Logged Keys:", font=(SF, 11),
                 bg=WHITE, fg=TXT2).pack(side=tk.LEFT, padx=(0, 4))
        self._kv = tk.StringVar(value="0")
        tk.Label(right_sc, textvariable=self._kv,
                 font=(MF, 11, "bold"), bg=WHITE, fg=BLUE).pack(side=tk.LEFT)

    def _mkbtn(self, parent, text, bg, hover, cmd, outline=False):
        """
        Cross-platform button that actually respects bg/fg on macOS.
        Uses Frame+Label on all platforms for consistency.
        """
        bdr   = RED   if outline else bg
        n_bg  = WHITE if outline else bg
        n_fg  = RED   if outline else WHITE
        # disabled: slate bg with white text at reduced opacity (still readable)
        d_bg  = "#8895A7" if not outline else "#E8D0D0"
        d_fg  = "#FFFFFF" if not outline else "#C09090"

        f = tk.Frame(parent, bg=bdr, cursor="hand2")

        lbl = tk.Label(f, text=text,
                       font=(SF, 12, "bold"),
                       bg=n_bg, fg=n_fg,
                       padx=16, pady=9,
                       cursor="hand2")
        lbl.pack(padx=1 if outline else 0,
                 pady=1 if outline else 0)

        # state
        f._off = False

        def _cfg(state=None, **kw):
            st = state if state is not None else kw.get("state")
            if st == tk.DISABLED:
                f._off = True
                lbl.config(bg=d_bg, fg=d_fg)
                tk.Frame.configure(f, bg=d_bg)
            elif st in (tk.NORMAL, "normal"):
                f._off = False
                lbl.config(bg=n_bg, fg=n_fg)
                tk.Frame.configure(f, bg=bdr)

        f.config = _cfg

        def _click(e):
            if not f._off:
                cmd()

        def _enter(e):
            if not f._off:
                lbl.config(bg=hover if not outline else "#FEF2F2")
                if not outline:
                    tk.Frame.configure(f, bg=hover)

        def _leave(e):
            if not f._off:
                lbl.config(bg=n_bg)
                tk.Frame.configure(f, bg=bdr)

        lbl.bind("<Button-1>", _click)
        f.bind("<Button-1>",   _click)
        lbl.bind("<Enter>", _enter)
        lbl.bind("<Leave>", _leave)

        return f

    # ─────────────────────────────────────────────────────────────────────────
    #  FOOTER  (36 px)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self) -> None:
        bar = tk.Frame(self, bg=NAVBAR, height=36)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=NAVBAR)
        inner.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        tk.Label(inner, text="🛡", font=(SF, 11),
                 bg=NAVBAR, fg="#34D399").pack(side=tk.LEFT, padx=(0, 6), pady=9)
        tk.Label(inner,
                 text="Offline Educational Keylogger  •  Data stored locally only",
                 font=(SF, 11), bg=NAVBAR, fg="#B0BDC8").pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────────────────
    #  KEY CAPTURE
    # ─────────────────────────────────────────────────────────────────────────
    def _on_kp(self, event: tk.Event) -> None:
        key   = resolve_key_name(event)
        entry = self.logger.record("KeyDown", key)
        if entry:
            self._push(entry)
            self._kv.set(str(self.logger.entry_count))

    def _on_kr(self, event: tk.Event) -> None:
        key   = resolve_key_name(event)
        entry = self.logger.record("KeyRelease", key)
        if entry:
            self._push(entry)
            self._kv.set(str(self.logger.entry_count))

    def _on_mod(self, _e) -> None:
        self._ta.edit_modified(False)
        t = self._ta.get("1.0", tk.END)
        self._cvar.set(str(count_chars(t)))
        self._wvar.set(str(count_words(t)))

    # ─────────────────────────────────────────────────────────────────────────
    #  LOG ROWS
    # ─────────────────────────────────────────────────────────────────────────
    def _push(self, entry: LogEntry) -> None:
        self._rows.insert(0, {
            "ts": entry.timestamp,
            "ev": entry.event_type,
            "key": entry.key,
        })
        self._redraw()

    def _redraw(self) -> None:
        for w in self._lf.winfo_children():
            w.destroy()

        flt = ""
        if self._flt_on:
            raw = self._fvar.get().strip()
            if raw and raw != PH:
                flt = raw.lower()

        visible = [r for r in self._rows
                   if not flt
                   or flt in r["ts"].lower()
                   or flt in r["ev"].lower()
                   or flt in r["key"].lower()]

        for i, r in enumerate(visible):
            self._row(r, i, newest=(i == 0))

    def _row(self, r: dict, idx: int, newest: bool) -> None:
        ROW_H = 46
        bg = RROW1 if idx % 2 == 0 else RROW2

        f = tk.Frame(self._lf, bg=bg, height=ROW_H)
        f.pack(fill=tk.X)
        f.pack_propagate(False)
        f.columnconfigure(0, weight=34, uniform="r")
        f.columnconfigure(1, weight=28, uniform="r")
        f.columnconfigure(2, weight=38, uniform="r")

        # left accent line on newest row
        tk.Frame(f, bg="#3B82F6" if newest else bg, width=3
                 ).pack(side=tk.LEFT, fill=tk.Y)

        # timestamp
        tk.Label(f, text=r["ts"], font=(MF, 11),
                 bg=bg, fg=RTS, anchor=tk.W,
                 padx=16).pack(side=tk.LEFT, fill=tk.Y)

        # event badge
        self._badge(f, r["ev"], r["key"]).pack(
            side=tk.LEFT, padx=(4, 0), pady=9)

        # key chip (right-aligned)
        self._chip(f, r["key"]).pack(
            side=tk.RIGHT, padx=(0, 16), pady=9)

        # row separator
        tk.Frame(self._lf, bg=RDIV, height=1).pack(fill=tk.X)

    def _badge(self, parent, ev: str, key: str) -> tk.Frame:
        if key == "Backspace":
            bg, fg = BS_BG, BS_FG
        elif ev == "KeyDown":
            bg, fg = KD_BG, KD_FG
        else:
            bg, fg = KR_BG, KR_FG

        f = tk.Frame(parent, bg=bg)
        tk.Label(f, text=ev, font=(SF, 9, "bold"),
                 bg=bg, fg=fg, padx=8, pady=3).pack()
        return f

    def _chip(self, parent, key: str) -> tk.Frame:
        label = KEY_LABEL.get(key, key if len(key) > 1 else key.upper())
        text  = f"[{label}]"
        bg, fg, bdr = CHIP_SPECIAL.get(key, (CHIP_BG, CHIP_FG, CHIP_BD))

        outer = tk.Frame(parent, bg=bdr)
        inner = tk.Frame(outer, bg=bg)
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=text, font=(MF, 10),
                 bg=bg, fg=fg, padx=6, pady=2).pack()
        return outer

    # ─────────────────────────────────────────────────────────────────────────
    #  SCROLL + FILTER
    # ─────────────────────────────────────────────────────────────────────────
    def _scroll(self, e: tk.Event) -> None:
        if   e.num == 4: self._cv.yview_scroll(-1, "units")
        elif e.num == 5: self._cv.yview_scroll( 1, "units")
        else: self._cv.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _fi(self, _e) -> None:
        self._flt_on = True
        if self._fe.get() == PH:
            self._fe.delete(0, tk.END)
            self._fe.config(fg="#C0D0E8")

    def _fo(self, _e) -> None:
        self._flt_on = False
        if not self._fe.get().strip():
            self._fe.insert(0, PH)
            self._fe.config(fg="#7E97BA")
        self._redraw()

    def _fc(self, *_) -> None:
        if self._flt_on:
            self._redraw()

    # ─────────────────────────────────────────────────────────────────────────
    #  COMMANDS
    # ─────────────────────────────────────────────────────────────────────────
    def _start(self) -> None:
        self.logger.start()
        self._refresh_btn_states()
        self._set_badge(True)
        self._ta.focus_set()
        self._tick()

    def _stop(self) -> None:
        self.logger.stop()
        self._refresh_btn_states()
        self._set_badge(False)
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    def _save(self) -> None:
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

    def _clear(self) -> None:
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self.logger.clear()
        self._rows.clear()
        self._ta.delete("1.0", tk.END)
        self._cvar.set("0")
        self._wvar.set("0")
        self._kv.set("0")
        self._tv.set("00m 00s")
        for w in self._lf.winfo_children():
            w.destroy()
        self._refresh_btn_states()
        self._set_badge(False)

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _refresh_btn_states(self) -> None:
        active = self.logger.is_active
        self._bs.config(state=tk.DISABLED if active  else tk.NORMAL)
        self._bx.config(state=tk.NORMAL   if active  else tk.DISABLED)

    def _set_badge(self, active: bool) -> None:
        if active:
            tk.Frame.configure(self._badge_f, bg="#0E8F64")
            self._badge_i.config(bg="#083D2E")
            self._dot.config(fg="#34D399",        bg="#083D2E")
            self._badge_t.config(text="Logging Active",
                                 fg="#34D399",    bg="#083D2E")
        else:
            tk.Frame.configure(self._badge_f, bg="#334155")
            self._badge_i.config(bg="#1E293B")
            self._dot.config(fg="#64748B",        bg="#1E293B")
            self._badge_t.config(text="Logging Inactive",
                                 fg="#64748B",    bg="#1E293B")

    def _tick(self) -> None:
        if not self.logger.is_active:
            return
        self._tv.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
