"""
Builds docs/rulebook/MummyTKT_Strategy_Rulebook.pdf — the single source of truth for
every rule the TradingView scripts implement (pine/MummyTKT_BiasPointer.pine and
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
IMG = HERE / "_img"
OUT = HERE / "MummyTKT_Strategy_Rulebook.pdf"
VERSION = "19 October 2026 · matches the Bias Pointer script with Daily market structure (most recent External high / low), exact-level, bias-side H4 rejections (19 Oct 2026) and Entry Confirmations commit 882609e"

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
        notes=[(3, 15.2, "reaction starts", GREEN), (6, 17.6, "Internal break", GREEN)], ylim=(14.9, 18.9))
    im["noneworigin"] = flow("noneworigin", [("Daily breakout", ACCENT), ("First reaction\n+ H4 break", GREEN), ("ORIGIN\n(once)", GREEN),
                                             ("Later reactions\n+ H4 breaks", ACCENT), ("CONTINUATION\nalerts", ACCENT)])
    im["breaker"] = chart("breaker", [(17.0, 17.9, 16.9, 17.7), (17.8, 18.6, 17.7, 18.4), (18.4, 18.5, 17.6, 17.9), (17.9, 18.0, 17.15, 17.7)],
        levels=[(17.3, "H4 Breaker (level broken by the Origin)", ACCENT)], zones=[(16.8, 17.8, "", ZONE)],
        notes=[(3, 16.45, "wick into breaker, close above\n→ continuation", GREEN, (2.6, 15.9))],
        labels=["H4", "H4", "H4", "H4"], ylim=(15.4, 19.1))
    im["h4oc"] = chart("h4oc", [(17.0, 17.9, 16.9, 17.8), (17.8, 18.7, 17.7, 18.6), (18.6, 18.7, 17.6, 18.1)],
        levels=[(17.8, "H4 OC (C1 close / C2 open)", ACCENT)], zones=[(17.3, 18.3, "", ZONE)],
        notes=[(1, 19.0, "completing candle\ncan't trigger it", MUTED), (2, 17.6, "later candle wicks in, closes above\n→ continuation", GREEN, (2.7, 16.3))],
        labels=["C1", "C2", "later"], ylim=(15.8, 19.6))
    im["realign"] = chart("realign", [(17.0, 17.1, 14.8, 15.0), (15.0, 15.7, 14.9, 15.6), (15.6, 15.7, 15.1, 15.2), (15.2, 16.1, 15.1, 15.95)],
        levels=[(16.4, "latest H4 V-shape", MUTED), (15.6, "latest H4 A-shape", RED, 1)],
        notes=[(0, 14.25, "closes below the latest V-shape\n→ OUT OF LINE (no alert)", RED), (3, 16.0, "closes above\n→ continuation", GREEN, (3.0, 17.0))],
        labels=["H4", "H4", "H4", "H4"], ylim=(13.8, 17.5))
    im["invalid"] = chart("invalid", [(12, 15, 11.5, 14.6), (14.6, 14.8, 12.0, 12.4), (12.4, 13.6, 11.8, 13.2), (13.2, 13.3, 9.6, 9.8)],
        levels=[(13.5, "breakout level", ACCENT), (10.5, "other side of the broken range", RED)],
        notes=[(1, 11.35, "back inside the range\n→ still VALID", GREEN, (1.0, 10.85)), (3, 8.9, "daily close below the low\n→ new SELL breakout", RED)],
        labels=["breakout", "Daily", "Daily", "Daily"], ylim=(8.2, 15.6))
    im["pcl"] = chart("pcl", [(16, 16.5, 13, 13.5), (13.5, 16.9, 13.2, 15.6)],
        levels=[(16, "C1 body high (swept level)", ACCENT)],
        notes=[(1, 17.2, "wick sweeps above", ACCENT), (1.55, 15.6, "closes back at/below\n→ bullish PCL", GREEN, (2.3, 14.4))],
        labels=["C1 down", "C2 up"], ylim=(12.6, 17.8))
    im["engulf"] = chart("engulf", [(16, 16.6, 13, 13.4), (13.4, 17.5, 12.4, 17.0)],
        levels=[(16.6, "C1 high", RED), (13.0, "C1 low (swept)", ACCENT)],
        notes=[(1, 12.0, "wick sweeps below C1 low", ACCENT), (1.3, 17.0, "body closes above C1 high\n→ bullish Engulfing Sweep", GREEN, (2.9, 14.9))],
        labels=["C1 down", "C2 up"], ylim=(11.5, 18.1))
    im["entrylevel"] = chart("entrylevel", [(16, 16.5, 13, 13.5), (13.5, 16.9, 13.2, 15.6), None, (19.5, 20, 17.5, 18), (18, 20.6, 17.8, 19.4)],
        levels=[(15.0, "your watched level", ACCENT)], zones=[(13.6, 16.4, "± your tolerance", ZONE)],
        notes=[(0.5, 17.4, "pattern inside your band → ALERT", GREEN), (3.5, 21.0, "same pattern far away → ignored", MUTED)],
        ylim=(12.4, 21.6))
    im["timing"] = timeline("timing")
    im["delivery"] = flow("delivery", [("TradingView\nsends the event", ACCENT), ("Server checks\nsource + rules", ACCENT), ("Active plan?\nTelegram linked?", INK),
                                       ("Watches this pair?\nWants this type?", INK), ("Telegram\nalert sent", GREEN)])
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
        ("C. Daily bias", "External high and low",
         "The <b>external low</b> is the lowest body bottom between a Daily A-shape and the Daily candle that <b>closes above that A-shape's level</b> "
         "(the external high is the mirror). The side in the direction of the move <b>keeps following price</b> (“still forming”) until price pulls back "
         "by closing beyond the last A/V-shape it came from; then it is fixed.",
         "Bullish: the external low is fixed; the external high follows new highs until a Daily close below the last V-shape",
         "Bearish: the external high is fixed; the external low follows new lows until a Daily close above the last A-shape",
         "A Daily close beyond the fixed level makes a new pair in the same direction. A close beyond the other level flips the direction.", im["external"]),
        ("C. Daily bias", "Structures inside the range",
         "While price is inside the current range, a <b>new structure can form inside it</b> by the same rules — a swing only counts once a later candle "
         "has traded beyond the candle that formed the A/V-shape (below the A's down candle, above the V's up candle) before the break. "
         "The new one becomes the <b>most recent External high and low</b>. This can repeat at any depth.",
         "When the most recent structure breaks, every structure inside it is dropped and the one around it counts again",
         "The Bias Pointer draws only the most recent pair, e.g. “Bullish External low” or “Bearish External low (still forming)”",
         "A close beyond an older, wider level is also beyond every newer one inside it, so the most recent pair is always the first to break.", im["layers"]),
        ("C. Daily bias", "Daily breakout",
         "A Daily candle <b>body closes beyond the most recent External high or low</b>. No tolerance is used for this. "
         "The <b>most recent break on any layer</b> sets the direction of the bias, and the level it broke is the Daily Breaker.",
         "Daily close above the most recent External high", "Daily close below the most recent External low",
         "A wick through a level is not a break. The breakout alone is not a trade signal — it starts the setup. "
         "A wick through a level is not a break. The breakout alone is not a trade signal — it starts the setup.", im["breakout"]),
        ("C. Daily bias", "The Daily Breaker and moving away first",
         f"The broken level becomes the <b>Daily Breaker</b>: former resistance becomes support (or the reverse). Its zone is the level ± {T}. "
         "Before any retest counts, an H4 candle must first <b>close beyond the zone</b> — proving price moved away.",
         "An H4 close above the breaker zone, then a later dip back into it", "An H4 close below the breaker zone, then a later rise back into it",
         "This stops a breakout that is still sitting on its level from counting as a retest straight away.", im["zone"]),
        ("D. Reaction zones (until the Origin)", "Post-breakout Daily OC",
         "After the breakout day, Daily candles that keep closing in the breakout direction, beyond the breakout level, form OCs. "
         "<b>Every completed OC</b> is watched until an opposing breakout.",
         "Two up Daily candles in a row, both closing above the breakout level", "Two down Daily candles in a row, both closing below the breakout level",
         f"The breakout candle itself doesn't count as candle 1. An OC must sit clear of the breaker zone (beyond ± {T}). "
         "The chart label shows the newest one, e.g. “D.OC 10704.99 (3 watched)”.", im["postoc"]),
        ("D. Reaction zones (until the Origin)", "What counts as a reaction",
         f"An H4 candle reacts from a zone when its <b>wick reaches the level exactly</b> (a near miss doesn't count) and its close doesn't go through it. Zones are checked in this order:",
         "1) the deepest post-breakout OC touched · 2) the Daily Breaker · 3) a Daily V-shape or Daily bullish OC level inside the range that was just broken",
         "1) the highest post-breakout OC touched · 2) the Daily Breaker · 3) a Daily A-shape or Daily bearish OC level inside the range that was just broken",
         "The reaction is reported with its source and level: Post-Breakout OC, Daily Breaker, or the Daily V/A-shape or OC inside the range. Simply being back inside the range is not a reaction. It doesn't matter which zone price reaches first. "
         "A Daily level is dead once a Daily candle closes through it (below a buy level, above a sell level) and never counts again.",
         im["zones3"]),
        ("D. Reaction zones (until the Origin)", "A reaction stays alive until it fails",
         "Once price has reacted, the reaction stays valid on <b>later candles</b>. It only <b>fails</b> when an H4 candle closes back through the zone "
         "on the wrong side. Then the next zone price reaches takes over.",
         f"Fails on an H4 close below the zone (the level − {T}, or the breaker zone)", f"Fails on an H4 close above the zone (the level + {T}, or the breaker zone)",
         "A candle that simply doesn't touch the zone any more does NOT cancel the reaction.", im["persist"]),
        ("E. H4 confirmation", "The Origin alert",
         "While a reaction is alive, an H4 candle <b>closes beyond the most recent H4 A-shape</b> (buy) or <b>V-shape</b> (sell). "
         "It can be <b>any later candle</b>, not only the one that reacted. The first confirmation of a Daily breakout is the <b>Origin</b>.",
         "H4 close above the most recent H4 A-shape level", "H4 close below the most recent H4 V-shape level",
         "The candle that forms an A/V-shape can't also break it. The alert names the reaction source and the H4 level broken.", im["origin"]),
        ("E. H4 confirmation", "External and internal breaks",
         "The script always uses the most recent H4 A/V-shape. It is <b>External</b> if it formed <b>before</b> price first reacted at the Daily level "
         "that confirms, and <b>Internal</b> if it formed <b>after</b>. If a reaction fails and price comes back to the <b>same</b> level, the first "
         "reaction there still counts as the start; a reaction at a <b>different</b> Daily level starts fresh.",
         "External: the last A-shape before price reached the Daily zone · Internal: a new A-shape formed during the reaction",
         "External: the last V-shape before price reached the Daily zone · Internal: a new V-shape formed during the reaction",
         "Each subscriber chooses in Preferences whether External and/or Internal Origins reach their Telegram.", im["extint"]),
        ("F. Continuations (after the Origin)", "One Origin per Daily breakout",
         "After the Origin fires, later reactions from Daily zones do <b>not</b> create new Origins. Further H4 breaks in the same direction are "
         "<b>continuation</b> alerts, until the next Daily breakout. While H4 is in line, every new H4 close beyond the <b>latest</b> H4 A-shape (buy) "
         "or V-shape (sell) sends an <b>“H4 breakout in line with the Daily”</b> alert; no Daily reaction is needed for it.",
         "Continuations keep firing in the buy direction", "Continuations keep firing in the sell direction",
         "Continuation alerts always reach subscribers, whatever their External/Internal preference.", im["noneworigin"]),
        ("F. Continuations (after the Origin)", "H4 Breaker retest",
         f"The H4 level broken by the Origin becomes the <b>H4 Breaker</b>. Each newer in-line H4 breakout (and a return in line) replaces it with "
         "the level it broke. When a later H4 candle <b>wicks exactly onto it and closes beyond it</b> in the bias direction, a continuation fires.",
         "Candle opens at/above the H4 breaker, wicks into it, closes above it", "Candle opens at/below the H4 breaker, wicks into it, closes below it",
         "The first one at each H4 Breaker is labelled “Breaker origin”, later ones “Breaker continuation”. Each visit alerts once; price must leave the zone before the next.",
         im["breaker"]),
        ("F. Continuations (after the Origin)", "H4 OC continuation",
         f"Two H4 candles in a row in the bias direction form an <b>H4 OC</b>. After each H4 breakout in the bias direction, <b>every OC of that breakout's leg</b> "
         "(from its swing low, or swing high for sells) and every OC formed after it is watched. When a <b>later</b> H4 candle wicks exactly onto one and closes "
         "beyond it, a continuation fires and that OC is used up.",
         "Candle opens at/above the H4 OC, wicks into it, closes above it", "Candle opens at/below the H4 OC, wicks into it, closes below it",
         "The candle that completes the OC can't trigger it, and a candle climbing up through it from below (falling through it from above, for sells) "
         "is not a rejection. If one candle rejects several OCs, one alert names the furthest and all of them are used up. An OC closed through against the "
         "bias is dropped. A newer H4 breakout keeps only its own leg's OCs; an H4 break the other way or a new Daily breakout drops them all.", im["h4oc"]),
        ("F. Continuations (after the Origin)", "Breakout continuation after a pullback",
         "If an H4 candle closes against the bias beyond the <b>latest</b> H4 V-shape (buy) or A-shape (sell), H4 is <b>out of line</b> (the chart label says OUT OF LINE) "
         "and every H4 OC is dropped. To come back in line, price must first <b>react at a Daily level again</b> (the Daily Breaker, a Daily V/A-shape "
         "or OC inside the range, or a post-breakout Daily OC — same rules as before the Origin). Then an H4 close beyond the latest H4 A/V-shape in the "
         "bias direction fires the continuation, naming that Daily level, and OC tracking starts fresh.",
         "Out of line on a close below the latest H4 V-shape; back in after a Daily reaction plus a close above the latest H4 A-shape",
         "Out of line on a close above the latest H4 A-shape; back in after a Daily reaction plus a close below the latest H4 V-shape",
         "Going out of line sends no alert. While out of line no H4 OC or H4 Breaker alerts fire, and the dashboard shows the pair as OUT OF LINE.", im["realign"]),
        ("G. A new breakout", "When the setup changes",
         "Pulling back into the range is not a cancellation — that's where reactions happen. The setup only changes at the "
         "<b>next Daily breakout</b> on any layer, in either direction.",
         "A Daily close below the other side of the broken range (or any lower low) starts a sell setup",
         "A Daily close above the other side of the broken range (or any higher high) starts a buy setup",
         "There is no separate invalidation any more: the next break replaces the setup.", im["invalid"]),
        ("H. Entry patterns (H1 / H2)", "PCL — sweep that holds",
         "A two-candle pattern measured on the previous candle's <b>body edge</b>. The new candle's wick sweeps past it, but its body closes back inside.",
         "Down candle, then up candle: its high goes above C1's body high, and it closes at or below that body high",
         "Up candle, then down candle: its low goes below C1's body low, and it closes at or above that body low",
         "The two candles must be opposite colours. Fires on candle close.", im["pcl"]),
        ("H. Entry patterns (H1 / H2)", "Engulfing Sweep — full engulf",
         "Measured on the previous candle's <b>full high and low</b>. The new candle's wick sweeps one extreme, and its body closes beyond the other.",
         "Down candle, then up candle: wick below C1's low, body closes above C1's high",
         "Up candle, then down candle: wick above C1's high, body closes below C1's low",
         "The two candles must be opposite colours. Fires on candle close.", im["engulf"]),
        ("H. Entry patterns (H1 / H2)", "When an entry alert fires",
         "Entry patterns only alert at a level <b>you chose</b> in Price Alerts → Entry Pattern Alerts: same direction, and the pattern's close within your tolerance "
         "(default 20 pips). The alert fires once, then closes.",
         "Set a Buy entry alert at your level", "Set a Sell entry alert at your level",
         "Entry alerts don't check the bias state — you decide when and where to watch.", im["entrylevel"]),
        ("I. Timing and delivery", "When alerts arrive",
         "Everything is judged at <b>candle close</b>. H4 candles on forex.com close at 2am, 6am, 10am, 2pm, 6pm and 10pm (Nigeria time); "
         "alerts arrive within moments of the close.",
         "Forex and metals: Sunday 10pm to Friday 10pm (Nigeria time)", "Crypto: around the clock",
         "When US clocks change in November, all these times move one hour later.", im["timing"]),
        ("I. Timing and delivery", "Who receives an alert",
         "An alert reaches a member only if their plan is active, their Telegram is linked, they follow that pair (Settings → My Instruments), "
         "and — for Origins — they allow that type (External / Internal).",
         "Buy and Sell alerts follow the same rules", "Continuations always go out, whatever the type setting",
         "Members without Telegram linked still see every alert on the dashboard and in History.", im["delivery"]),
    ]


GLOSSARY = [
    ("Bias", "The direction (buy or sell) the Daily breakout sets."),
    ("Breakout", "A Daily candle body closing beyond the most recent External high (buy) or low (sell)."),
    ("External high / low (Daily)", "The most recent structure's high and low. Smaller structures can form inside the range at any depth; the newest one counts."),
    ("Daily Breaker", "The broken level, now acting as support (buy) or resistance (sell)."),
    ("OC", "Open/Close level: where the first of two same-direction candles closed and the second opened."),
    ("Reaction / Retest", "An H4 candle's wick entering a Daily zone without closing through it."),
    ("Origin", "The first H4 confirmation of a Daily breakout. One per breakout."),
    ("Continuation", "Every later H4 confirmation in the same direction, until the next Daily breakout."),
    ("H4 External / Internal", "Whether the H4 A/V-shape that broke formed before or after the reaction began."),
    ("Tolerance", "The ± band (default 5 pips) used for moving away from the breaker and for a reaction failing; touches must be exact. Entry alerts use 20 pips. On crypto and Deriv synthetic indices one pip is 0.002% of price, so the 5-pip band is 0.01% of price."),
    ("Next breakout", "Any later Daily break replaces the setup; a break the other way flips the bias."),
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
        scale = min(W / pic.drawWidth, (62 * mm) / pic.drawHeight)
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
