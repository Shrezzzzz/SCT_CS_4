"""
ui.py — KeyTrace
1366 × 768, non-resizable, pure Tkinter + stdlib.
Rounded panels via Canvas overlay technique.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ── Palette ──────────────────────────────────────────────────────────────────
BG      = "#E9EEF5"
NAVBAR  = "#27344A"
WHITE   = "#FFFFFF"
BLUE    = "#2563EB"
GREEN   = "#16A34A"
RED     = "#EF4444"
TXT1    = "#1F2937"
TXT2    = "#64748B"

# Right panel
RP      = "#162845"
RP_ROW1 = "#162845"
RP_ROW2 = "#1B304E"
RCOL_BG = "#0E1B2F"
RCOL_FG = "#8FA4C0"
RDIV    = "#29415F"

# Badges
KD_BG, KD_FG = "#1E4EA8", "#BFD8FF"   # KeyDown  — blue
KR_BG, KR_FG = "#374151", "#D1D5DB"   # KeyRelease — grey  ← FIXED
BS_BG, BS_FG = "#78350F", "#FDE68A"   # Backspace — amber

SF = "Segoe UI"
MF = "Consolas"
PH = "Filter keystrokes..."


def _resolve_fonts():
    """Pick the best available font on this platform."""
    global SF, MF
    import tkinter as tk
    from tkinter import font as tkfont
    try:
        root = tk.Tk()
        root.withdraw()
        available = set(tkfont.families())
        root.destroy()
    except Exception:
        return   # leave defaults if Tk isn't ready yet

    # Sans-serif: prefer Segoe UI (Win) → SF Pro / Helvetica Neue (macOS)
    #             → Liberation Sans / DejaVu Sans (Linux) → Arial → Helvetica
    for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue",
              "Liberation Sans", "DejaVu Sans", "Arial", "Helvetica"):
        if f in available:
            SF = f
            break

    # Monospace: prefer Consolas (Win) → Menlo / Monaco (macOS)
    #            → DejaVu Sans Mono / Liberation Mono (Linux) → Courier New
    for f in ("Consolas", "Menlo", "Monaco",
              "DejaVu Sans Mono", "Liberation Mono", "Courier New", "Courier"):
        if f in available:
            MF = f
            break


_resolve_fonts()


# ── Rounded-panel helper ──────────────────────────────────────────────────────
def _rrect(canvas: tk.Canvas, x1, y1, x2, y2, r, fill, outline="", width=0):
    """Draw a filled rounded rectangle on canvas."""
    pts = [
        x1+r, y1,  x2-r, y1,
        x2,   y1,  x2,   y1+r,
        x2,   y2-r, x2,  y2,
        x2-r, y2,  x1+r, y2,
        x1,   y2,  x1,   y2-r,
        x1,   y1+r, x1,  y1,
    ]
    return canvas.create_polygon(pts, smooth=True,
                                  fill=fill, outline=outline, width=width)


class RoundPanel(tk.Frame):
    """
    A Frame that draws its background as a rounded rectangle.
    Children should be placed inside  self.inner  (a plain Frame).
    radius=18 matches the reference design.
    """
    def __init__(self, master, bg_color, radius=18,
                 border_color=None, border_width=1, **kw):
        # The outer frame is transparent (matches parent bg)
        parent_bg = master.cget("bg") if hasattr(master, "cget") else BG
        super().__init__(master, bg=parent_bg, **kw)
        self._bg    = bg_color
        self._r     = radius
        self._bclr  = border_color
        self._bw    = border_width

        self._cv = tk.Canvas(self, bg=parent_bg,
                             bd=0, highlightthickness=0)
        self._cv.pack(fill=tk.BOTH, expand=True)

        self.inner = tk.Frame(self._cv, bg=bg_color)
        self._win  = self._cv.create_window(0, 0, window=self.inner,
                                             anchor="nw")

        self._cv.bind("<Configure>", self._redraw)

    def _redraw(self, _=None):
        w = self._cv.winfo_width()
        h = self._cv.winfo_height()
        if w < 4 or h < 4:
            return
        self._cv.delete("bg")
        if self._bclr:
            _rrect(self._cv, 0, 0, w, h, self._r,
                   fill=self._bclr, outline=self._bclr, width=0)
            _rrect(self._cv, self._bw, self._bw,
                   w-self._bw, h-self._bw,
                   max(1, self._r - self._bw),
                   fill=self._bg, outline=self._bg)
        else:
            _rrect(self._cv, 0, 0, w, h, self._r,
                   fill=self._bg, outline=self._bg)

        # Paint corner-masking rectangles over the inner Frame's square corners.
        # These fill the 4 corner regions with the parent background colour,
        # creating the illusion of rounded corners even though tk.Frame is square.
        r = self._r
        pbg = self._cv.cget("bg")
        for x, y in ((0, 0), (w-r, 0), (0, h-r), (w-r, h-r)):
            self._cv.create_rectangle(x, y, x+r, y+r,
                                       fill=pbg, outline=pbg, tags="bg")
        # Redraw the rounded rect on top of the corner masks
        if self._bclr:
            _rrect(self._cv, 0, 0, w, h, self._r,
                   fill=self._bclr, outline=self._bclr, width=0)
            _rrect(self._cv, self._bw, self._bw,
                   w-self._bw, h-self._bw,
                   max(1, self._r - self._bw),
                   fill=self._bg, outline=self._bg)
        else:
            _rrect(self._cv, 0, 0, w, h, self._r,
                   fill=self._bg, outline=self._bg)

        # Inner frame sits on top of everything
        self._cv.tag_raise(self._win)
        self._cv.itemconfig(self._win, width=w, height=h)
        self._cv.coords(self._win, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────

class KeyTraceApp(tk.Tk):

    W, H = 1366, 768

    def __init__(self) -> None:
        super().__init__()
        self.logger     = KeystrokeLogger()
        self._rows: List[dict] = []
        self._timer_id  = None
        self._flt_on    = False

        self._setup_window()
        self._build()
        self._refresh_btn_states()

    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

    def _build(self) -> None:
        self._build_footer()
        self._build_action_bar()
        self._build_navbar()
        self._build_body()

    # ─────────────────────────────────────────────────────────────────────────
    #  NAVBAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_navbar(self) -> None:
        nav = tk.Frame(self, bg=NAVBAR, height=56)
        nav.pack(side=tk.TOP, fill=tk.X)
        nav.pack_propagate(False)

        lf = tk.Frame(nav, bg=NAVBAR)
        lf.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 0))

        # Keyboard icon
        kc = tk.Canvas(lf, bg=NAVBAR, width=22, height=22,
                       bd=0, highlightthickness=0)
        kc.pack(side=tk.LEFT, padx=(0, 7))

        def _draw_kb():
            kc.delete("all")
            kc.create_rectangle(1, 5, 21, 17, outline=WHITE,
                                 fill="", width=1.5)
            for row_y in (9, 13):
                for kx in range(4, 19, 4):
                    kc.create_rectangle(kx, row_y, kx+2, row_y+2,
                                        fill=WHITE, outline="")
            kc.create_rectangle(6, 15, 16, 17, fill=WHITE, outline="")

        self.after(20, _draw_kb)

        tk.Label(lf, text="KeyTrace", font=(SF, 15, "bold"),
                 bg=NAVBAR, fg=WHITE).pack(side=tk.LEFT)

        # Badge (right) — no fixed width so text is never clipped
        rf = tk.Frame(nav, bg=NAVBAR)
        rf.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 18))

        self._badge_f = tk.Frame(rf, bg="#334155")
        self._badge_f.pack(side=tk.RIGHT, pady=14)

        self._badge_i = tk.Frame(self._badge_f, bg="#1E293B")
        self._badge_i.pack(padx=1, pady=1)

        self._dot = tk.Label(self._badge_i, text="●", font=(SF, 9),
                             bg="#1E293B", fg="#64748B")
        self._dot.pack(side=tk.LEFT, padx=(12, 4), pady=6)

        self._badge_t = tk.Label(self._badge_i, text="Logging Inactive",
                                 font=(SF, 10, "bold"),
                                 bg="#1E293B", fg="#64748B")
        self._badge_t.pack(side=tk.LEFT, padx=(0, 12), pady=6)

        tk.Frame(self, bg="#1E2B3D", height=1).pack(side=tk.TOP, fill=tk.X)

    # ─────────────────────────────────────────────────────────────────────────
    #  BODY
    # ─────────────────────────────────────────────────────────────────────────
    def _build_body(self) -> None:
        body = tk.Frame(self, bg=BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                  padx=16, pady=(10, 0))
        body.columnconfigure(0, weight=42, minsize=420)
        body.columnconfigure(1, weight=58, minsize=560)
        body.rowconfigure(0, weight=1)
        self._build_left(body)
        self._build_right(body)

    # ─────────────────────────────────────────────────────────────────────────
    #  LEFT PANEL  — white card matching HTML reference
    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, body: tk.Frame) -> None:
        # Outer white card — radius 20, box-shadow simulated by border
        panel = RoundPanel(body, bg_color=WHITE, radius=20,
                           border_color="#E0E6F0", border_width=1)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 12))

        card = panel.inner
        card.columnconfigure(0, weight=1)
        # row 3 = textarea, expands to fill remaining space
        card.rowconfigure(3, weight=1, minsize=160)

        # ── Header: icon + h1 + p ──────────────────────
        hrow = tk.Frame(card, bg=WHITE)
        hrow.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 0))

        # SVG icon equivalent: canvas-drawn lines + arrow
        ic_cv = tk.Canvas(hrow, bg=WHITE, width=20, height=20,
                          bd=0, highlightthickness=0)
        ic_cv.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 10), pady=(3, 0))
        # M4 6h13  M4 12h13  M4 18h7
        ic_cv.create_line(3, 5,  16, 5,  fill="#3B5BFD", width=1.8,
                          capstyle=tk.ROUND)
        ic_cv.create_line(3, 10, 16, 10, fill="#3B5BFD", width=1.8,
                          capstyle=tk.ROUND)
        ic_cv.create_line(3, 15, 10, 15, fill="#3B5BFD", width=1.8,
                          capstyle=tk.ROUND)
        # Arrow: M18 15l3 3-3 3
        ic_cv.create_line(17, 14, 20, 17, 17, 20,
                          fill="#3B5BFD", width=1.8,
                          capstyle=tk.ROUND, joinstyle=tk.ROUND)

        txt_c = tk.Frame(hrow, bg=WHITE)
        txt_c.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(txt_c, text="Typing Area",
                 font=(SF, 20, "bold"), bg=WHITE, fg="#1B2130"
                 ).pack(anchor=tk.W)
        tk.Label(txt_c,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=(SF, 13), bg=WHITE, fg="#8991A3",
                 wraplength=310, justify=tk.LEFT
                 ).pack(anchor=tk.W, pady=(3, 0))

        # ── hr: 1px #ececf0 ────────────────────────────
        tk.Frame(card, bg="#ECECF0", height=1).grid(
            row=1, column=0, sticky="ew", padx=28, pady=(20, 0))

        # ── Stats grid: 2 cols, gap 16, border-radius 14 ─
        sr = tk.Frame(card, bg=WHITE)
        sr.grid(row=2, column=0, sticky="ew", padx=28, pady=(16, 0))
        sr.columnconfigure(0, weight=1, uniform="s")
        sr.columnconfigure(1, weight=1, uniform="s")

        self._cvar = tk.StringVar(value="0")
        self._wvar = tk.StringVar(value="0")
        self._stat(sr, "CHARACTERS", self._cvar, "#3B5BFD", 0)
        self._stat(sr, "WORDS",      self._wvar, "#1B2130", 1)

        # ── Textarea: border-radius 14, bg #f9fafc, border #e4e7ee ──
        # RoundPanel gives the rounded border; Text widget sits inside
        ta_rp = RoundPanel(card, bg_color="#F9FAFC", radius=14,
                           border_color="#E4E7EE", border_width=1)
        ta_rp.grid(row=3, column=0, sticky="nsew", padx=28, pady=(16, 0))

        self._ta = tk.Text(
            ta_rp.inner,
            font=(SF, 14), bg="#F9FAFC", fg="#1B2130",
            insertbackground="#3B5BFD",
            relief=tk.FLAT, bd=18,
            wrap=tk.WORD, undo=True,
            selectbackground="#3B5BFD", selectforeground=WHITE,
            highlightthickness=0, spacing1=2, spacing3=2,
        )
        self._ta.pack(fill=tk.BOTH, expand=True)
        self._ta.bind("<Key>",        self._on_kp)
        self._ta.bind("<KeyRelease>", self._on_kr)
        self._ta.bind("<<Modified>>", self._on_mod)
        # focus: border-color #b9c3f7, background #fff
        self._ta.bind("<FocusIn>",
            lambda e: (self._ta.config(bg=WHITE),
                       ta_rp._cv.configure(bg=WHITE),
                       ta_rp.inner.config(bg=WHITE)))
        self._ta.bind("<FocusOut>",
            lambda e: (self._ta.config(bg="#F9FAFC"),
                       ta_rp._cv.configure(bg=BG),
                       ta_rp.inner.config(bg="#F9FAFC")))

        # ── Footer notice: border-radius 12, bg #eef1fd — fixed height ──
        nwrap = tk.Frame(card, bg=WHITE, height=72)
        nwrap.grid(row=4, column=0, sticky="ew", padx=28, pady=(14, 24))
        nwrap.pack_propagate(False)
        nwrap.grid_propagate(False)

        nrp = RoundPanel(nwrap, bg_color="#EEF1FD", radius=12)
        nrp.pack(fill=tk.BOTH, expand=True)

        ni = tk.Frame(nrp.inner, bg="#EEF1FD")
        ni.pack(fill=tk.X, padx=14, pady=10)

        # Shield SVG: M12 2l8 4v6c0 5... + checkmark
        sh = tk.Canvas(ni, bg="#EEF1FD", width=16, height=16,
                       bd=0, highlightthickness=0)
        sh.pack(side=tk.LEFT, padx=(0, 10), pady=1)
        sh.create_polygon(8,1, 15,4, 15,9, 8,15, 1,9, 1,4,
                          smooth=False, outline="#3B5BFD", fill="", width=1.5)
        sh.create_line(4,8, 7,11, 12,5, smooth=False,
                       fill="#3B5BFD", width=1.5,
                       capstyle=tk.ROUND, joinstyle=tk.ROUND)

        tk.Label(ni,
                 text="Educational Sandbox  •  Keys logged only within this application window",
                 font=(SF, 12), bg="#EEF1FD", fg="#5B6478",
                 wraplength=310, justify=tk.LEFT
                 ).pack(side=tk.LEFT, anchor=tk.W)

    def _stat(self, parent, label, var, vfg, col):
        """Stat card — fixed 92px height, snug around label+icon+number."""
        pad = (0, 14) if col == 0 else (0, 0)

        # Fixed-height container stops RoundPanel from stretching
        wrapper = tk.Frame(parent, bg=parent.cget("bg"), height=92)
        wrapper.grid(row=0, column=col, sticky="ew", padx=pad)
        wrapper.pack_propagate(False)
        wrapper.grid_propagate(False)

        # Rounded card fills the fixed wrapper
        rp = RoundPanel(wrapper, bg_color="#F4F6FA", radius=14)
        rp.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(rp.inner, bg="#F4F6FA")
        inner.pack(fill=tk.X, padx=12, pady=(10, 8))

        # stat-top: label left, icon right
        top = tk.Frame(inner, bg="#F4F6FA")
        top.pack(fill=tk.X, pady=(0, 6))

        tk.Label(top, text=label, font=(SF, 11, "bold"),
                 bg="#F4F6FA", fg="#8991A3").pack(side=tk.LEFT)

        # Canvas icon (stat-icon, color #b3bac8)
        if col == 0:
            # rect with "123" text inside
            ic = tk.Canvas(top, bg="#F4F6FA", width=18, height=14,
                           bd=0, highlightthickness=0)
            ic.pack(side=tk.RIGHT)
            ic.create_rectangle(0, 0, 17, 13, outline="#B3BAC8",
                                 width=1.2, fill="")
            ic.create_text(9, 7, text="123", font=(SF, 5),
                           fill="#B3BAC8", anchor="center")
        else:
            # 3 horizontal lines
            ic = tk.Canvas(top, bg="#F4F6FA", width=16, height=12,
                           bd=0, highlightthickness=0)
            ic.pack(side=tk.RIGHT)
            for y, x2 in ((1, 16), (6, 16), (11, 10)):
                ic.create_line(0, y, x2, y, fill="#B3BAC8", width=1.5,
                               capstyle=tk.ROUND)

        # stat-value: 32px bold, blue for chars, dark for words
        tk.Label(inner, textvariable=var, font=(SF, 24, "bold"),
                 bg="#F4F6FA", fg=vfg).pack(anchor=tk.W)

    # ─────────────────────────────────────────────────────────────────────────
    #  RIGHT PANEL  — rounded dark card
    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, body: tk.Frame) -> None:
        panel = RoundPanel(body, bg_color=RP, radius=18,
                           border_color="#0D1A2E", border_width=1)
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 12))

        card = panel.inner
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        # ── Header  88px ──────────────────────────────
        hdr = tk.Frame(card, bg=RP, height=88)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.pack_propagate(False)
        hdr.columnconfigure(0, weight=1)
        hdr.columnconfigure(1, weight=0)

        # Left: terminal icon + title + subtitle
        lh = tk.Frame(hdr, bg=RP)
        lh.grid(row=0, column=0, sticky="w", padx=(20, 10), pady=(18, 0))

        tr = tk.Frame(lh, bg=RP)
        tr.pack(anchor=tk.W)

        ib = tk.Frame(tr, bg="#0D5C3A", width=28, height=28)
        ib.pack(side=tk.LEFT, padx=(0, 10))
        ib.pack_propagate(False)
        tk.Label(ib, text=">_", font=(MF, 10, "bold"),
                 bg="#0D5C3A", fg="#34D399"
                 ).place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(tr, text="Keystroke Log", font=(SF, 16, "bold"),
                 bg=RP, fg=WHITE).pack(side=tk.LEFT)

        tk.Label(lh,
                 text="Chronological event stream with instant keycap resolution.",
                 font=(SF, 11), bg=RP, fg="#6B87A8"
                 ).pack(anchor=tk.W, pady=(4, 0))

        # Right: search box 220×42
        rh = tk.Frame(hdr, bg=RP)
        rh.grid(row=0, column=1, sticky="e", padx=(0, 20))

        sb_o = tk.Frame(rh, bg="#35527A")
        sb_o.pack(pady=23)   # (88-42)/2 = 23 → vertically centered

        sb_i = tk.Frame(sb_o, bg="#102038", width=220, height=42)
        sb_i.pack(padx=1, pady=1)
        sb_i.pack_propagate(False)

        tk.Label(sb_i, text="🔍", font=(SF, 10),
                 bg="#102038", fg="#4A6A8A"
                 ).pack(side=tk.LEFT, padx=(10, 3))

        self._fvar = tk.StringVar()
        self._fe = tk.Entry(sb_i, textvariable=self._fvar,
                            font=(SF, 11), bg="#102038", fg="#7E97BA",
                            insertbackground="#8899BB",
                            relief=tk.FLAT, bd=0, highlightthickness=0)
        self._fe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._fe.insert(0, PH)
        self._fe.bind("<FocusIn>",  self._fi)
        self._fe.bind("<FocusOut>", self._fo)
        self._fvar.trace_add("write", self._fc)

        # ── Divider ────────────────────────────────────
        tk.Frame(card, bg=RDIV, height=1).grid(row=1, column=0, sticky="ew")

        # ── Column headers ─────────────────────────────
        ch = tk.Frame(card, bg=RCOL_BG, height=44)
        ch.grid(row=2, column=0, sticky="ew")
        ch.pack_propagate(False)
        ch.columnconfigure(0, weight=34, uniform="c")
        ch.columnconfigure(1, weight=28, uniform="c")
        ch.columnconfigure(2, weight=38, uniform="c")
        for ci, txt, anc, px in [
            (0, "TIMESTAMP",    tk.W, 22),
            (1, "EVENT",        tk.W,  8),
            (2, "CAPTURED KEY", tk.E, 22),
        ]:
            tk.Label(ch, text=txt, font=(SF, 9, "bold"),
                     bg=RCOL_BG, fg=RCOL_FG,
                     anchor=anc, padx=px
                     ).grid(row=0, column=ci, sticky="nsew")

        # ── Scrollable log ─────────────────────────────
        lf = tk.Frame(card, bg=RP)
        lf.grid(row=3, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)

        vsb = tk.Scrollbar(lf, orient=tk.VERTICAL, width=5)
        vsb.grid(row=0, column=1, sticky="ns")

        self._cv = tk.Canvas(lf, bg=RP, bd=0,
                             highlightthickness=0,
                             yscrollcommand=vsb.set)
        self._cv.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._cv.yview)

        self._lf = tk.Frame(self._cv, bg=RP)
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
    #  ACTION BAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_action_bar(self) -> None:
        bar = tk.Frame(self, bg="#F4F7FA", height=64)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        tk.Frame(bar, bg="#DDE4EE", height=1).pack(fill=tk.X, side=tk.TOP)

        row = tk.Frame(bar, bg="#F4F7FA")
        row.pack(fill=tk.BOTH, expand=True, padx=20)

        bl = tk.Frame(row, bg="#F4F7FA")
        bl.pack(side=tk.LEFT, fill=tk.Y)

        self._bs = self._mkbtn(bl, "▶  Start Logging",
                               "#2563EB", "#1D4ED8", self._start)
        self._bs.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        self._bx = self._mkbtn(bl, "⏸  Stop Logging",
                               "#4B5563", "#374151", self._stop)
        self._bx.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        self._bv = self._mkbtn(bl, "⬇  Save Log (.txt)",
                               "#16A34A", "#15803D", self._save)
        self._bv.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        self._bc = self._mkbtn(bl, "🗑  Clear", WHITE, "#FEE2E2",
                               self._clear, outline=True)
        self._bc.pack(side=tk.LEFT, pady=12)

        # Session card
        sc = tk.Frame(row, bg="#F4F7FA",
                      highlightbackground="#D1D9E6", highlightthickness=1)
        sc.pack(side=tk.RIGHT, pady=12)

        sci = tk.Frame(sc, bg=WHITE)
        sci.pack(fill=tk.BOTH, expand=True)

        ls = tk.Frame(sci, bg=WHITE)
        ls.pack(side=tk.LEFT, padx=(14, 12), pady=10)
        tk.Label(ls, text="⏱", font=(SF, 11), bg=WHITE, fg=TXT2
                 ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(ls, text="Session:", font=(SF, 11), bg=WHITE, fg=TXT2
                 ).pack(side=tk.LEFT, padx=(0, 5))
        self._tv = tk.StringVar(value="00m 00s")
        tk.Label(ls, textvariable=self._tv,
                 font=(SF, 11, "bold"), bg=WHITE, fg=TXT1
                 ).pack(side=tk.LEFT)

        tk.Frame(sci, bg="#D1D9E6", width=1).pack(
            side=tk.LEFT, fill=tk.Y, pady=10)

        rs = tk.Frame(sci, bg=WHITE)
        rs.pack(side=tk.LEFT, padx=(12, 14), pady=10)
        tk.Label(rs, text="Logged Keys:", font=(SF, 11), bg=WHITE, fg=TXT2
                 ).pack(side=tk.LEFT, padx=(0, 5))
        self._kv = tk.StringVar(value="0")
        tk.Label(rs, textvariable=self._kv,
                 font=(SF, 11, "bold"), bg=WHITE, fg=BLUE
                 ).pack(side=tk.LEFT)

    def _mkbtn(self, parent, text, bg, hover, cmd, outline=False):
        bdr  = RED   if outline else bg
        n_bg = WHITE if outline else bg
        n_fg = RED   if outline else WHITE
        d_bg = "#8895A7" if not outline else "#E8D0D0"
        d_fg = WHITE     if not outline else "#C09090"

        f   = tk.Frame(parent, bg=bdr)
        lbl = tk.Label(f, text=text, font=(SF, 12, "bold"),
                       bg=n_bg, fg=n_fg, padx=16, pady=9)
        lbl.pack(padx=1 if outline else 0, pady=1 if outline else 0)

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

        lbl.bind("<Button-1>", lambda e: (not f._off) and cmd())
        f.bind("<Button-1>",   lambda e: (not f._off) and cmd())
        lbl.bind("<Enter>",    lambda e: not f._off and (
            lbl.config(bg=hover if not outline else "#FEF2F2"),
            tk.Frame.configure(f, bg=hover) if not outline else None))
        lbl.bind("<Leave>",    lambda e: not f._off and (
            lbl.config(bg=n_bg),
            tk.Frame.configure(f, bg=bdr)))
        return f

    # ─────────────────────────────────────────────────────────────────────────
    #  FOOTER
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self) -> None:
        bar = tk.Frame(self, bg="#27344A", height=40)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg="#27344A")
        inner.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        tk.Label(inner, text="🛡", font=(SF, 12),
                 bg="#27344A", fg="#34D399"
                 ).pack(side=tk.LEFT, padx=(0, 8), pady=10)
        tk.Label(inner,
                 text="Offline Educational Keylogger  •  Data stored locally only",
                 font=(SF, 11), bg="#27344A", fg="#94A3B8"
                 ).pack(side=tk.LEFT)

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
        bg = RP_ROW1 if idx % 2 == 0 else RP_ROW2

        f = tk.Frame(self._lf, bg=bg, height=52)
        f.pack(fill=tk.X)
        f.pack_propagate(False)

        # Blue accent on newest row only
        tk.Frame(f, bg="#3B82F6" if newest else bg, width=3
                 ).pack(side=tk.LEFT, fill=tk.Y)

        # Timestamp
        tk.Label(f, text=r["ts"], font=(MF, 12),
                 bg=bg, fg="#7A9EC8", anchor=tk.W, padx=16
                 ).pack(side=tk.LEFT, fill=tk.Y)

        # Chip RIGHT (pack before badge so it stays right)
        cf = tk.Frame(f, bg=bg)
        cf.pack(side=tk.RIGHT, padx=(0, 18), pady=11)
        self._chip(cf, r["key"])

        # Badge
        bf = tk.Frame(f, bg=bg)
        bf.pack(side=tk.LEFT, pady=13)
        self._badge(bf, r["ev"], r["key"])

    def _badge(self, parent: tk.Frame, ev: str, key: str) -> None:
        if key == "Backspace":
            bg, fg = BS_BG, BS_FG          # amber
        elif ev == "KeyDown":
            bg, fg = KD_BG, KD_FG          # blue
        else:
            bg, fg = KR_BG, KR_FG          # grey  ← FIXED (was red)

        tk.Label(parent, text=ev, font=(SF, 10, "bold"),
                 bg=bg, fg=fg, padx=10, pady=4).pack()

    _KL = {
        "Enter": "Enter ↵",  "Space": "Space ␣",
        "Backspace": "Backspace ⌫", "Tab": "Tab ⇥",
        "Escape": "Esc",
        "Shift_L": "Shift_L ⇧", "Shift_R": "Shift_R ⇧",
        "Control_L": "Ctrl_L",  "Control_R": "Ctrl_R",
        "Alt_L": "Alt_L",       "Alt_R": "Alt_R",
        "CapsLock": "CapsLock ⇪", "Delete": "Del ⌦",
        "Up": "↑", "Down": "↓", "Left": "←", "Right": "→",
        "Meta_L": "Cmd_L ⌘",   "Meta_R": "Cmd_R ⌘",
    }

    _CS = {
        "Enter":     ("#1D4ED8", "#FFFFFF", "#3B82F6"),
        "Space":     ("#1E3A5F", "#93C5FD", "#2E5A8A"),
        "Backspace": ("#78350F", "#FDE68A", "#D97706"),
        "Escape":    ("#7F1D1D", "#FCA5A5", "#DC2626"),
        "Tab":       ("#3B0764", "#DDD6FE", "#7C3AED"),
        "Shift_L":   ("#164E63", "#A5F3FC", "#0891B2"),
        "Shift_R":   ("#164E63", "#A5F3FC", "#0891B2"),
        "CapsLock":  ("#164E63", "#A5F3FC", "#0891B2"),
        "Meta_L":    ("#1C2D4A", "#93C5FD", "#2E5A8A"),
        "Meta_R":    ("#1C2D4A", "#93C5FD", "#2E5A8A"),
    }
    _CD = ("#1E3A5F", "#93C5FD", "#2A4D72")  # default chip

    def _chip(self, parent: tk.Frame, key: str) -> None:
        label = self._KL.get(key, key if len(key) > 1 else key.upper())
        bg, fg, bdr = self._CS.get(key, self._CD)
        outer = tk.Frame(parent, bg=bdr)
        outer.pack()
        inner = tk.Frame(outer, bg=bg)
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=f"[{label}]", font=(MF, 11),
                 bg=bg, fg=fg, padx=8, pady=3).pack()

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
        self._bs.config(state=tk.DISABLED if active else tk.NORMAL)
        self._bx.config(state=tk.NORMAL   if active else tk.DISABLED)

    def _set_badge(self, active: bool) -> None:
        if active:
            tk.Frame.configure(self._badge_f, bg="#0E8F64")
            self._badge_i.config(bg="#083D2E")
            self._dot.config(fg="#34D399",       bg="#083D2E")
            self._badge_t.config(text="Logging Active",
                                 fg="#34D399",   bg="#083D2E")
        else:
            tk.Frame.configure(self._badge_f, bg="#334155")
            self._badge_i.config(bg="#1E293B")
            self._dot.config(fg="#64748B",       bg="#1E293B")
            self._badge_t.config(text="Logging Inactive",
                                 fg="#64748B",   bg="#1E293B")

    def _tick(self) -> None:
        if not self.logger.is_active:
            return
        self._tv.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
