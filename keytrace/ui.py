"""
ui.py — KeyTrace
Pixel-perfect recreation of the mockup.
Fixed 1468 × 920 window. All measurements taken directly from the spec.
Uses only tkinter + standard library — no third-party packages.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from logger import KeystrokeLogger, LogEntry
from utils import count_chars, count_words, format_elapsed, resolve_key_name

# ─────────────────────────────────────────────────────────────────────────────
#  EXACT COLOUR PALETTE  (from spec)
# ─────────────────────────────────────────────────────────────────────────────
P = {
    # Window / chrome
    "win":           "#DCE2EC",
    "navbar":        "#2D3647",
    "footer":        "#2D3647",

    # Panels
    "left_panel":    "#F8FAFD",
    "right_panel":   "#18263C",

    # Borders
    "panel_border":  "#C8D3E2",
    "card_border":   "#C9D5E6",
    "stat_border":   "#C9D5E6",
    "ta_border":     "#AFC3DD",
    "notice_border": "#C8D9F0",
    "action_top":    "#CAD4E3",
    "session_border":"#D1DAE7",
    "right_div":     "#314560",
    "tbl_hdr_bg":    "#0E1B31",
    "right_search_bg":"#102038",
    "right_search_br":"#35527A",

    # Typography
    "txt_dark":      "#1C2A44",
    "txt_gray":      "#61718D",
    "txt_white":     "#FFFFFF",
    "txt_light":     "#8EA4C7",
    "ts_color":      "#8EA4C7",
    "col_hdr_fg":    "#A9BCD8",

    # Buttons
    "btn_start":     "#2E64F0",
    "btn_start_h":   "#2456D8",
    "btn_stop":      "#5C6C84",
    "btn_stop_h":    "#4E5C71",
    "btn_save":      "#16A34A",
    "btn_save_h":    "#128C3E",
    "btn_clear_fg":  "#EF4444",
    "btn_clear_h":   "#DC2626",

    # Action bar
    "action_bar":    "#EEF2F7",

    # Badge (navbar)
    "badge_bg":      "#113D34",
    "badge_border":  "#1ED38A",
    "badge_fg":      "#38E38F",

    # Stat cards
    "char_val":      "#2C64F0",

    # Traffic lights
    "tl_red":        "#FF5F57",
    "tl_yellow":     "#FEBC2E",
    "tl_green":      "#28C840",

    # Notice card
    "notice_bg":     "#EEF4FB",

    # Event badges
    "kd_bg":         "#1E4EA8",
    "kd_fg":         "#BFD8FF",
    "kr_bg":         "#37475D",
    "kr_fg":         "#CED7E5",
    "bs_bg":         "#47320C",
    "bs_fg":         "#FFC857",
    "bs_border":     "#F59E0B",

    # Key chip defaults
    "chip_bg":       "#1E3050",
    "chip_fg":       "#BFD8FF",
    "chip_border":   "#2E4A6E",

    # Accent line on newest row
    "accent_line":   "#3B82F6",
}

SF = "Segoe UI"      # primary font family
MF = "Consolas"      # monospace


# ─────────────────────────────────────────────────────────────────────────────
#  ROUNDED FRAME  (Canvas-based so we get real border-radius)
# ─────────────────────────────────────────────────────────────────────────────

class RoundFrame(tk.Canvas):
    """
    A Canvas that draws a filled rounded rectangle as its background,
    then hosts child widgets inside an embedded Frame window.
    Exposes `.inner` as the frame to place children in.
    """

    def __init__(self, master, radius=18, bg_color="#ffffff",
                 border_color=None, border_width=0, **kwargs):
        # Canvas itself should be transparent against the parent bg
        parent_bg = master.cget("bg") if hasattr(master, "cget") else P["win"]
        super().__init__(master, bg=parent_bg, bd=0,
                         highlightthickness=0, **kwargs)
        self._radius      = radius
        self._bg_color    = bg_color
        self._border_color = border_color
        self._border_width = border_width
        self._rect_id     = None
        self._border_id   = None

        self.inner = tk.Frame(self, bg=bg_color)
        self._win_id = self.create_window(0, 0, window=self.inner, anchor="nw")

        self.bind("<Configure>", self._redraw)

    def _redraw(self, _event=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2 or h < 2:
            return
        r = self._radius
        self.delete("rr")

        # Optional border
        if self._border_color and self._border_width:
            bw = self._border_width
            self._draw_rrect(bw/2, bw/2, w - bw/2, h - bw/2,
                             r, self._border_color, "rr", outline_only=True, width=bw)

        # Fill
        self._draw_rrect(0, 0, w, h, r, self._bg_color, "rr")

        # Keep the inner frame inset by the border width
        pad = self._border_width
        self.coords(self._win_id, pad, pad)
        self.itemconfig(self._win_id,
                        width=max(1, w - 2*pad),
                        height=max(1, h - 2*pad))

    def _draw_rrect(self, x1, y1, x2, y2, r, color, tag, outline_only=False, width=1):
        """Draw a filled (or outline-only) rounded rectangle."""
        pts = [
            x1+r, y1,
            x2-r, y1,
            x2,   y1,
            x2,   y1+r,
            x2,   y2-r,
            x2,   y2,
            x2-r, y2,
            x1+r, y2,
            x1,   y2,
            x1,   y2-r,
            x1,   y1+r,
            x1,   y1,
        ]
        if outline_only:
            self.create_polygon(pts, smooth=True, fill="",
                                outline=color, width=width, tags=tag)
        else:
            self.create_polygon(pts, smooth=True, fill=color,
                                outline=color, width=1, tags=tag)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class KeyTraceApp(tk.Tk):

    WIN_W = 1468
    WIN_H = 920

    def __init__(self) -> None:
        super().__init__()
        self.logger = KeystrokeLogger()
        self._rows:      List[dict] = []
        self._timer_id:  str | None = None
        self._flt_focus: bool       = False
        self._PLACEHOLDER = "Filter keystrokes..."

        self._setup_window()
        self._build()
        self._set_btn_states()

    # ── window ───────────────────────────────────────────────────────────────
    def _setup_window(self) -> None:
        self.title("KeyTrace")
        self.configure(bg=P["win"])
        self.resizable(False, False)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.WIN_W) // 2
        y  = (sh - self.WIN_H) // 2
        self.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+{y}")

    # ── scaffold ─────────────────────────────────────────────────────────────
    def _build(self) -> None:
        self._build_footer()    # pack BOTTOM first
        self._build_action_bar()
        self._build_navbar()    # pack TOP
        self._build_body()

    # ─────────────────────────────────────────────────────────────────────────
    #  NAVBAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_navbar(self) -> None:
        nav = tk.Frame(self, bg=P["navbar"], height=72)
        nav.pack(side=tk.TOP, fill=tk.X)
        nav.pack_propagate(False)

        # Left section
        lf = tk.Frame(nav, bg=P["navbar"])
        lf.pack(side=tk.LEFT, padx=24, fill=tk.Y)

        # Traffic lights
        tl = tk.Frame(lf, bg=P["navbar"])
        tl.pack(side=tk.LEFT, padx=(0, 16), fill=tk.Y, pady=26)
        for color in (P["tl_red"], P["tl_yellow"], P["tl_green"]):
            tk.Label(tl, bg=color, width=2, height=1,
                     relief=tk.FLAT).pack(side=tk.LEFT, padx=3)
            # use canvas circles for perfect circles
        # redo as canvas for exact circles
        tl.destroy()
        tl_c = tk.Canvas(lf, bg=P["navbar"], width=62, height=16,
                         bd=0, highlightthickness=0)
        tl_c.pack(side=tk.LEFT, padx=(0, 16), pady=28)
        for i, col in enumerate((P["tl_red"], P["tl_yellow"], P["tl_green"])):
            cx = 8 + i * 22
            tl_c.create_oval(cx-7, 1, cx+7, 15, fill=col, outline=col)

        # Keyboard icon + title
        tk.Label(lf, text="⌨", font=(SF, 16),
                 bg=P["navbar"], fg="#AABBCC").pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(lf, text="KeyTrace", font=(SF, 20, "bold"),
                 bg=P["navbar"], fg=P["txt_white"]).pack(side=tk.LEFT)

        # Right section — Logging Active badge
        rf = tk.Frame(nav, bg=P["navbar"])
        rf.pack(side=tk.RIGHT, padx=24, fill=tk.Y)

        self._badge_outer = tk.Frame(
            rf, bg=P["badge_border"],   # border via outer frame
        )
        self._badge_outer.pack(side=tk.RIGHT, pady=20)

        self._badge_inner = tk.Frame(self._badge_outer, bg=P["badge_bg"])
        self._badge_inner.pack(padx=1, pady=1)

        self._badge_dot = tk.Label(
            self._badge_inner, text="●", font=(SF, 10),
            bg=P["badge_bg"], fg=P["badge_fg"])
        self._badge_dot.pack(side=tk.LEFT, padx=(18, 4), pady=8)

        self._badge_lbl = tk.Label(
            self._badge_inner, text="Logging Inactive",
            font=(SF, 15, "bold"), bg=P["badge_bg"], fg="#8BBFA8")
        self._badge_lbl.pack(side=tk.LEFT, padx=(0, 18), pady=8)

        # Bottom separator
        tk.Frame(self, bg="#232A38", height=1).pack(side=tk.TOP, fill=tk.X)

    # ─────────────────────────────────────────────────────────────────────────
    #  BODY  (left + right panels)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_body(self) -> None:
        body = tk.Frame(self, bg=P["win"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                  padx=14, pady=(14, 0))

        # Left panel wrapper — 42% width
        self._left_wrap = tk.Frame(body, bg=P["win"])
        self._left_wrap.place(relx=0, rely=0, relwidth=0.415, relheight=1.0)

        # Right panel wrapper — 58% width
        self._right_wrap = tk.Frame(body, bg=P["win"])
        self._right_wrap.place(relx=0.429, rely=0, relwidth=0.571, relheight=1.0)

        self._build_left_panel()
        self._build_right_panel()

    # ─────────────────────────────────────────────────────────────────────────
    #  LEFT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_left_panel(self) -> None:
        p = self._left_wrap

        # Outer card with border
        card = tk.Frame(p, bg=P["panel_border"])
        card.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        inner = tk.Frame(card, bg=P["left_panel"])
        inner.place(x=1, y=1, relwidth=1.0, relheight=1.0,
                    width=-2, height=-2)

        # Give inner a grid layout
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(3, weight=1)   # text area expands

        # ── Title row ────────────────────────────────────────────────
        title_row = tk.Frame(inner, bg=P["left_panel"])
        title_row.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 0))

        icon_c = tk.Canvas(title_row, bg=P["left_panel"], width=28, height=28,
                           bd=0, highlightthickness=0)
        icon_c.pack(side=tk.LEFT, padx=(0, 8))
        icon_c.create_text(14, 14, text="✏", font=(SF, 14),
                           fill=P["btn_start"], anchor="center")

        tk.Label(title_row, text="Typing Area", font=(SF, 22, "bold"),
                 bg=P["left_panel"], fg=P["txt_dark"]).pack(side=tk.LEFT)

        tk.Label(inner,
                 text="Type into this sandbox to simulate & capture keystrokes in real time.",
                 font=(SF, 14), bg=P["left_panel"], fg=P["txt_gray"],
                 wraplength=380, justify=tk.LEFT
                 ).grid(row=1, column=0, sticky="w", padx=28, pady=(6, 0))

        # Divider
        tk.Frame(inner, bg="#D6DFEB", height=1).grid(
            row=2, column=0, sticky="ew", padx=28, pady=(16, 0))

        # ── Stat cards ───────────────────────────────────────────────
        stat_row = tk.Frame(inner, bg=P["left_panel"])
        stat_row.grid(row=3, column=0, sticky="ew", padx=28, pady=(16, 0))
        stat_row.columnconfigure(0, weight=1, uniform="sc")
        stat_row.columnconfigure(1, weight=1, uniform="sc")
        stat_row.columnconfigure(2, weight=1, uniform="sc")

        self._char_var = tk.StringVar(value="0")
        self._word_var = tk.StringVar(value="0")
        self._rate_var = tk.StringVar(value="—")

        self._make_stat(stat_row, "CHARACTERS", self._char_var,
                        val_color=P["char_val"], icon="⌨", col=0)
        self._make_stat(stat_row, "WORDS",      self._word_var,
                        val_color=P["txt_dark"], icon="≡",  col=1)
        self._make_stat(stat_row, "CAPTURE RATE", self._rate_var,
                        val_color=P["txt_gray"], icon="📊", col=2)

        # ── Typing text box ───────────────────────────────────────────
        ta_wrap = tk.Frame(inner, bg=P["ta_border"])
        ta_wrap.grid(row=4, column=0, sticky="ew", padx=28, pady=(16, 0))
        ta_wrap.columnconfigure(0, weight=1)

        self._ta = tk.Text(
            ta_wrap,
            height=11,               # ~260 px
            font=(SF, 16),
            bg="#FFFFFF",
            fg="#1E293B",
            insertbackground=P["btn_start"],
            relief=tk.FLAT, bd=18,
            wrap=tk.WORD, undo=True,
            selectbackground=P["btn_start"],
            selectforeground="#FFFFFF",
            highlightthickness=0,
        )
        self._ta.grid(row=0, column=0, sticky="ew")

        self._ta.bind("<Key>",        self._on_key_press)
        self._ta.bind("<KeyRelease>", self._on_key_release)
        self._ta.bind("<<Modified>>", self._on_modified)

        # ── Educational notice ────────────────────────────────────────
        notice = tk.Frame(inner, bg=P["notice_bg"],
                          highlightbackground=P["notice_border"],
                          highlightthickness=1)
        notice.grid(row=5, column=0, sticky="ew", padx=28, pady=(16, 24))

        nr = tk.Frame(notice, bg=P["notice_bg"])
        nr.pack(fill=tk.X, padx=16, pady=12)

        tk.Label(nr, text="🛡", font=(SF, 16), bg=P["notice_bg"],
                 fg=P["btn_start"]).pack(side=tk.LEFT, padx=(0, 10))

        nt = tk.Frame(nr, bg=P["notice_bg"])
        nt.pack(side=tk.LEFT)
        tk.Label(nt, text="Educational Sandbox", font=(SF, 13, "bold"),
                 bg=P["notice_bg"], fg=P["txt_dark"]).pack(anchor=tk.W)
        tk.Label(nt, text="Keys logged only within this application window",
                 font=(SF, 13), bg=P["notice_bg"], fg=P["txt_gray"]).pack(anchor=tk.W)

    def _make_stat(self, parent, label, var, val_color, icon, col):
        pad = (0, 8) if col < 2 else (0, 0)
        card = tk.Frame(parent, bg=P["card_border"],
                        highlightbackground=P["card_border"], highlightthickness=0)
        card.grid(row=0, column=col, sticky="nsew", padx=pad)

        inner = tk.Frame(card, bg="#FFFFFF", height=84)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner.pack_propagate(False)

        top = tk.Frame(inner, bg="#FFFFFF")
        top.pack(fill=tk.X, padx=14, pady=(10, 0))
        tk.Label(top, text=label, font=(SF, 12, "bold"),
                 bg="#FFFFFF", fg=P["txt_gray"]).pack(side=tk.LEFT)
        tk.Label(top, text=icon, font=(SF, 12),
                 bg="#FFFFFF", fg=P["txt_gray"]).pack(side=tk.RIGHT)

        tk.Label(inner, textvariable=var, font=(SF, 28, "bold"),
                 bg="#FFFFFF", fg=val_color).pack(anchor=tk.W, padx=14)

    # ─────────────────────────────────────────────────────────────────────────
    #  RIGHT PANEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_right_panel(self) -> None:
        p = self._right_wrap

        # outer border frame
        border = tk.Frame(p, bg=P["panel_border"])
        border.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        card = tk.Frame(border, bg=P["right_panel"])
        card.place(x=1, y=1, relwidth=1.0, relheight=1.0, width=-2, height=-2)

        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        # ── Header ───────────────────────────────────────────────────
        hdr = tk.Frame(card, bg=P["right_panel"])
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 0))
        hdr.columnconfigure(0, weight=1)

        # title + subtitle (left)
        lh = tk.Frame(hdr, bg=P["right_panel"])
        lh.grid(row=0, column=0, sticky="w")

        tr = tk.Frame(lh, bg=P["right_panel"])
        tr.pack(anchor=tk.W)
        tk.Label(tr, text="⌨", font=(SF, 16),
                 bg=P["right_panel"], fg="#4A7FA5").pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(tr, text="Keystroke Log", font=(SF, 22, "bold"),
                 bg=P["right_panel"], fg=P["txt_white"]).pack(side=tk.LEFT)

        tk.Label(lh,
                 text="Chronological event stream with instant keycap resolution.",
                 font=(SF, 14), bg=P["right_panel"], fg=P["txt_light"]
                 ).pack(anchor=tk.W, pady=(4, 0))

        # search box (right)
        fbox = tk.Frame(hdr, bg=P["right_search_br"])
        fbox.grid(row=0, column=1, sticky="e")

        finner = tk.Frame(fbox, bg=P["right_search_bg"])
        finner.pack(padx=1, pady=1)

        tk.Label(finner, text="🔍", font=(SF, 11),
                 bg=P["right_search_bg"], fg="#5A7499").pack(side=tk.LEFT, padx=(10, 4), pady=10)

        self._fvar = tk.StringVar()
        self._fentry = tk.Entry(
            finner, textvariable=self._fvar,
            font=(MF, 12), bg=P["right_search_bg"], fg=P["right_search_br"],
            insertbackground="#8899BB", relief=tk.FLAT, bd=0, width=18,
        )
        self._fentry.pack(side=tk.LEFT, padx=(0, 12), pady=10)
        self._fentry.insert(0, self._PLACEHOLDER)
        self._fentry.config(fg="#7E97BA")
        self._fentry.bind("<FocusIn>",  self._flt_in)
        self._fentry.bind("<FocusOut>", self._flt_out)
        self._fvar.trace_add("write", self._flt_changed)

        # ── Divider ───────────────────────────────────────────────────
        tk.Frame(card, bg=P["right_div"], height=1).grid(
            row=1, column=0, sticky="ew", padx=0, pady=(20, 0))

        # ── Column headers ────────────────────────────────────────────
        ch = tk.Frame(card, bg=P["tbl_hdr_bg"], height=44)
        ch.grid(row=2, column=0, sticky="ew")
        ch.pack_propagate(False)
        ch.columnconfigure(0, weight=34, uniform="col")
        ch.columnconfigure(1, weight=28, uniform="col")
        ch.columnconfigure(2, weight=38, uniform="col")

        for col_idx, text in enumerate(("TIMESTAMP", "EVENT", "CAPTURED KEY")):
            anchor = tk.E if col_idx == 2 else tk.W
            pad_l  = 28 if col_idx == 0 else 0
            pad_r  = 28 if col_idx == 2 else 0
            tk.Label(ch, text=text, font=(SF, 13, "bold"),
                     bg=P["tbl_hdr_bg"], fg=P["col_hdr_fg"],
                     anchor=anchor, padx=pad_l + pad_r
                     ).grid(row=0, column=col_idx, sticky="nsew", ipady=12)

        # ── Scrollable rows ───────────────────────────────────────────
        log_wrap = tk.Frame(card, bg=P["right_panel"])
        log_wrap.grid(row=3, column=0, sticky="nsew")
        log_wrap.rowconfigure(0, weight=1)
        log_wrap.columnconfigure(0, weight=1)

        vsb = tk.Scrollbar(log_wrap, orient=tk.VERTICAL, width=6)
        vsb.grid(row=0, column=1, sticky="ns")

        self._log_cv = tk.Canvas(log_wrap, bg=P["right_panel"],
                                 bd=0, highlightthickness=0,
                                 yscrollcommand=vsb.set)
        self._log_cv.grid(row=0, column=0, sticky="nsew")
        vsb.config(command=self._log_cv.yview)

        self._log_inner = tk.Frame(self._log_cv, bg=P["right_panel"])
        self._log_cwin  = self._log_cv.create_window(
            (0, 0), window=self._log_inner, anchor="nw")

        self._log_inner.bind("<Configure>",
            lambda e: self._log_cv.configure(
                scrollregion=self._log_cv.bbox("all")))
        self._log_cv.bind("<Configure>",
            lambda e: self._log_cv.itemconfig(self._log_cwin, width=e.width))

        for w in (self._log_cv, self._log_inner):
            w.bind("<MouseWheel>", self._scroll)
            w.bind("<Button-4>",   self._scroll)
            w.bind("<Button-5>",   self._scroll)

    # ─────────────────────────────────────────────────────────────────────────
    #  ACTION BAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_action_bar(self) -> None:
        bar = tk.Frame(self, bg=P["action_bar"], height=88)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        # top border
        tk.Frame(bar, bg=P["action_top"], height=1).pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(bar, bg=P["action_bar"])
        inner.pack(fill=tk.BOTH, expand=True, padx=20)

        # Left buttons
        bl = tk.Frame(inner, bg=P["action_bar"])
        bl.pack(side=tk.LEFT, fill=tk.Y)

        self._btn_start = self._mk_btn(
            bl, "▶  Start Logging", P["btn_start"], P["btn_start_h"], self._cmd_start,
            w=180)
        self._btn_start.pack(side=tk.LEFT, padx=(0, 12), pady=21)

        self._btn_stop = self._mk_btn(
            bl, "⏹  Stop Logging", P["btn_stop"], P["btn_stop_h"], self._cmd_stop,
            w=180)
        self._btn_stop.pack(side=tk.LEFT, padx=(0, 12), pady=21)

        self._btn_save = self._mk_btn(
            bl, "⬇  Save Log (.txt)", P["btn_save"], P["btn_save_h"], self._cmd_save,
            w=200)
        self._btn_save.pack(side=tk.LEFT, padx=(0, 12), pady=21)

        self._btn_clear = self._mk_btn(
            bl, "🗑  Clear", "#FFFFFF", "#FEE2E2", self._cmd_clear,
            w=140, outline=True)
        self._btn_clear.pack(side=tk.LEFT, pady=21)

        # Right session card
        sc = tk.Frame(inner, bg="#FFFFFF",
                      highlightbackground=P["session_border"],
                      highlightthickness=1)
        sc.pack(side=tk.RIGHT, pady=21, ipadx=4)

        sc_inner = tk.Frame(sc, bg="#FFFFFF")
        sc_inner.pack(fill=tk.BOTH, expand=True, padx=18, pady=12)

        # Session time row
        sr = tk.Frame(sc_inner, bg="#FFFFFF")
        sr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(sr, text="⏱  Session:", font=(SF, 14),
                 bg="#FFFFFF", fg=P["txt_gray"]).pack(side=tk.LEFT, padx=(0, 8))
        self._tvar = tk.StringVar(value="00m 00s")
        tk.Label(sr, textvariable=self._tvar, font=(MF, 14, "bold"),
                 bg="#FFFFFF", fg=P["txt_dark"]).pack(side=tk.LEFT)

        # Separator
        tk.Frame(sc_inner, bg=P["session_border"], height=1).pack(fill=tk.X, pady=2)

        # Logged keys row
        kr = tk.Frame(sc_inner, bg="#FFFFFF")
        kr.pack(fill=tk.X, pady=(4, 0))
        tk.Label(kr, text="Logged Keys:", font=(SF, 14),
                 bg="#FFFFFF", fg=P["txt_gray"]).pack(side=tk.LEFT, padx=(0, 8))
        self._kvar = tk.StringVar(value="0")
        tk.Label(kr, textvariable=self._kvar, font=(MF, 14, "bold"),
                 bg="#FFFFFF", fg=P["btn_start"]).pack(side=tk.LEFT)

    def _mk_btn(self, parent, text, bg, hover, cmd, w=160, outline=False):
        common = dict(
            text=text, font=(SF, 16, "bold"),
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=cmd, width=w // 10,
        )
        if outline:
            b = tk.Button(parent, bg="#FFFFFF", fg=P["btn_clear_fg"],
                          activebackground="#FEE2E2",
                          activeforeground=P["btn_clear_h"],
                          highlightbackground=P["btn_clear_fg"],
                          highlightthickness=1, **common)
        else:
            b = tk.Button(parent, bg=bg, fg="#FFFFFF",
                          activebackground=hover,
                          activeforeground="#FFFFFF", **common)
        b.bind("<Enter>", lambda e, b=b, hv=hover, ol=outline: (
            b.config(bg="#FEE2E2" if ol else hv)))
        b.bind("<Leave>", lambda e, b=b, ob="#FFFFFF" if outline else bg, ol=outline: (
            b.config(bg=ob)))
        return b

    # ─────────────────────────────────────────────────────────────────────────
    #  FOOTER STATUS BAR
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self) -> None:
        bar = tk.Frame(self, bg=P["footer"], height=54)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        inner = tk.Frame(bar, bg=P["footer"])
        inner.pack(side=tk.LEFT, fill=tk.Y, padx=24)

        tk.Label(inner, text="🛡", font=(SF, 15),
                 bg=P["footer"], fg=P["badge_fg"]).pack(side=tk.LEFT, pady=15, padx=(0, 8))
        tk.Label(inner,
                 text="Offline Educational Keylogger  •  Data stored locally only",
                 font=(SF, 14), bg=P["footer"], fg="#B0BDD0").pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────────────────
    #  KEY CAPTURE
    # ─────────────────────────────────────────────────────────────────────────
    def _on_key_press(self, event: tk.Event) -> None:
        key   = resolve_key_name(event)
        entry = self.logger.record("KeyDown", key)
        if entry:
            self._push_row(entry)
            self._kvar.set(str(self.logger.entry_count))

    def _on_key_release(self, event: tk.Event) -> None:
        key   = resolve_key_name(event)
        entry = self.logger.record("KeyRelease", key)
        if entry:
            self._push_row(entry)
            self._kvar.set(str(self.logger.entry_count))

    def _on_modified(self, _e) -> None:
        self._ta.edit_modified(False)
        t = self._ta.get("1.0", tk.END)
        self._char_var.set(str(count_chars(t)))
        self._word_var.set(str(count_words(t)))

    # ─────────────────────────────────────────────────────────────────────────
    #  LOG ROWS
    # ─────────────────────────────────────────────────────────────────────────
    def _push_row(self, entry: LogEntry) -> None:
        self._rows.insert(0, {
            "ts":  entry.timestamp,
            "ev":  entry.event_type,
            "key": entry.key,
        })
        self._redraw_rows()

    def _redraw_rows(self) -> None:
        for w in self._log_inner.winfo_children():
            w.destroy()

        flt = ""
        if self._flt_focus:
            flt = self._fvar.get().strip().lower()

        rows = [r for r in self._rows
                if not flt
                or flt in r["ts"].lower()
                or flt in r["ev"].lower()
                or flt in r["key"].lower()]

        for i, row in enumerate(rows):
            self._draw_row(row, i, newest=(i == 0))

    def _draw_row(self, row: dict, idx: int, newest: bool = False) -> None:
        ROW_H = 52
        bg = P["right_panel"]   # transparent alternating effect via subtle color
        if idx % 2 == 1:
            bg = "#1B2E47"

        frame = tk.Frame(self._log_inner, bg=bg, height=ROW_H)
        frame.pack(fill=tk.X)
        frame.pack_propagate(False)
        frame.columnconfigure(0, weight=34, uniform="rc")
        frame.columnconfigure(1, weight=28, uniform="rc")
        frame.columnconfigure(2, weight=38, uniform="rc")

        # Left accent line (only newest row)
        ac_color = P["accent_line"] if newest else bg
        tk.Frame(frame, bg=ac_color, width=3).pack(side=tk.LEFT, fill=tk.Y)

        # Timestamp
        tk.Label(frame, text=row["ts"], font=(MF, 15),
                 bg=bg, fg=P["ts_color"],
                 anchor=tk.W, padx=24).pack(side=tk.LEFT, fill=tk.Y)

        # Event badge — centered in its column
        ev_frame = tk.Frame(frame, bg=bg)
        ev_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        self._event_badge(ev_frame, row["ev"], row["key"]).pack(
            side=tk.LEFT, pady=13)

        # Key chip — right-aligned
        key_frame = tk.Frame(frame, bg=bg)
        key_frame.pack(side=tk.RIGHT, padx=(0, 24), fill=tk.Y)
        self._key_chip(key_frame, row["key"]).pack(side=tk.RIGHT, pady=12)

        # Row separator
        tk.Frame(self._log_inner, bg=P["right_div"], height=1).pack(fill=tk.X)

    def _event_badge(self, parent, ev: str, key: str) -> tk.Frame:
        """Return a coloured pill label for KeyDown/KeyRelease."""
        # Special badge for Backspace
        if key == "Backspace":
            bg, fg = P["bs_bg"], P["bs_fg"]
            bdr = P["bs_border"]
        elif ev == "KeyDown":
            bg, fg = P["kd_bg"], P["kd_fg"]
            bdr = P["kd_bg"]
        else:
            bg, fg = P["kr_bg"], P["kr_fg"]
            bdr = P["kr_bg"]

        f = tk.Frame(parent, bg=bdr)
        i = tk.Frame(f, bg=bg)
        i.pack(padx=1, pady=1)
        tk.Label(i, text=ev, font=(SF, 12, "bold"),
                 bg=bg, fg=fg, padx=10, pady=3).pack()
        return f

    # Key chip display labels for special keys
    _KEY_LABEL = {
        "Enter":     "Enter ↵",
        "Space":     "Space ␣",
        "BackSpace": "Backspace ⌫",
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
        "Delete":    "Delete ⌦",
        "Up":        "↑",
        "Down":      "↓",
        "Left":      "←",
        "Right":     "→",
    }

    _CHIP_STYLE = {
        # key: (bg, fg, border)
        "Enter":    ("#1E4EA8", "#BFD8FF", "#3B82F6"),
        "Space":    ("#1B3A5C", "#8CB8E8", "#2E5F8A"),
        "Backspace":("#47320C", "#FFC857", "#F59E0B"),
        "Escape":   ("#5C1A1A", "#FCA5A5", "#EF4444"),
        "Tab":      ("#2E1F5C", "#C4B5FD", "#7C3AED"),
        "Shift_L":  ("#1E3A4A", "#93C5D0", "#2D7D9A"),
        "Shift_R":  ("#1E3A4A", "#93C5D0", "#2D7D9A"),
        "CapsLock": ("#1E3A4A", "#93C5D0", "#2D7D9A"),
    }

    def _key_chip(self, parent, key: str) -> tk.Frame:
        label = self._KEY_LABEL.get(key, key)
        if len(label) == 1:
            label = label.upper()
        display = f"[{label}]"

        style = self._CHIP_STYLE.get(key)
        if style:
            bg, fg, bdr = style
        else:
            bg, fg, bdr = P["chip_bg"], P["chip_fg"], P["chip_border"]

        f = tk.Frame(parent, bg=bdr)
        i = tk.Frame(f, bg=bg)
        i.pack(padx=1, pady=1)
        tk.Label(i, text=display, font=(MF, 13),
                 bg=bg, fg=fg, padx=8, pady=2).pack()
        return f

    # ─────────────────────────────────────────────────────────────────────────
    #  SCROLLING
    # ─────────────────────────────────────────────────────────────────────────
    def _scroll(self, event: tk.Event) -> None:
        if event.num == 4:
            self._log_cv.yview_scroll(-1, "units")
        elif event.num == 5:
            self._log_cv.yview_scroll(1, "units")
        else:
            self._log_cv.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ─────────────────────────────────────────────────────────────────────────
    #  FILTER
    # ─────────────────────────────────────────────────────────────────────────
    def _flt_in(self, _e) -> None:
        self._flt_focus = True
        if self._fentry.get() == self._PLACEHOLDER:
            self._fentry.delete(0, tk.END)
            self._fentry.config(fg="#C8D8EE")

    def _flt_out(self, _e) -> None:
        self._flt_focus = False
        if not self._fentry.get().strip():
            self._fentry.insert(0, self._PLACEHOLDER)
            self._fentry.config(fg="#7E97BA")
        self._redraw_rows()

    def _flt_changed(self, *_) -> None:
        if self._flt_focus:
            self._redraw_rows()

    # ─────────────────────────────────────────────────────────────────────────
    #  BUTTON COMMANDS
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
        for w in self._log_inner.winfo_children():
            w.destroy()
        self._set_btn_states()
        self._set_badge(False)

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _set_btn_states(self) -> None:
        active = self.logger.is_active
        self._btn_start.config(state=tk.DISABLED if active else tk.NORMAL)
        self._btn_stop.config( state=tk.NORMAL   if active else tk.DISABLED)

    def _set_badge(self, active: bool) -> None:
        if active:
            self._badge_outer.config(bg=P["badge_border"])
            self._badge_inner.config(bg=P["badge_bg"])
            self._badge_dot.config(fg=P["badge_fg"],  bg=P["badge_bg"])
            self._badge_lbl.config(text="Logging Active",
                                   fg=P["badge_fg"],  bg=P["badge_bg"])
        else:
            self._badge_outer.config(bg="#3A4A5C")
            self._badge_inner.config(bg="#1E2A38")
            self._badge_dot.config(fg="#6B7E95",  bg="#1E2A38")
            self._badge_lbl.config(text="Logging Inactive",
                                   fg="#6B7E95",  bg="#1E2A38")

    def _tick(self) -> None:
        if not self.logger.is_active:
            return
        self._tvar.set(format_elapsed(self.logger.session_elapsed_seconds))
        self._timer_id = self.after(1000, self._tick)
