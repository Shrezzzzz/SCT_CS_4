"""
ui.py — KeyTrace
1366 × 768, non-resizable, pure Tkinter + stdlib.
Every UI element uses rounded corners via Canvas where native Tkinter
does not support border-radius.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Tuple

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#E9EEF5"
NAVBAR  = "#27344A"
WHITE   = "#FFFFFF"
BLUE    = "#2563EB"
GREEN   = "#16A34A"
RED     = "#EF4444"
TXT1    = "#1F2937"
TXT2    = "#64748B"

RP      = "#162845"          # right panel bg
RP_ROW1 = "#162845"
RP_ROW2 = "#1B304E"
RCOL_BG = "#0E1B2F"
RCOL_FG = "#8FA4C0"
RDIV    = "#29415F"

KD_BG, KD_FG = "#1E4EA8", "#BFD8FF"   # KeyDown  — blue
KR_BG, KR_FG = "#374151", "#D1D5DB"   # KeyRelease — grey
BS_BG, BS_FG = "#78350F", "#FDE68A"   # Backspace — amber

SF = "Segoe UI"
MF = "Consolas"
PH = "Filter keystrokes..."


# ── Canvas rounded-rectangle primitives ──────────────────────────────────────

def _rrect_pts(x1, y1, x2, y2, r):
    """Return smooth polygon point list for a rounded rect."""
    return [
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
    ]


def _rrect(cv: tk.Canvas, x1, y1, x2, y2, r,
           fill="", outline="", width=0, tags=()):
    return cv.create_polygon(
        _rrect_pts(x1, y1, x2, y2, r),
        smooth=True, fill=fill, outline=outline, width=width, tags=tags)


class RoundPanel(tk.Frame):
    """
    A Frame whose background is a filled rounded rectangle drawn on a Canvas.
    Place children inside  self.inner  (a plain tk.Frame).
    """
    def __init__(self, master, bg_color: str, radius: int = 18,
                 border_color: str = "", border_width: int = 1, **kw):
        parent_bg = master.cget("bg") if hasattr(master, "cget") else BG
        super().__init__(master, bg=parent_bg, **kw)
        self._bg  = bg_color
        self._r   = radius
        self._bc  = border_color
        self._bw  = border_width

        self._cv = tk.Canvas(self, bg=parent_bg, bd=0, highlightthickness=0)
        self._cv.pack(fill=tk.BOTH, expand=True)

        self.inner = tk.Frame(self._cv, bg=bg_color)
        self._win  = self._cv.create_window(0, 0, window=self.inner, anchor="nw")
        self._cv.bind("<Configure>", self._redraw)

    def _redraw(self, _=None):
        w = self._cv.winfo_width()
        h = self._cv.winfo_height()
        if w < 4 or h < 4:
            return
        self._cv.delete("bg")
        bw = self._bw
        if self._bc:
            _rrect(self._cv, 0, 0, w, h, self._r,
                   fill=self._bc, outline=self._bc, tags="bg")
            _rrect(self._cv, bw, bw, w-bw, h-bw, max(1, self._r-bw),
                   fill=self._bg, outline=self._bg, tags="bg")
        else:
            _rrect(self._cv, 0, 0, w, h, self._r,
                   fill=self._bg, outline=self._bg, tags="bg")
        self._cv.tag_lower("bg")
        self._cv.itemconfig(self._win, width=w, height=h)
        self._cv.coords(self._win, 0, 0)


class RoundLabel(tk.Canvas):
    """
    A Canvas that draws a rounded-rectangle background and a centered text label.
    Used for event badges and key chips where tk.Label gives sharp corners.
    Supports live color updates via  .update_colors(bg, fg).
    """
    def __init__(self, master, text: str, font, bg: str, fg: str,
                 radius: int = 6, padx: int = 10, pady: int = 4, **kw):
        # Measure text size
        tmp = tk.Label(master, text=text, font=font)
        tmp.update_idletasks()
        tw = tmp.winfo_reqwidth()
        th = tmp.winfo_reqheight()
        tmp.destroy()

        cw = tw + padx * 2
        ch = th + pady * 2

        super().__init__(master, width=cw, height=ch,
                         bd=0, highlightthickness=0, **kw)
        self._bg = bg
        self._fg = fg
        self._r  = radius
        self._text = text
        self._font = font
        self._cw = cw
        self._ch = ch
        self._rect_id = None
        self._text_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        self.configure(bg=self._bg)
        _rrect(self, 0, 0, self._cw, self._ch, self._r,
               fill=self._bg, outline=self._bg)
        self._text_id = self.create_text(
            self._cw // 2, self._ch // 2,
            text=self._text, font=self._font,
            fill=self._fg, anchor="center")

    def update_colors(self, bg: str, fg: str):
        self._bg = bg
        self._fg = fg
        self._draw()


class RoundButton(tk.Frame):
    """
    Cross-platform button with a rounded background (Canvas-drawn).
    Supports  .config(state=tk.DISABLED/tk.NORMAL).
    """
    def __init__(self, master, text: str, bg: str, fg: str,
                 hover_bg: str, cmd, radius: int = 10,
                 padx: int = 18, pady: int = 9,
                 outline_color: str = "",
                 disabled_bg: str = "#8895A7",
                 disabled_fg: str = WHITE,
                 parent_bg: str = BG, **kw):
        super().__init__(master, bg=parent_bg, **kw)
        self._bg   = bg
        self._fg   = fg
        self._hov  = hover_bg
        self._cmd  = cmd
        self._r    = radius
        self._dis_bg = disabled_bg
        self._dis_fg = disabled_fg
        self._ol   = outline_color
        self._off  = False

        tmp = tk.Label(self, text=text, font=(SF, 12, "bold"))
        tmp.update_idletasks()
        tw = tmp.winfo_reqwidth()
        th = tmp.winfo_reqheight()
        tmp.destroy()

        cw = tw + padx * 2
        ch = th + pady * 2

        self._cv = tk.Canvas(self, bg=parent_bg, width=cw, height=ch,
                             bd=0, highlightthickness=0)
        self._cv.pack()

        self._rid = None
        self._tid = None
        self._text = text
        self._cw = cw
        self._ch = ch
        self._draw(bg, fg)

        self._cv.bind("<Button-1>", self._click)
        self._cv.bind("<Enter>",    self._enter)
        self._cv.bind("<Leave>",    self._leave)

    def _draw(self, bg: str, fg: str):
        self._cv.delete("all")
        self._cv.configure(bg=self.cget("bg"))
        if self._ol:
            _rrect(self._cv, 0, 0, self._cw, self._ch, self._r,
                   fill=self._ol, outline=self._ol)
            _rrect(self._cv, 1, 1, self._cw-1, self._ch-1, max(1, self._r-1),
                   fill=bg, outline=bg)
        else:
            _rrect(self._cv, 0, 0, self._cw, self._ch, self._r,
                   fill=bg, outline=bg)
        self._cv.create_text(self._cw//2, self._ch//2,
                             text=self._text, font=(SF, 12, "bold"),
                             fill=fg, anchor="center")

    def _click(self, _):
        if not self._off:
            self._cmd()

    def _enter(self, _):
        if not self._off:
            self._draw(self._hov, self._fg if not self._ol else self._ol)

    def _leave(self, _):
        if not self._off:
            self._draw(self._bg, self._fg)

    def config(self, state=None, **kw):
        st = state if state is not None else kw.get("state")
        if st == tk.DISABLED:
            self._off = True
            self._draw(self._dis_bg, self._dis_fg)
        elif st in (tk.NORMAL, "normal"):
            self._off = False
            self._draw(self._bg, self._fg)


# ─────────────────────────────────────────────────────────────────────────────

class KeyTraceApp(tk.Tk):

    W, H = 1366, 768

    def __init__(self) -> None:
        super().__init__()
        self.logger    = KeystrokeLogger()
        self._rows: List[dict] = []
        self._timer_id = None
        self._flt_on   = False

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
    #  NAVBAR  (56 px dark bar — full-width, no radius needed at top)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_navbar(self) -> None:
        nav = tk.Frame(self, bg=NAVBAR, height=56)
        nav.pack(side=tk.TOP, fill=tk.X)
        nav.pack_propagate(False)

        lf = tk.Frame(nav, bg=NAVBAR)
        lf.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 0))

        # Traffic lights (canvas circles)
        tl = tk.Canvas(lf, bg=NAVBAR, width=64, height=56,
                       bd=0, highlightthickness=0)
        tl.pack(side=tk.LEFT)

        def _draw_tl():
            tl.delete("all")
            for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
                cx = 8 + i * 22
                tl.create_oval(cx-7, 21, cx+7, 35, fill=c, outline=c)
        self.after(20, _draw_tl)

        # Vertical separator
        tk.Frame(lf, bg="#3A4A5E", width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=(4, 14), pady=16)

        # Keyboard icon (canvas-drawn, cross-platform)
        kc = tk.Canvas(lf, bg=NAVBAR, width=22, height=22,
                       bd=0, highlightthickness=0)
        kc.pack(side=tk.LEFT, padx=(0, 7))

        def _draw_kb():
            kc.delete("all")
            kc.create_rectangle(1, 5, 21, 17, outline=WHITE, fill="", width=1.5)
            for row_y in (9, 13):
                for kx in range(4, 19, 4):
                    kc.create_rectangle(kx, row_y, kx+2, row_y+2,
                                        fill=WHITE, outline="")
            kc.create_rectangle(6, 15, 16, 17, fill=WHITE, outline="")
        self.after(20, _draw_kb)

        tk.Label(lf, text="KeyTrace", font=(SF, 15, "bold"),
                 bg=NAVBAR, fg=WHITE).pack(side=tk.LEFT)

        # ── Status badge — rounded pill via Canvas ────────────────────────
        rf = tk.Frame(nav, bg=NAVBAR)
        rf.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 18))

        # We use a Canvas to draw the pill shape (rounded badge)
        self._badge_cv = tk.Canvas(rf, bg=NAVBAR, bd=0, highlightthickness=0)
        self._badge_cv.pack(side=tk.RIGHT, pady=14)
        self._badge_state = False
        self._badge_dot_txt = "●  "
        self._badge_lbl_txt = "Logging Inactive"
        self._badge_font    = (SF, 10, "bold")
        self._badge_cv.bind("<Configure>", lambda e: self._draw_badge())
        self.after(30, self._draw_badge)

        tk.Frame(self, bg="#1E2B3D", height=1).pack(side=tk.TOP, fill=tk.X)

    def _draw_badge(self):
        cv = self._badge_cv
        active = self._badge_state
        pill_bg  = "#083D2E" if active else "#1E293B"
        pill_bdr = "#0E8F64" if active else "#334155"
        fg_color = "#34D399" if active else "#64748B"
        text = ("● " + ("Logging Active" if active else "Logging Inactive"))

        # Measure text
        tmp = tk.Label(cv, text=text, font=self._badge_font)
        tmp.update_idletasks()
        tw = tmp.winfo_reqwidth()
        th = tmp.winfo_reqheight()
        tmp.destroy()

        pw = tw + 28
        ph = th + 12
        cv.configure(width=pw, height=ph)
        cv.delete("all")
        _rrect(cv, 0, 0, pw, ph, ph//2, fill=pill_bdr, outline=pill_bdr)
        _rrect(cv, 1, 1, pw-1, ph-1, ph//2-1, fill=pill_bg, outline=pill_bg)
        cv.create_text(pw//2, ph//2, text=text,
                       font=self._badge_font, fill=fg_color, anchor="center")

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
    #  LEFT PANEL  — rounded white card (radius 18)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_left(self, body: tk.Frame) -> None:
        panel = RoundPanel(body, bg_color=WHITE, radius=18,
                           border_color="#E0E6F0", border_width=1)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 12))

        card = panel.inner
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1, minsize=160)

        # ── Header ────────────────────────────────────
        hrow = tk.Frame(card, bg=WHITE)
        hrow.grid(row=0, column=0, sticky="ew", padx=26, pady=(24, 0))

        ico = tk.Frame(hrow, bg=WHITE)
        ico.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 10), pady=(3, 0))
        tk.Label(ico, text="≡", font=(SF, 11, "bold"),
                 bg=WHITE, fg="#3B5BFD").pack(anchor=tk.W)
        tk.Label(ico, text="✎", font=(SF, 10),
                 bg=WHITE, fg="#3B5BFD").pack(anchor=tk.W)

        txt_c = tk.Frame(hrow, bg=WHITE)
        txt_c.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(txt_c, text="Typing Area",
                 font=(SF, 20, "bold"), bg=WHITE, fg="#1B2130").pack(anchor=tk.W)
        tk.Label(txt_c,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=(SF, 12), bg=WHITE, fg="#8991A3",
                 wraplength=300, justify=tk.LEFT).pack(anchor=tk.W, pady=(3, 0))

        # Divider
        tk.Frame(card, bg="#ECECF0", height=1).grid(
            row=1, column=0, sticky="ew", padx=26, pady=(16, 0))

        # ── Stat cards ─────────────────────────────────
        sr = tk.Frame(card, bg=WHITE)
        sr.grid(row=2, column=0, sticky="ew", padx=26, pady=(14, 0))
        sr.columnconfigure(0, weight=1, uniform="s")
        sr.columnconfigure(1, weight=1, uniform="s")

        self._cvar = tk.StringVar(value="0")
        self._wvar = tk.StringVar(value="0")
        self._stat(sr, "CHARACTERS", self._cvar, "#3B5BFD", 0)
        self._stat(sr, "WORDS",      self._wvar, "#1B2130", 1)

        # ── Typing area — rounded border via RoundPanel ─
        ta_panel = RoundPanel(card, bg_color="#F9FAFC", radius=12,
                              border_color="#E4E7EE", border_width=1)
        ta_panel.grid(row=3, column=0, sticky="nsew", padx=26, pady=(14, 0))

        self._ta = tk.Text(
            ta_panel.inner, font=(SF, 14), bg="#F9FAFC", fg="#1B2130",
            insertbackground="#3B5BFD",
            relief=tk.FLAT, bd=14,
            wrap=tk.WORD, undo=True,
            selectbackground="#3B5BFD", selectforeground=WHITE,
            highlightthickness=0, spacing1=3, spacing3=3,
        )
        self._ta.pack(fill=tk.BOTH, expand=True)
        self._ta.bind("<Key>",        self._on_kp)
        self._ta.bind("<KeyRelease>", self._on_kr)
        self._ta.bind("<<Modified>>", self._on_mod)
        self._ta.bind("<FocusIn>",
            lambda e: ta_panel._cv.configure(
                highlightbackground="#B9C3F7", highlightthickness=0) or
            ta_panel.inner.configure(bg=WHITE) or
            self._ta.configure(bg=WHITE))
        self._ta.bind("<FocusOut>",
            lambda e: ta_panel.inner.configure(bg="#F9FAFC") or
            self._ta.configure(bg="#F9FAFC"))

        # ── Notice — rounded blue-tinted card ──────────
        notice_panel = RoundPanel(card, bg_color="#EEF1FD", radius=12,
                                  border_color="#D6E4FF", border_width=1)
        notice_panel.grid(row=4, column=0, sticky="ew", padx=26, pady=(14, 24))

        ni = tk.Frame(notice_panel.inner, bg="#EEF1FD")
        ni.pack(fill=tk.X, padx=14, pady=12)

        sh = tk.Canvas(ni, bg="#EEF1FD", width=18, height=18,
                       bd=0, highlightthickness=0)
        sh.pack(side=tk.LEFT, padx=(0, 10), pady=1)
        sh.create_polygon(9,1, 17,4, 17,10, 9,17, 1,10, 1,4,
                          smooth=False, outline="#3B5BFD", fill="", width=1.5)
        sh.create_line(5,9, 8,12, 13,6, smooth=False, fill="#3B5BFD",
                       width=1.5, capstyle=tk.ROUND, joinstyle=tk.ROUND)

        tk.Label(ni,
                 text="Educational Sandbox  •  Keys logged only within this application window",
                 font=(SF, 11), bg="#EEF1FD", fg="#5B6478",
                 wraplength=300, justify=tk.LEFT).pack(side=tk.LEFT, anchor=tk.W)

    def _stat(self, parent, label, var, vfg, col):
        pad = (0, 12) if col == 0 else (0, 0)
        # Rounded stat card via RoundPanel (radius 12)
        rp = RoundPanel(parent, bg_color="#F4F6FA", radius=12,
                        border_color="#E4E7EE", border_width=1)
        rp.grid(row=0, column=col, sticky="nsew", padx=pad)

        inner = tk.Frame(rp.inner, bg="#F4F6FA", height=92)
        inner.pack(fill=tk.BOTH, expand=True)
        inner.pack_propagate(False)

        top = tk.Frame(inner, bg="#F4F6FA")
        top.pack(fill=tk.X, padx=16, pady=(14, 0))
        tk.Label(top, text=label, font=(SF, 10, "bold"),
                 bg="#F4F6FA", fg="#8991A3").pack(side=tk.LEFT)

        if col == 0:
            ic = tk.Canvas(top, bg="#F4F6FA", width=22, height=16,
                           bd=0, highlightthickness=0)
            ic.pack(side=tk.RIGHT)
            ic.create_rectangle(1, 1, 21, 15, outline="#C0C8D4", width=1)
            ic.create_text(11, 8, text="123", font=(SF, 6),
                           fill="#C0C8D4", anchor="center")
        else:
            ic = tk.Canvas(top, bg="#F4F6FA", width=16, height=14,
                           bd=0, highlightthickness=0)
            ic.pack(side=tk.RIGHT)
            for y, w2 in ((2, 16), (7, 16), (12, 10)):
                ic.create_line(0, y, w2, y, fill="#C0C8D4", width=1.5)

        tk.Label(inner, textvariable=var, font=(SF, 30, "bold"),
                 bg="#F4F6FA", fg=vfg).pack(anchor=tk.W, padx=16, pady=(4, 0))

    # ─────────────────────────────────────────────────────────────────────────
    #  RIGHT PANEL  — rounded dark card (radius 18)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_right(self, body: tk.Frame) -> None:
        panel = RoundPanel(body, bg_color=RP, radius=18,
                           border_color="#0D1A2E", border_width=1)
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 12))

        card = panel.inner
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        # ── Header 88px ───────────────────────────────
        hdr = tk.Frame(card, bg=RP, height=88)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.pack_propagate(False)
        hdr.columnconfigure(0, weight=1)
        hdr.columnconfigure(1, weight=0)

        lh = tk.Frame(hdr, bg=RP)
        lh.grid(row=0, column=0, sticky="w", padx=(20, 10), pady=(18, 0))

        tr = tk.Frame(lh, bg=RP)
        tr.pack(anchor=tk.W)

        ib = tk.Frame(tr, bg="#0D5C3A", width=28, height=28)
        ib.pack(side=tk.LEFT, padx=(0, 10))
        ib.pack_propagate(False)
        tk.Label(ib, text=">_", font=(MF, 10, "bold"),
                 bg="#0D5C3A", fg="#34D399").place(relx=0.5, rely=0.5,
                                                   anchor="center")

        tk.Label(tr, text="Keystroke Log", font=(SF, 16, "bold"),
                 bg=RP, fg=WHITE).pack(side=tk.LEFT)
        tk.Label(lh,
                 text="Chronological event stream with instant keycap resolution.",
                 font=(SF, 11), bg=RP, fg="#6B87A8"
                 ).pack(anchor=tk.W, pady=(4, 0))

        # Search box — rounded via RoundPanel (radius 10)
        rh = tk.Frame(hdr, bg=RP)
        rh.grid(row=0, column=1, sticky="e", padx=(0, 20))

        srp = RoundPanel(rh, bg_color="#102038", radius=10,
                         border_color="#35527A", border_width=1)
        srp.pack(pady=23)   # vertically centered in 88px header

        sb_inner = tk.Frame(srp.inner, bg="#102038", width=218, height=40)
        sb_inner.pack(padx=1, pady=1)
        sb_inner.pack_propagate(False)

        tk.Label(sb_inner, text="🔍", font=(SF, 10),
                 bg="#102038", fg="#4A6A8A").pack(side=tk.LEFT, padx=(10, 3))

        self._fvar = tk.StringVar()
        self._fe = tk.Entry(sb_inner, textvariable=self._fvar,
                            font=(SF, 11), bg="#102038", fg="#7E97BA",
                            insertbackground="#8899BB",
                            relief=tk.FLAT, bd=0, highlightthickness=0)
        self._fe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._fe.insert(0, PH)
        self._fe.bind("<FocusIn>",  self._fi)
        self._fe.bind("<FocusOut>", self._fo)
        self._fvar.trace_add("write", self._fc)

        # Divider
        tk.Frame(card, bg=RDIV, height=1).grid(row=1, column=0, sticky="ew")

        # Column headers — rounded top corners via Canvas
        ch_cv = tk.Canvas(card, bg=RP, height=44, bd=0, highlightthickness=0)
        ch_cv.grid(row=2, column=0, sticky="ew")

        def _draw_ch():
            w = ch_cv.winfo_width()
            if w < 4:
                return
            ch_cv.delete("all")
            ch_cv.create_rectangle(0, 0, w, 44, fill=RCOL_BG, outline=RCOL_BG)
            cols = [
                (0.34, "TIMESTAMP",    "w", 22),
                (0.28, "EVENT",        "w",  8),
                (0.38, "CAPTURED KEY", "e", 22),
            ]
            x = 0
            for frac, txt, anc, px in cols:
                cw2 = int(w * frac)
                anchor = tk.W if anc == "w" else tk.E
                ax = x + (px if anc == "w" else cw2 - px)
                ch_cv.create_text(ax, 22, text=txt, font=(SF, 9, "bold"),
                                  fill=RCOL_FG, anchor=anchor)
                x += cw2

        ch_cv.bind("<Configure>", lambda e: _draw_ch())
        self.after(30, _draw_ch)

        # Scrollable log
        lf = tk.Frame(card, bg=RP)
        lf.grid(row=3, column=0, sticky="nsew")
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)

        vsb = tk.Scrollbar(lf, orient=tk.VERTICAL, width=5)
        vsb.grid(row=0, column=1, sticky="ns")

        self._cv_log = tk.Canvas(lf, bg=RP, bd=0,
                                 highlightthickness=0,
                                 yscrollcommand=vsb.set)
        self._cv_log.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._cv_log.yview)

        self._lf = tk.Frame(self._cv_log, bg=RP)
        self._cw = self._cv_log.create_window(
            (0, 0), window=self._lf, anchor="nw")

        self._lf.bind("<Configure>",
            lambda e: self._cv_log.configure(
                scrollregion=self._cv_log.bbox("all")))
        self._cv_log.bind("<Configure>",
            lambda e: self._cv_log.itemconfig(self._cw, width=e.width))

        for w in (self._cv_log, self._lf):
            w.bind("<MouseWheel>", self._scroll)
            w.bind("<Button-4>",   self._scroll)
            w.bind("<Button-5>",   self._scroll)

    # ─────────────────────────────────────────────────────────────────────────
    #  ACTION BAR  — rounded buttons + rounded session card
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

        # Rounded buttons (radius 10)
        self._bs = RoundButton(bl, "▶  Start Logging",
                               bg="#2563EB", fg=WHITE, hover_bg="#1D4ED8",
                               cmd=self._start, radius=10, padx=18, pady=9,
                               parent_bg="#F4F7FA")
        self._bs.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        self._bx = RoundButton(bl, "⏸  Stop Logging",
                               bg="#4B5563", fg=WHITE, hover_bg="#374151",
                               cmd=self._stop, radius=10, padx=18, pady=9,
                               disabled_bg="#8895A7", disabled_fg=WHITE,
                               parent_bg="#F4F7FA")
        self._bx.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        self._bv = RoundButton(bl, "⬇  Save Log (.txt)",
                               bg="#16A34A", fg=WHITE, hover_bg="#15803D",
                               cmd=self._save, radius=10, padx=18, pady=9,
                               parent_bg="#F4F7FA")
        self._bv.pack(side=tk.LEFT, padx=(0, 10), pady=12)

        self._bc = RoundButton(bl, "🗑  Clear",
                               bg=WHITE, fg=RED, hover_bg="#FEF2F2",
                               cmd=self._clear, radius=10, padx=18, pady=9,
                               outline_color=RED, parent_bg="#F4F7FA")
        self._bc.pack(side=tk.LEFT, pady=12)

        # Session card — rounded (radius 10)
        sc_panel = RoundPanel(row, bg_color=WHITE, radius=10,
                              border_color="#D1D9E6", border_width=1)
        sc_panel.pack(side=tk.RIGHT, pady=12)

        sci = sc_panel.inner

        ls = tk.Frame(sci, bg=WHITE)
        ls.pack(side=tk.LEFT, padx=(14, 12), pady=10)
        tk.Label(ls, text="⏱", font=(SF, 11), bg=WHITE, fg=TXT2
                 ).pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(ls, text="Session:", font=(SF, 11), bg=WHITE, fg=TXT2
                 ).pack(side=tk.LEFT, padx=(0, 5))
        self._tv = tk.StringVar(value="00m 00s")
        tk.Label(ls, textvariable=self._tv,
                 font=(SF, 11, "bold"), bg=WHITE, fg=TXT1).pack(side=tk.LEFT)

        tk.Frame(sci, bg="#D1D9E6", width=1).pack(
            side=tk.LEFT, fill=tk.Y, pady=10)

        rs = tk.Frame(sci, bg=WHITE)
        rs.pack(side=tk.LEFT, padx=(12, 14), pady=10)
        tk.Label(rs, text="Logged Keys:", font=(SF, 11), bg=WHITE, fg=TXT2
                 ).pack(side=tk.LEFT, padx=(0, 5))
        self._kv = tk.StringVar(value="0")
        tk.Label(rs, textvariable=self._kv,
                 font=(SF, 11, "bold"), bg=WHITE, fg=BLUE).pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────────────────
    #  FOOTER  (full-width dark strip — no radius needed)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self) -> None:
        bar = tk.Frame(self, bg="#27344A", height=40)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg="#27344A")
        inner.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        tk.Label(inner, text="🛡", font=(SF, 12),
                 bg="#27344A", fg="#34D399").pack(side=tk.LEFT, padx=(0, 8), pady=10)
        tk.Label(inner,
                 text="Offline Educational Keylogger  •  Data stored locally only",
                 font=(SF, 11), bg="#27344A", fg="#94A3B8").pack(side=tk.LEFT)

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

        # Left accent on newest row
        tk.Frame(f, bg="#3B82F6" if newest else bg, width=3
                 ).pack(side=tk.LEFT, fill=tk.Y)

        # Timestamp
        tk.Label(f, text=r["ts"], font=(MF, 12),
                 bg=bg, fg="#7A9EC8", anchor=tk.W, padx=16
                 ).pack(side=tk.LEFT, fill=tk.Y)

        # Key chip RIGHT (pack before badge)
        cf = tk.Frame(f, bg=bg)
        cf.pack(side=tk.RIGHT, padx=(0, 18), pady=10)
        self._chip(cf, r["key"])

        # Event badge
        bf = tk.Frame(f, bg=bg)
        bf.pack(side=tk.LEFT, pady=12)
        self._badge(bf, r["ev"], r["key"])

    def _badge(self, parent: tk.Frame, ev: str, key: str) -> None:
        """Rounded event badge using RoundLabel (radius 6)."""
        if key == "Backspace":
            bg, fg = BS_BG, BS_FG
        elif ev == "KeyDown":
            bg, fg = KD_BG, KD_FG
        else:
            bg, fg = KR_BG, KR_FG

        rl = RoundLabel(parent, text=ev, font=(SF, 10, "bold"),
                        bg=bg, fg=fg, radius=6,
                        padx=10, pady=4)
        rl.configure(bg=parent.cget("bg"))
        rl.pack()

    _KL = {
        "Enter": "Enter ↵",   "Space": "Space ␣",
        "Backspace": "Backspace ⌫", "Tab": "Tab ⇥",
        "Escape": "Esc",
        "Shift_L": "Shift_L ⇧", "Shift_R": "Shift_R ⇧",
        "Control_L": "Ctrl_L",  "Control_R": "Ctrl_R",
        "Alt_L": "Alt_L",       "Alt_R": "Alt_R",
        "CapsLock": "CapsLock ⇪", "Delete": "Del ⌦",
        "Up": "↑", "Down": "↓", "Left": "←", "Right": "→",
        "Meta_L": "Cmd_L ⌘",  "Meta_R": "Cmd_R ⌘",
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
    _CD = ("#1E3A5F", "#93C5FD", "#2A4D72")

    def _chip(self, parent: tk.Frame, key: str) -> None:
        """Rounded key chip using RoundLabel (radius 6)."""
        label = self._KL.get(key, key if len(key) > 1 else key.upper())
        bg, fg, bdr = self._CS.get(key, self._CD)
        # Outer border via 1px larger canvas
        rl = RoundLabel(parent, text=f"[{label}]",
                        font=(MF, 11),
                        bg=bg, fg=fg, radius=6,
                        padx=8, pady=3)
        rl.configure(bg=parent.cget("bg"))
        rl.pack()

    # ─────────────────────────────────────────────────────────────────────────
    #  SCROLL + FILTER
    # ─────────────────────────────────────────────────────────────────────────
    def _scroll(self, e: tk.Event) -> None:
        if   e.num == 4: self._cv_log.yview_scroll(-1, "units")
        elif e.num == 5: self._cv_log.yview_scroll( 1, "units")
        else: self._cv_log.yview_scroll(-1 if e.delta > 0 else 1, "units")

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
        self._badge_state = True
        self._draw_badge()
        self._ta.focus_set()
        self._tick()

    def _stop(self) -> None:
        self.logger.stop()
        self._refresh_btn_states()
        self._badge_state = False
        self._draw_badge()
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
        self._badge_state = False
        self._draw_badge()

    def _refresh_btn_states(self) -> None:
        active = self.logger.is_active
        self._bs.config(state=tk.DISABLED if active else tk.NORMAL)
        self._bx.config(state=tk.NORMAL   if active else tk.DISABLED)

    # Legacy _set_badge kept for compatibility — now delegates to canvas draw
    def _set_badge(self, active: bool) -> None:
        self._badge_state = active
        self._draw_badge()

    def _tick(self) -> None:
        if not self.logger.is_active:
            return
        self._tv.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
