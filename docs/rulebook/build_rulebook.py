"""
Builds docs/rulebook/MummyTKT_Strategy_Rulebook.pdf — the single source of truth for
every rule the TradingView scripts implement (pine/MummyTKT_BiasPointer.pine, v14, and
pine/MummyTKT_EntryConfirmations.pine).

When a rule changes, update RULES below (and the script), then rebuild:
    python docs/rulebook/build_rulebook.py
Needs: pip install reportlab matplotlib   (dev tool only — not used by the server)
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"   # hand-checked pictures kept in the repo (the Weekly chain)
IMG = HERE / "_img"
OUT = HERE / "MummyTKT_Strategy_Rulebook.pdf"
VERSION = "10 November 2026 (script v14: the MTF story, with the numbered pullback map. Daily breakout, H4 continuations, the pullback line, pullback confirmed, the H4 range, reaction zones and the ten story alerts. Entry Confirmations v3: PCL, OCTGD, Sweep and Break, Engulfing)"

GREEN, RED, LEVEL, ACCENT, INK, MUTED = "#1a9e6c", "#d6455a", "#7d8796", "#3b5bdb", "#182230", "#5d6b7e"
ZONE, FAIL = "#3b5bdb22", "#d6455a22"

# ── Fonts (DejaVu ships with matplotlib and covers ≥ ≤ → ± ✓) ─────────────────
_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(_FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(_FONT_DIR / "DejaVuSans-Oblique.ttf")))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")


# ── Candlestick drawing ───────────────────────────────────────────────────────

def chart(name, candles, levels=(), zones=(), notes=(), labels=None, ylim=None, size=(7.2, 2.9)):
    """candles: list of (open, high, low, close) or None for a gap.
    levels: (y, text, color, x0, x1)   zones: (lo, hi, text, color)
    notes: (x, y, text, color, (tx, ty) or None)   labels: text under each candle."""
    fig, ax = plt.subplots(figsize=size, dpi=220)
    n = len(candles)
    for lo, hi, text, col in zones:
        ax.axhspan(lo, hi, color=col, zorder=0)
        if text:
            ax.text(n + 2.4, lo, text + " ", ha="right", va="bottom", fontsize=6.5, color=MUTED, zorder=1)
    for lv in levels:
        y, text, col = lv[0], lv[1], (lv[2] if len(lv) > 2 else LEVEL)
        x0 = lv[3] if len(lv) > 3 and lv[3] is not None else -0.6
        x1 = lv[4] if len(lv) > 4 and lv[4] is not None else n - 0.4
        ax.plot([x0, x1], [y, y], ls="--", lw=1.1, color=col, zorder=2)
        ax.text(x1 + 0.05, y, " " + text, ha="left", va="center", fontsize=7.5, color=col, fontweight="bold", zorder=3)
    for i, c in enumerate(candles):
        if c is None:
            continue
        o, h, l, cl = c
        col = GREEN if cl >= o else RED
        ax.plot([i, i], [l, h], color=col, lw=1.4, zorder=4)
        ax.add_patch(Rectangle((i - 0.28, min(o, cl)), 0.56, max(abs(cl - o), 0.04), color=col, zorder=5))
    for nt in notes:
        x, y, text, col = nt[0], nt[1], nt[2], (nt[3] if len(nt) > 3 else INK)
        target = nt[4] if len(nt) > 4 else None
        if target:
            ax.annotate(text, xy=(x, y), xytext=target, fontsize=7.5, color=col, ha="center",
                        arrowprops=dict(arrowstyle="->", color=col, lw=1), zorder=6)
        else:
            ax.text(x, y, text, fontsize=7.5, color=col, ha="center", zorder=6)
    ax.set_xlim(-0.8, n + 2.6)
    if ylim:
        ax.set_ylim(*ylim)
    if labels:
        for i, t in enumerate(labels):
            if t:
                ax.text(i, ax.get_ylim()[0], t, ha="center", va="top", fontsize=7, color=MUTED)
    ax.axis("off")
    path = IMG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    plt.close(fig)
    return path


def flow(name, steps, size=(7.2, 1.5)):
    """A simple left-to-right flow of boxes."""
    fig, ax = plt.subplots(figsize=size, dpi=220)
    n = len(steps)
    w = 1.0 / n
    for i, (text, col) in enumerate(steps):
        x = i * w + 0.01
        ax.add_patch(FancyBboxPatch((x, 0.2), w - 0.04, 0.6, boxstyle="round,pad=0.01,rounding_size=0.03",
                                    fc=col + "22", ec=col, lw=1.2))
        ax.text(x + (w - 0.04) / 2, 0.5, text, ha="center", va="center", fontsize=7.6, color=INK, wrap=True)
        if i < n - 1:
            ax.annotate("", xy=(x + w - 0.005, 0.5), xytext=(x + w - 0.035, 0.5),
                        arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    path = IMG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return path


def timeline(name):
    fig, ax = plt.subplots(figsize=(7.2, 1.3), dpi=220)
    ax.plot([0, 24], [0, 0], color=LEVEL, lw=1.2)
    for h in range(0, 25, 2):
        ax.plot([h, h], [-0.08, 0.08], color=LEVEL, lw=0.8)
    for h in (2, 6, 10, 14, 18, 22):
        ax.plot([h], [0], "o", color=ACCENT, ms=7)
        lab = f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"
        ax.text(h, 0.22, lab, ha="center", fontsize=8, color=INK, fontweight="bold")
        ax.text(h, -0.38, "H4 close", ha="center", fontsize=6.5, color=MUTED)
    ax.text(22, -0.7, "Sunday open: 10pm", ha="center", fontsize=6.5, color=MUTED)
    ax.set_xlim(-0.5, 24.5); ax.set_ylim(-0.9, 0.5); ax.axis("off")
    path = IMG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return path


def make_images():
    IMG.mkdir(exist_ok=True)
    tol = 0.5
    im = {}
    im["anatomy"] = chart("anatomy", [(10, 16.2, 8.4, 14.6), None, (14.6, 15.4, 9.2, 10.2)],
        notes=[(0.45, 15.8, "upper wick", MUTED, (1.6, 16.3)), (0.4, 12.2, "body", INK, (1.5, 12.2)),
               (0.45, 9.0, "lower wick", MUTED, (1.6, 8.6)),
               (2.45, 14.6, "open", MUTED, (3.4, 14.9)), (2.45, 10.2, "close", MUTED, (3.4, 9.8))],
        labels=["bullish (up)", "", "bearish (down)"], ylim=(7.6, 17))
    im["closes"] = chart("closes", [(17, 22, 16.2, 19.2), None, (19.2, 24, 18.6, 23)],
        levels=[(20, "level", LEVEL)],
        notes=[(0, 22.5, "wick through, body closes below\n→ NOT broken", RED), (2, 24.4, "body closes above\n→ BROKEN", GREEN)],
        ylim=(15.5, 25.6))
    im["ashape"] = chart("ashape", [(10, 17, 9, 16), (16, 16.8, 11, 12)],
        levels=[(17, "Daily level with the Wick setting: highest wick", MUTED), (16, "H4 and Daily (Body, default): body high", ACCENT)],
        labels=["C1 up", "C2 down"], ylim=(8.4, 18.2))
    im["vshape"] = chart("vshape", [(16, 17, 9, 10), (10, 15, 9.2, 14)],
        levels=[(9, "Daily level with the Wick setting: lowest wick", MUTED), (10, "H4 and Daily (Body, default): body low", ACCENT)],
        labels=["C1 down", "C2 up"], ylim=(7.8, 17.6))
    im["oc"] = chart("oc", [(10, 13, 9.5, 12.5), (12.5, 15.5, 12, 15), (15, 18, 14.5, 17.5)],
        levels=[(12.5, "OC 1 = C1 close / C2 open", ACCENT, 0, 1), (15, "OC 2 = C2 close / C3 open", ACCENT, 1, 2)],
        labels=["C1", "C2", "C3"], ylim=(9, 18.6))
    im["breakout"] = chart("breakout", [(10, 14, 9, 13.5), (13.5, 13.8, 10.5, 11), (11, 14.6, 10.2, 13.2), (12.6, 15.2, 12.2, 14.7)],
        levels=[(14, "a structure high", ACCENT)],
        notes=[(2, 14.95, "wick only →\nno breakout", RED), (3, 15.55, "body closes above\n→ BREAKOUT", GREEN)],
        labels=["", "", "", "breakout"], ylim=(8.6, 16.6))
    im["external"] = chart("external", [(14, 15, 13.5, 14.8), (14.8, 15.6, 13.8, 14.0), (14.0, 14.2, 12.0, 12.4), (12.4, 13.4, 11.6, 13.2),
                                        (13.2, 16.4, 13.0, 16.1), (16.1, 18.0, 15.9, 17.7), (17.7, 18.6, 16.9, 17.1), (17.1, 17.8, 16.4, 17.5),
                                        (17.5, 17.6, 15.6, 15.9)],
        levels=[(18.6, "External high (fixed by the pullback)", GREEN, 6), (16.4, "last V-shape", MUTED, 7), (15.6, "A-shape", ACCENT, 1),
                (11.6, "External low", RED, 3)],
        notes=[(4, 16.3, "close above the A\n→ bullish break", GREEN, (2.4, 17.3)), (8, 13.7, "close below the V\n→ pullback", RED)],
        labels=["", "A", "", "", "break", "", "", "V", "pullback"], ylim=(10.6, 19.6), size=(7.2, 3.2))
    im["layers"] = chart("layers", [(19, 19.5, 17.5, 17.8), (17.8, 18.0, 15.5, 15.8), (15.8, 16.2, 13.2, 13.6), (13.6, 15.4, 13.0, 15.1),
                                    (15.1, 17.2, 14.9, 16.9), (16.9, 17.0, 15.3, 15.6), (15.6, 16.6, 15.4, 16.4)],
        levels=[(20, "earlier structure high", MUTED), (17.2, "earlier structure high", MUTED, 4), (16.6, "most recent External high", ACCENT, 6),
                (15.3, "most recent External low", ACCENT, 5), (13.0, "earlier structure low", MUTED, 3), (10.5, "earlier structure low", MUTED)],
        ylim=(9.8, 20.8), size=(7.2, 3.2))
    im["zone"] = chart("zone", [(13.6, 14.3, 13.4, 14.1), (14.1, 15.7, 14.0, 15.5), (15.5, 15.8, 14.7, 14.9), (14.9, 15.0, 13.7, 14.3)],
        levels=[(13.5, "Daily Breaker (broken level)", ACCENT)], zones=[(13.0, 14.0, "breaker zone", ZONE)],
        notes=[(1, 15.95, "H4 closes beyond the zone\n= price has moved away", INK), (3, 12.95, "now a touch counts as a retest", GREEN, (3, 12.3))],
        labels=["H4", "H4", "H4", "H4"], ylim=(11.8, 16.8))
    im["postoc"] = chart("postoc", [(12, 15, 11.5, 14.6), (14.6, 16.3, 14.3, 16.0), (16.0, 17.7, 15.7, 17.4), (17.4, 18.9, 17.0, 18.6)],
        levels=[(16.0, "OC 1", ACCENT, 1), (17.4, "OC 2", ACCENT, 2)], zones=[(13.0, 14.0, "breaker zone", ZONE)],
        notes=[(0, 15.35, "breakout day\n(doesn't count)", MUTED)],
        labels=["Daily", "Daily", "Daily", "Daily"], ylim=(11, 19.6))
    im["zones3"] = chart("zones3", [(18.9, 19.0, 18.3, 18.4), (18.4, 18.5, 15.7, 16.8)],
        levels=[(17.4, "post-breakout OC 2", ACCENT), (16.0, "post-breakout OC 1", ACCENT), (10.5, "other side of the broken range", RED)],
        zones=[(16.9, 17.9, "", ZONE), (15.5, 16.5, "", ZONE), (13.0, 14.0, "daily breaker", ZONE), (11.0, 13.0, "inside range", "#7d879614")],
        notes=[(1, 15.6, "wick touches OC 2 and OC 1\n→ reacts from OC 1 (the deepest)", GREEN, (2.2, 14.3))],
        labels=["H4", "H4"], ylim=(9.8, 19.4))
    im["persist"] = chart("persist", [(17.0, 17.2, 15.8, 16.6), (16.6, 17.1, 16.6, 16.9), (16.9, 17.0, 15.0, 15.2), (15.2, 15.4, 13.6, 14.1)],
        levels=[(16.0, "OC", ACCENT)], zones=[(15.5, 16.5, "", ZONE), (13.0, 14.0, "breaker zone", ZONE)],
        notes=[(0, 17.5, "reaction", GREEN), (1, 17.45, "not touching —\nstill alive", INK), (2, 14.55, "closes back through\n→ FAILED", RED, (2.0, 13.0)),
               (3.3, 13.8, "next zone takes over", GREEN, (4.3, 12.75))],
        labels=["H4", "H4", "H4", "H4"], ylim=(12.4, 18.1))
    im["origin"] = chart("origin", [(16.4, 17.5, 16.2, 17.3), (17.3, 17.4, 15.95, 16.3), (16.3, 16.9, 16.1, 16.7), (16.7, 17.9, 16.6, 17.8)],
        levels=[(17.3, "H4 A-shape level", RED), (16.0, "post-breakout OC", ACCENT)], zones=[(15.5, 16.5, "", ZONE)],
        notes=[(1, 15.2, "reaction", GREEN), (3, 18.15, "H4 CLOSES above → CONFIRMED\n(Origin alert)", GREEN)],
        labels=["H4", "H4", "H4", "H4"], ylim=(14.9, 18.9))
    im["extint"] = chart("extint", [(17.6, 18.4, 17.4, 18.2), (18.2, 18.3, 17.2, 17.4), (17.4, 17.5, 16.6, 16.8), (16.8, 16.9, 15.8, 16.2),
                                    (16.2, 17.0, 16.1, 16.9), (16.9, 17.0, 16.3, 16.5), (16.5, 17.4, 16.4, 17.25)],
        levels=[(18.2, "External A-shape (before the reaction)", RED, 0), (16.9, "Internal A-shape (after)", RED, 4), (16.0, "OC", ACCENT)],
        zones=[(15.5, 16.5, "", ZONE)],
        notes=[(3, 15.2, "first touch of the Daily level", GREEN), (6, 17.6, "Internal break", GREEN)], ylim=(14.9, 18.9))
    im["noneworigin"] = flow("noneworigin", [("Daily breakout", ACCENT), ("First reaction\n+ H4 break", GREEN), ("ORIGIN\n(once)", GREEN),
                                             ("Each later Daily\nreaction + H4 break", ACCENT), ("DAILY REACTION\n+ H4 BREAKOUT", ACCENT)])
    im["breaker"] = chart("breaker", [(17.0, 17.9, 16.9, 17.7), (17.8, 18.6, 17.7, 18.4), (18.4, 18.5, 17.6, 17.9), (17.9, 18.0, 17.15, 17.7)],
        levels=[(17.3, "H4 Breaker (level broken by the Origin)", ACCENT)], zones=[(16.8, 17.8, "", ZONE)],
        notes=[(3, 16.45, "wick into breaker, close above\n→ continuation", GREEN, (2.6, 15.9))],
        labels=["H4", "H4", "H4", "H4"], ylim=(15.4, 19.1))
    im["h4oc"] = chart("h4oc", [(17.0, 17.9, 16.9, 17.8), (17.8, 18.7, 17.7, 18.6), (18.6, 18.7, 17.6, 18.1)],
        levels=[(17.8, "H4 OC (C1 close / C2 open)", ACCENT)], zones=[(17.3, 18.3, "", ZONE)],
        notes=[(1, 19.0, "completing candle\ncan't trigger it", MUTED), (2, 17.6, "later candle wicks in, closes above\n→ continuation", GREEN, (2.7, 16.3))],
        labels=["C1", "C2", "later"], ylim=(15.8, 19.6))
    im["dfvg"] = chart("dfvg", [(10.0, 12.0, 9.6, 11.8), (11.8, 15.5, 11.6, 15.2), (15.2, 16.0, 13.2, 15.6),
                                (15.6, 15.7, 13.0, 14.1), (14.1, 15.8, 12.5, 15.5)],
        levels=[(12.6, "Daily Breaker", ACCENT)], zones=[(12.0, 13.2, "Daily FVG", ZONE)],
        notes=[(2, 13.2, "3rd candle's low stays above\nthe 1st's high → FVG", GREEN, (2.0, 16.6)),
               (3, 13.0, "enters the gap\n= reaction", GREEN, (3.3, 11.0)),
               (4, 12.5, "dips below the previous Daily low,\nstill in the gap → External check restarts", GREEN, (4.4, 9.9))],
        labels=["1st", "2nd (breakout)", "3rd", "enters", "deeper"], ylim=(9.2, 17.2))
    im["fvgwhich"] = chart("fvgwhich", [(12.3, 12.4, 11.9, 12.0), (12.0, 12.1, 11.2, 11.3), (11.3, 11.4, 10.2, 10.3),
                                        (10.3, 11.0, 10.25, 10.9), (10.9, 11.8, 10.85, 11.7), (11.7, 11.75, 11.6, 11.65),
                                        (11.65, 11.7, 11.0, 11.1)],
        levels=[(11.5, "External H4 level", ACCENT, None, 6.4)],
        zones=[(10.8, 11.4, "upper FVG", ZONE), (10.0, 10.4, "lower FVG", ZONE)],
        notes=[(1, 11.2, "enters the\nupper FVG", GREEN, (0.4, 9.45)),
               (2, 10.2, "goes on into the deeper FVG\n→ it takes over", GREEN, (2.6, 8.95)),
               (4, 11.8, "closes above the External level\n→ alert from the lower FVG", GREEN, (3.6, 12.6)),
               (6, 11.0, "back into the upper FVG\n→ ignored: price already went\nthrough it, and it's used up", RED, (5.6, 9.2))],
        labels=["", "", "", "", "breakout", "", "later"], ylim=(8.4, 13.0))
    im["h4fvg"] = chart("h4fvg", [(17.0, 17.4, 16.8, 17.1), (17.1, 18.6, 17.0, 18.5), (18.5, 19.0, 17.7, 18.9)],
        levels=[(17.4, "high of the candle before", ACCENT)], zones=[(17.4, 17.7, "H4 FVG", ZONE)],
        notes=[(1, 18.6, "H4 breakout\nin line", GREEN, (0.9, 19.4)),
               (2, 17.7, "next candle's low stays above\n→ “H4 FVG candle after breakout has formed”", GREEN, (2.0, 16.5))],
        labels=["before", "H4 breakout", "next candle"], ylim=(16.2, 19.9))
    im["h4engulf"] = chart("h4engulf", [(17.6, 17.75, 16.9, 17.0), (16.95, 18.05, 16.85, 17.95)],
        levels=[(17.75, "bearish candle's HIGH (top of its wick)", MUTED)],
        notes=[(1, 18.05, "opens at/below its close, closes above its high\n→ engulfing continuation", GREEN, (0.7, 18.8))],
        labels=["bearish", "engulfing"], ylim=(16.4, 19.2))
    im["dengulf"] = chart("dengulf", [(16.4, 17.1, 16.2, 16.9), (17.6, 17.75, 16.9, 17.0), (16.95, 18.05, 16.85, 17.95)],
        levels=[(17.75, "previous Daily candle's HIGH (top of its wick)", MUTED)],
        notes=[(2, 18.05, "Daily candle opens at/below its close,\ncloses above its high → Daily engulfing", GREEN, (1.2, 18.8))],
        labels=["Daily", "bearish Daily", "engulfing Daily"], ylim=(16.0, 19.2))
    im["ocformed"] = chart("ocformed", [(17.2, 17.4, 16.7, 16.8), (16.8, 17.6, 16.7, 17.5), (17.5, 18.3, 17.4, 18.2)],
        levels=[(17.5, "OC level: where the first candle closed", MUTED)],
        notes=[(2, 18.3, "second candle in a row closes in the\nDaily direction → “OC has formed”", GREEN, (0.9, 18.95))],
        labels=["", "1st bullish", "2nd bullish"], ylim=(16.3, 19.3))
    im["ocretest"] = chart("ocretest", [(10.2, 11.1, 10.1, 11.0), (11.0, 11.05, 10.3, 10.4), (9.9, 10.6, 9.7, 10.5),
                                       (10.5, 11.6, 10.4, 11.5), (11.5, 12.1, 11.4, 12.0), (12.0, 12.5, 11.9, 12.4),
                                       (12.4, 12.45, 10.95, 11.3), (11.3, 12.7, 11.2, 12.6), (12.6, 13.1, 12.5, 13.0), (13.0, 13.2, 12.6, 13.1)],
        levels=[(11.0, "H4 Breaker", ACCENT), (12.6, "H4 OC level", MUTED)],
        notes=[(3, 11.6, "H4 breakout in line", GREEN, (2.2, 12.9)),
               (6, 10.95, "touches the Breaker,\ncloses back above (held)", ACCENT, (5.4, 9.9)),
               (9, 12.6, "OC rejection after\nthe retest → alert", GREEN, (8.6, 11.4))],
        labels=["", "", "", "breakout", "", "", "retest", "", "", "OC rejection"], ylim=(9.4, 13.6))
    im["weekly"] = chart("weekly", [(15.0, 15.7, 14.9, 15.6), (15.6, 17.3, 15.5, 17.1), (17.1, 17.2, 16.0, 16.3), (16.3, 17.9, 16.1, 17.7)],
        levels=[(16.0, "Weekly Breaker (broken Weekly External high)", RED)],
        notes=[(1, 17.1, "Weekly close above\n→ Weekly breakout", GREEN, (0.4, 18.4)),
               (2, 16.0, "Daily touches the Weekly Breaker\nand holds → Weekly reaction", ACCENT, (2.1, 14.9)),
               (3, 17.7, "Daily breakout in the Weekly direction\n→ Weekly-confirmed", GREEN, (3.2, 18.6))],
        labels=["week", "week", "day", "day"], ylim=(14.2, 19.2))
    im["realign"] = chart("realign", [(17.0, 17.1, 14.8, 15.0), (15.0, 15.7, 14.9, 15.6), (15.6, 15.7, 15.1, 15.2), (15.2, 16.1, 15.1, 15.95)],
        levels=[(16.4, "latest H4 V-shape", MUTED), (15.6, "latest H4 A-shape", RED, 1)],
        notes=[(0, 14.25, "closes below the latest V-shape\n→ OUT OF LINE (no alert)", RED), (3, 16.0, "closes above\n→ continuation", GREEN, (3.0, 17.0))],
        labels=["H4", "H4", "H4", "H4"], ylim=(13.8, 17.5))
    im["invalid"] = chart("invalid", [(12, 15, 11.5, 14.6), (14.6, 14.8, 12.0, 12.4), (12.4, 13.6, 11.8, 13.2), (13.2, 13.3, 9.6, 9.8)],
        levels=[(13.5, "breakout level", ACCENT), (10.5, "other side of the broken range", RED)],
        notes=[(1, 11.35, "back inside the range\n→ still VALID", GREEN, (1.0, 10.85)), (3, 8.9, "daily close below the low\n→ new SELL breakout", RED)],
        labels=["breakout", "Daily", "Daily", "Daily"], ylim=(8.2, 15.6))
    im["pcl"] = chart("pcl", [(16, 16.5, 13, 13.5), (13.4, 15.3, 12.2, 15.0)],
        levels=[(13, "C1 low (swept)", ACCENT)],
        notes=[(1, 11.6, "wick sweeps below C1's low", ACCENT), (1.3, 15.0, "body closes back above it\n→ bullish PCL", GREEN, (2.6, 16.3))],
        labels=["C1 down", "C2 up"], ylim=(11.2, 17.2))
    im["octgd"] = chart("octgd", [(18.6, 18.8, 17.4, 17.6), (17.6, 17.8, 16.2, 16.4), (16.4, 16.6, 14.6, 14.8), (14.8, 15.6, 14.5, 15.3), (15.3, 15.5, 14.8, 15.0), (15.0, 17.5, 14.9, 17.2)],
        levels=[(16.4, "OC level (C1 close = C2 open)", ACCENT, 0.6, 5.4)], zones=[(13.8, 15.2, "POI", ZONE)],
        notes=[(1.5, 13.3, "C1 + C2: the last two down candles at the POI", MUTED), (5, 17.8, "closes above the OC level\n→ bullish OCTGD", GREEN)],
        labels=["", "C1", "C2", "", "", "break"], ylim=(12.8, 19.4))
    im["sweepbreak"] = chart("sweepbreak", [(19, 19.3, 17.2, 17.5), (17.5, 17.6, 15.6, 15.9), (15.9, 16.0, 14.6, 14.8), (14.8, 16.6, 14.7, 16.3), (16.3, 16.8, 15.9, 16.2),
                                             (16.2, 16.3, 15.2, 15.4), (15.4, 15.5, 13.9, 15.1), (15.1, 16.4, 15.0, 16.2), (16.2, 18.0, 16.1, 17.8)],
        levels=[(14.6, "low at the level", ACCENT, 2, 6.4), (16.8, "last lower high", RED, 4, 8.4)],
        notes=[(6, 13.4, "the sweep: wick below, closes back above", ACCENT), (8, 18.3, "body closes above\nthe lower high → BUY", GREEN)],
        labels=["", "", "low", "", "LH", "", "sweep", "", "break"], ylim=(12.8, 19.6))
    im["engulf"] = chart("engulf", [(16, 16.6, 13, 13.4), (13.3, 16.9, 12.9, 16.3)],
        levels=[(16.6, "C1 high (closing above it: covers the wick too)", RED), (16.0, "C1 open (closing above it: covers the body)", ACCENT)],
        notes=[(1.3, 12.2, "C2 opens at or below C1's close", MUTED)],
        labels=["C1 down", "C2 up"], ylim=(11.6, 17.6))
    im["entrylevel"] = chart("entrylevel", [(16, 16.5, 13, 13.5), (13.5, 16.9, 13.2, 15.6), None, (19.5, 20, 17.5, 18), (18, 20.6, 17.8, 19.4)],
        levels=[(15.0, "your watched level", ACCENT)], zones=[(13.6, 16.4, "± your tolerance", ZONE)],
        notes=[(0.5, 17.4, "pattern inside your band → ALERT", GREEN), (3.5, 21.0, "same pattern far away → ignored", MUTED)],
        ylim=(12.4, 21.6))
    im["timing"] = timeline("timing")
    im["delivery"] = flow("delivery", [("TradingView\nsends the event", ACCENT), ("Server checks\nsource + rules", ACCENT), ("Active plan?\nTelegram linked?", INK),
                                       ("Watches this pair?\nWants this type?", INK), ("Telegram\nalert sent", GREEN)])
    # ── The story (v14): one H4 path, buys; sells are the mirror ──
    H = [(100, 101, 99.5, 100.8), (100.8, 103, 100.5, 102.6), (102.6, 105, 102.2, 104.6), (104.6, 104.9, 102, 103),
         (103, 103.6, 101.8, 102.4), (102.4, 105.2, 102.1, 104.9), (104.9, 107.4, 104.6, 107.1), (107.1, 107.3, 104.4, 105.6),
         (105.6, 108.4, 105.3, 108.1), (108.1, 110.6, 107.8, 110.2), (110.2, 110.5, 107.5, 108), (108, 108.4, 105.6, 106),
         (106, 106.3, 103.6, 104), (104, 104.6, 102.2, 102.6), (102.6, 104.9, 102.3, 103.8), (103.8, 105, 103.4, 104.6),
         (104.6, 104.8, 101.4, 101.8), (101.8, 102, 100, 100.4), (100.4, 102.6, 100.1, 102.2), (102.2, 105.6, 102, 105.3),
         (105.3, 107.2, 105, 106.9), (106.9, 107, 104.8, 105.2), (105.2, 108.2, 105, 107.9), (107.9, 108, 106.6, 107), (107, 111.4, 106.8, 111)]
    im["s_daily"] = chart("s_daily", [(101, 103, 100.4, 102.6), (102.6, 106.2, 102.1, 105.8), (105.8, 106.4, 103, 103.6), (103.6, 105, 102.8, 104.6), (104.6, 108.4, 104.2, 108)],
        levels=[(105.8, "Daily external high", ACCENT, -0.6, 4.4), (101, "Daily external low", MUTED, -0.6, 4.4)],
        notes=[(4, 108.9, "Body closes above: Daily bullish breakout", GREEN)], ylim=(99.8, 109.8))
    im["s_real"] = chart("s_real", H[2:6],
        levels=[(104.6, "the high", ACCENT, -0.6, 3.4), (101.8, "the low that broke it: the pullback line", RED, 2, 3.4)],
        notes=[(1, 101.1, "Wick below the candle before:\na real pullback", INK), (3, 105.7, "Close above: H4 continuation", GREEN)], ylim=(100.2, 106.4))
    im["s_line"] = chart("s_line", H[0:10],
        levels=[(101.8, "pullback line, first", MUTED, 4, 6.6), (104.4, "pullback line, moved up", RED, 7, 9.4)],
        notes=[(5, 107.8, "H4.C", GREEN), (8, 108.9, "H4.C", GREEN)], ylim=(99, 111.4))
    im["s_pb"] = chart("s_pb", H[7:14],
        levels=[(104.4, "pullback line", RED, -0.6, 6.4), (106.9, "Daily range 0.5", MUTED, 3, 6.4), (110.6, "the new line (closest high, here the top)", ACCENT, 2, 6.4)],
        notes=[(5, 104, "Body closes below:\npullback confirmed", RED, (2.2, 102.7))], ylim=(101.6, 111.4))
    im["s_against"] = chart("s_against", H[12:19],
        levels=[(102.6, "the H4 low", MUTED, 1, 4.4), (105, "H4 key level: the closest high", RED, 3, 6.4)],
        notes=[(4, 101.8, "Close below: H4 bearish\ncontinuation", RED, (1.5, 100.4)), (5, 99.4, "Careful: Daily discount", INK)], ylim=(99, 106.2))
    im["s_align"] = chart("s_align", H[15:21],
        levels=[(105, "H4 key level", RED, -0.6, 5.4), (100, "H4 range low", ACCENT, 2, 5.4)],
        notes=[(4, 105.3, "Close above: back in alignment", GREEN, (1.6, 106.6))], ylim=(99.2, 107.8))
    im["s_inrange"] = chart("s_inrange", H[19:24],
        levels=[(110.2, "H4 range high", ACCENT), (104.8, "pullback line, inside the range", RED, 2, 4.4)],
        notes=[(3, 108.9, "H4.C al", GREEN)], ylim=(103.8, 111))
    im["s_high"] = chart("s_high", H[20:25],
        levels=[(110.2, "H4 range high", ACCENT)],
        notes=[(4, 111.9, "Close above: the Daily continues", GREEN)], ylim=(104.2, 112.6))
    LOWB = [H[19], (105.3, 105.6, 103, 103.4), (103.4, 103.7, 101, 101.4), (101.4, 102.8, 101.1, 102.5), (102.5, 102.7, 99.2, 99.6)]
    im["s_low"] = chart("s_low", LOWB,
        levels=[(104.2, "pullback line, inside the range", RED, -0.6, 1.4), (100.4, "H4 range low", ACCENT)],
        notes=[(1, 105.9, "PB.in", RED), (2, 99.9, "H4.C in", RED), (4, 98.6, "Close below: range low broken", RED)], ylim=(97.9, 106.6))
    im["s_zones"] = chart("s_zones", [(101, 102.2, 100.6, 102), (102, 105.2, 101.8, 104.8), (104.8, 107, 104.4, 106.6), (106.6, 107.4, 105.5, 106), (106, 108.6, 105.8, 108.3)],
        zones=[(102.2, 104.4, "FVG", ZONE)],
        levels=[(104.8, "OC", GREEN, 1, 4.4), (106, "V-shape", ACCENT, 3, 4.4)], ylim=(100, 109.2))
    im["s_merge"] = chart("s_merge", [(101, 102.2, 100.6, 102), (102, 105.2, 101.8, 104.8), (104.8, 107, 104.5, 106.6), (106.6, 106.8, 104.9, 105), (105, 108.6, 104.8, 108.3)],
        zones=[(102.2, 105, "H4 FVG+OC+V", ZONE)], ylim=(100, 109.2))
    im["s_flow"] = flow("s_flow", [("D.BO\nDaily\nbreakout", GREEN), ("H4.C\ncontinue", GREEN), ("PB · D.PC\npullback\nconfirmed", RED),
                                   ("H4.C pb\ncontinue\nagainst", RED), ("H4.P · BIA\nH4 range", ACCENT), ("H4.RHB\nDaily\ncontinues", GREEN)])
    return im


# ── Content ───────────────────────────────────────────────────────────────────

def make_rules(im):
    """Each rule: section, title, plain words, buy, sell, notes, image."""
    T = "5 pips"  # default tolerance (Bias Pointer input "Tolerance Pips")
    return [
        ("A. Candle basics", "Bullish and bearish candles",
         "A candle is <b>bullish</b> (up) when it closes at or above its open, and <b>bearish</b> (down) when it closes below its open. "
         "The <b>body</b> runs between open and close; the <b>wicks</b> are the high and low beyond the body.",
         "Close ≥ open", "Close &lt; open",
         "H4 levels and Daily levels (the External high and low, D.A, D.V and inside-range V/A-shapes) use candle <b>bodies</b>. "
         "The indicator setting <b>Daily levels from: Wick</b> switches the Daily levels back to wicks. Entry patterns are described in section H.", im["anatomy"]),
        ("A. Candle basics", "Closes, not wicks",
         "A level is only broken when a candle <b>body closes</b> beyond it. A wick that pokes through and closes back never counts as a break.",
         "Broken when a candle closes above the level", "Broken when a candle closes below the level",
         "Confirmations are judged on <b>closed</b> candles only. A candle still forming can react, but it can't confirm.", im["closes"]),
        ("B. Formations (Daily and H4)", "A-shape — resistance",
         "An up candle followed immediately by a down candle. On <b>H4</b> the level is the <b>body high of the up candle</b>. "
         "On the <b>Daily</b> it is the <b>highest body top</b> of the two candles (the highest wick with the Wick setting).",
         "Broken upward when a candle closes above it", "In a sell bias the latest Daily one is shown as D.A",
         "The level exists once the down candle has closed. The most recent A-shape is the one that counts.", im["ashape"]),
        ("B. Formations (Daily and H4)", "V-shape — support",
         "A down candle followed immediately by an up candle. On <b>H4</b> the level is the <b>body low of the down candle</b>. "
         "On the <b>Daily</b> it is the <b>lowest body bottom</b> of the two candles (the lowest wick with the Wick setting).",
         "In a buy bias the latest Daily one is shown as D.V", "Broken downward when a candle closes below it",
         "The level exists once the up candle has closed. The most recent V-shape is the one that counts.", im["vshape"]),
        ("B. Formations (Daily and H4)", "OC — Open/Close level",
         "Two candles in a row in the same direction. The OC level is where the <b>first candle closed and the second opened</b>.",
         "Two up candles in a row", "Two down candles in a row",
         "A run of three same-direction candles makes two OC levels (C1/C2 and C2/C3).", im["oc"]),
        ("C. The story", "The whole story at a glance",
         "The Daily sets the direction and H4 tells the story inside it. Each step below is an alert. The abbreviation is what you see on the chart, and the key table on the chart explains each one.",
         "Bullish Daily breakout, H4 continues up, the pullback is confirmed down, H4 turns back up inside its range", "The mirror: bearish Daily breakout, H4 continues down, the pullback is confirmed up, H4 turns back down",
         "Only one story runs at a time. Every new Daily breakout starts it again in its direction.", im["s_flow"]),
        ("C. The story", "Daily external high and low, and the Daily breakout",
         "A Daily candle <b>body closes</b> beyond the Daily external level. The chart labels the levels with the Daily direction: <b>D.Bull XH / XL</b> or <b>D.Bear XH / XL</b> (f = still forming).",
         "Daily close above the external high", "Daily close below the external low",
         "Alert: <b>Daily breakout</b>. On the chart: D.BO. A breakout the other way starts a mirrored story.", im["s_daily"]),
        ("C. The story", "A real pullback",
         "A high only counts as broken after a real pullback: a candle's <b>wick took out the previous candle's low</b>. Until then a new high is the same leg.",
         "Wick below the previous candle's low", "Wick above the previous candle's high",
         "Tiny pauses that don't take out the previous candle's low are ignored. One candle can do both, after a bearish candle: its wick takes out that candle's low and it closes above the high. A straight run of candles the same way has no high or low inside it. It then counts as a continuation and its wick is the new pullback line.", im["s_real"]),
        ("C. The story", "H4 continuations and the pullback line",
         "Each H4 body close beyond a real high is an <b>H4 continuation</b>. The <b>pullback line (PL)</b> is the last low inside the breaking move that broke a high; else the new dip low if it is above the current line; else the broken high itself (PL b). It is drawn on the candle's wick; a PL b is drawn on the high itself. A line price has already closed through is finished and is never used again: when the story restarts at a Daily breakout, the next continuation's line is the low the move came from (sells: high).",
         "Close above the last high; the line moves up", "Close below the last low; the line moves down",
         "Alert: <b>H4 continuation after the Daily breakout</b>. On the chart: H4.C.", im["s_line"]),
        ("C. The story", "Pullback confirmed",
         "An H4 <b>body close</b> beyond the pullback line. H4 is now against the Daily. The Daily range shows with its 0.5 (D.EQ): discount below, premium above. The new line, the H4 key level, is the <b>closest high inside the range just broken</b>: walking back from the breaking candle, the last candle whose wick took out the previous candle's high; none means the breaking candle's own wick. The <b>H4 range</b> resets to the range just broken: one side is the far end of the broken leg, the other is the newest leg extreme beyond the old line.",
         "H4 close below the pullback line", "H4 close above the pullback line",
         "Alert: <b>H4 pullback confirmed</b>. On the chart: PB · D.PC.", im["s_pb"]),
        ("C. The story", "H4 continuation after the pullback",
         "Each H4 close beyond the last low of this move, against the Daily, until H4 reverses into the H4 range. The <b>H4 key level</b> is the closest high: the line that moves down as each low breaks.",
         "H4 close below the last low", "H4 close above the last high",
         "Alert: <b>H4 continuation after the pullback</b>. On the chart: H4.C pb. The message warns you when price is in the Daily discount (premium for sells).", im["s_against"]),
        ("C. The story", "H4 pullback: back in alignment, the H4 range",
         "An H4 close beyond the key level brings H4 back with the Daily. The <b>H4 range</b> resets to the range just broken, as it does at every pullback: one side is the far end of the move against the Daily, the other is the newest leg extreme beyond the old line, always inside the Daily range.",
         "H4 close above the key level", "H4 close below the key level",
         "Alert: <b>H4 pullback: back in alignment</b>. On the chart: H4.P · BIA, H4.RH, H4.RL.", im["s_align"]),
        ("C. The story", "Inside the H4 range",
         "The pullback line keeps following the same rule. Each H4 close beyond a real high in the Daily direction is a continuation in alignment. A close beyond the line is a pullback break inside the range, and later breaks against the Daily are continuations inside the range. That pullback break resets the range too. If one candle closes through the line and the range edge, it is one alert: H4 pullback + continuation (H4.P+C).",
         "Close above the last high: in alignment. Close below the line: inside the range", "Close below the last low: in alignment. Close above the line: inside the range",
         "Alerts: <b>H4 continuation in alignment</b> (H4.C al), <b>Inside the H4 range: H4 against the Daily</b> (PB.in, H4.C in).", im["s_inrange"]),
        ("C. The story", "H4 range high broken: the Daily continues",
         "An H4 close beyond the H4 range high. The last H4 high inside the Daily range has gone, so the Daily continues and the story goes back to H4 continuations.",
         "H4 close above the range high", "H4 close below the range low",
         "This is a continuation: it comes as <b>H4 continuation after the Daily breakout</b>, with that switch (for sells the range's “high” is its lower side). On the chart: H4.RHB · D.C.", im["s_high"]),
        ("C. The story", "H4 range low broken: H4 against the Daily again",
         "An H4 close beyond the H4 range low. H4 is against the Daily again.",
         "H4 close below the range low", "H4 close above the range high",
         "This is a continuation too: it comes as <b>H4 continuation after the pullback</b>, with that switch. On the chart: H4.RLB.", im["s_low"]),
        ("D. Reaction zones", "FVG, OC and V-shape in the move",
         "The zones of the move price is trading in are drawn for you to watch entries: <b>FVG</b> (three-candle gap), <b>OC</b> (two candles the same way: where the first closed), <b>V-shape</b> (sells: A-shape).",
         "Zones below price, from the bullish move", "Zones above price, from the bearish move",
         "Against the Daily they start from the top of the leg; in alignment from the H4 range low; just after the Daily breakout from the pullback line. A zone is gone once an H4 candle closes through it.", im["s_zones"]),
        ("D. Reaction zones", "Merged zones",
         "Zones that touch or sit within a few pips of each other merge into one, named after its parts, to keep the chart clean.",
         "H4 FVG+OC+V", "H4 FVG+OC+A",
         "Twelve zones show by default, newest first; change it in the script settings.", im["s_merge"]),
        ("E. Entry patterns", "PCL — H1 (the same as the H1 Sweep)",
         "Measured on the previous candle's <b>low</b> (high for sells). The new candle's wick sweeps past it, and its body closes back inside.",
         "Down candle, then up candle: its wick goes below C1's low, and its body closes back above that low",
         "Up candle, then down candle: its wick goes above C1's high, and its body closes back below that high",
         "The two candles must be opposite colours. Fires on candle close.", im["pcl"]),
        ("E. Entry patterns", "OCTGD — H1: the Open-Close that got disrespected",
         "The <b>last two same-colour candles</b> as price touches your POI form an OC (C2 is the candle that touches it, or both form inside it). "
         "Its level is where C1 closes and C2 opens. Within a few candles, a candle closes through that level the other way.",
         "Two down candles at the POI (bearish OC), then an up candle closes above the OC level",
         "Two up candles at the POI (bullish OC), then a down candle closes below the OC level",
         "An OC that formed before price reached the POI does not count. A newer OC replaces the older one.", im["octgd"]),
        ("E. Entry patterns", "Sweep and Break — M15 / M5",
         "A low forms at your level (a fractal low: below the 2 candles on each side). A wick sweeps it and closes back above. "
         "Then, before a close below the sweep wick, a body closes above the last lower high.",
         "Low at the level, its sweep, then a close above the last lower high",
         "High at the level, its sweep, then a close below the last higher low",
         "Up to 20 candles from the sweep to the break. Fires on candle close.", im["sweepbreak"]),
        ("E. Entry patterns", "Engulfing — H1 / H2",
         "C2 opens at or below C1's close and its <b>body covers C1's body</b> (closes beyond C1's open). When it also closes beyond C1's high (low), "
         "it covers the wick too. One confirmation: whichever kind shows, and the alert says which.",
         "Down candle, then up candle: closes above C1's open (body), or above C1's high (wick)",
         "Up candle, then down candle: closes below C1's open (body), or below C1's low (wick)",
         "The two candles must be opposite colours. Fires on candle close.", im["engulf"]),
        ("E. Entry patterns", "When an entry alert fires",
         "Entry patterns only alert at a level <b>you chose</b> in Price Alerts → Entry Pattern Alerts: same direction, a confirmation you ticked for that level, and the wick that reached it "
         "within your tolerance (default 20 pips). The first one closes the alert, unless you chose to keep watching the others.",
         "Set a Buy entry alert at your level", "Set a Sell entry alert at your level",
         "Entry alerts don't check the bias state — you decide when and where to watch.", im["entrylevel"]),
        ("F. Timing and delivery", "When alerts arrive",
         "Everything is judged at <b>candle close</b>. H4 candles on forex.com close at 2am, 6am, 10am, 2pm, 6pm and 10pm (Nigeria time). "
         "Alerts arrive on the first tick after the close, usually within seconds. Friday's last H4 alert arrives when the market reopens on Sunday.",
         "Forex and metals: Sunday 10pm to Friday 10pm (Nigeria time)", "Crypto: around the clock",
         "When US clocks change in November, all these times move one hour later.", im["timing"]),
        ("F. Timing and delivery", "Who receives an alert",
         "An alert reaches a member only if their plan is active, their Telegram is linked, they follow that pair (Settings → My Instruments), "
         "and they allow that alert type in Alert Filters. There is one switch per alert, and each message comes in the Full or Short style they chose.",
         "Buy and Sell alerts follow the same rules", "Every alert type is on until switched off",
         "Members without Telegram linked still see every alert on the dashboard and in History.", im["delivery"]),
    ]


GLOSSARY = [
    ("Bias", "The direction (buy or sell) the Daily breakout sets."),
    ("D.Bull XH / XL, D.Bear XH / XL", "Daily external high and low, with the Daily direction. f = still forming."),
    ("D.BO", "Daily breakout: a Daily body close beyond the external level."),
    ("D.EQ", "The 0.5 of the Daily range. Discount below, premium above."),
    ("H4.C", "H4 continuation. al = in alignment, pb = in the pullback, in = against the Daily inside the H4 range."),
    ("PL, H4.PL", "Pullback line. PL b = it sits on the broken high itself."),
    ("PB, D.PC", "Pullback break: an H4 close beyond the line. Daily pullback confirmed."),
    ("H4 key level", "The pullback line while H4 is against the Daily: the closest high (sells: low)."),
    ("H4.P · BIA", "H4 pullback: back in alignment with the Daily."),
    ("H4.RH, H4.RL", "H4 range high and low. f = forming, ? = the range low if the pullback line breaks. For sells the letters swap."),
    ("H4.RHB, H4.RLB", "H4 range high broken (the Daily continues). H4 range low broken (H4 against the Daily again)."),
    ("PB.in", "Pullback break inside the H4 range."),
    ("H4.P+C", "One H4 candle closed through the pullback line and the H4 range edge: one alert instead of two."),
    ("FVG, OC, V, A", "Reaction zones. + = merged."),
    ("!", "An alert point on the chart."),
    ("Tolerance", "The ± band your entry alert allows around your level. Entry alerts use 20 pips by default."),
]


# ── PDF assembly ──────────────────────────────────────────────────────────────

def build():
    im = make_images()
    rules = make_rules(im)
    ss = {
        "title": ParagraphStyle("t", fontName="DejaVu-Bold", fontSize=26, leading=31, textColor=colors.HexColor(INK), spaceAfter=6),
        "sub": ParagraphStyle("s", fontName="DejaVu", fontSize=12, leading=17, textColor=colors.HexColor(MUTED)),
        "sec": ParagraphStyle("sec", fontName="DejaVu-Bold", fontSize=10, leading=13, textColor=colors.HexColor(ACCENT), spaceBefore=4),
        "h": ParagraphStyle("h", fontName="DejaVu-Bold", fontSize=14.5, leading=18, textColor=colors.HexColor(INK), spaceAfter=4),
        "p": ParagraphStyle("p", fontName="DejaVu", fontSize=9.6, leading=14, textColor=colors.HexColor(INK)),
        "note": ParagraphStyle("n", fontName="DejaVu", fontSize=8.6, leading=12.5, textColor=colors.HexColor(MUTED)),
        "cell": ParagraphStyle("c", fontName="DejaVu", fontSize=8.8, leading=12.2, textColor=colors.HexColor(INK)),
        "cellh": ParagraphStyle("ch", fontName="DejaVu-Bold", fontSize=8.8, leading=12, textColor=colors.white),
        "toc": ParagraphStyle("toc", fontName="DejaVu", fontSize=9.4, leading=14.5, textColor=colors.HexColor(INK)),
        "small": ParagraphStyle("sm", fontName="DejaVu", fontSize=8, leading=11, textColor=colors.HexColor(MUTED), alignment=TA_CENTER),
    }
    W = A4[0] - 36 * mm

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 7.5)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(18 * mm, 10 * mm, "MummyTKT's Bias Pointer · Strategy Rulebook")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    story = [Spacer(1, 40 * mm),
             Paragraph("MummyTKT's Bias Pointer", ss["sub"]),
             Paragraph("Strategy Rulebook", ss["title"]),
             Paragraph("Every rule the platform uses to find a directional bias, confirm it and alert you — "
                       "in plain words, with a picture for each.", ss["sub"]),
             Spacer(1, 10 * mm),
             Paragraph(f"Version: {VERSION}", ss["note"]),
             Paragraph("This rulebook is the source of truth. When a rule changes, this document and the TradingView "
                       "scripts change together.", ss["note"]),
             Spacer(1, 14 * mm),
             Paragraph("<b>How to read each rule</b>", ss["p"]), Spacer(1, 2 * mm),
             Paragraph("Each rule has a plain-words description, the exact condition for a <b>Buy</b> (bullish) and a "
                       "<b>Sell</b> (bearish) setup side by side, a picture, and notes. Pictures show the buy side; "
                       "the sell side is the mirror image. Green candles are up, red are down, dashed lines are levels, "
                       "and blue bands are zones.", ss["p"]),
             PageBreak(),
             Paragraph("Contents", ss["h"]), Spacer(1, 2 * mm)]
    last = None
    for i, r in enumerate(rules, 1):
        if r[0] != last:
            story.append(Paragraph(f"<b>{r[0]}</b>", ss["toc"]))
            last = r[0]
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;Rule {i} — {r[1]}", ss["toc"]))
    story.append(Paragraph("<b>Glossary</b>", ss["toc"]))
    story.append(PageBreak())

    last = None
    for i, (sec, title, plain, buy, sell, note, img) in enumerate(rules, 1):
        block = []
        if sec != last:
            block.append(Paragraph(sec.upper(), ss["sec"]))
            last = sec
        block += [Paragraph(f"Rule {i} — {title}", ss["h"]), Paragraph(plain, ss["p"]), Spacer(1, 3 * mm)]
        tbl = Table([[Paragraph("Buy (bullish)", ss["cellh"]), Paragraph("Sell (bearish)", ss["cellh"])],
                     [Paragraph(buy, ss["cell"]), Paragraph(sell, ss["cell"])]], colWidths=[W / 2, W / 2])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(GREEN)), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(RED)),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f4f6f9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e7ee")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e7ee")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        block += [tbl, Spacer(1, 3 * mm)]
        pic = Image(str(img))
        # the Weekly-chain pictures carry their own notes: give them the full page width
        scale = min(W / pic.drawWidth, ((120 if ASSETS in Path(str(img)).parents else 62) * mm) / pic.drawHeight)
        pic.drawWidth, pic.drawHeight = pic.drawWidth * scale, pic.drawHeight * scale
        block += [pic, Spacer(1, 1.5 * mm), Paragraph(note, ss["note"]), Spacer(1, 6 * mm)]
        story.append(KeepTogether(block))

    story += [PageBreak(), Paragraph("Glossary", ss["h"]), Spacer(1, 2 * mm)]
    g = Table([[Paragraph(f"<b>{k}</b>", ss["cell"]), Paragraph(v, ss["cell"])] for k, v in GLOSSARY], colWidths=[38 * mm, W - 38 * mm])
    g.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e7ee")),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [g, Spacer(1, 12 * mm),
              Paragraph("Directional bias only — not financial advice. Alerts describe market direction; entries, risk and "
                        "exits are your decision.", ss["small"])]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="MummyTKT's Bias Pointer — Strategy Rulebook",
                            author="MummyTKT's Bias Pointer", subject="Strategy rules")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUT


if __name__ == "__main__":
    print(build())
