"""
Builds docs/rulebook/The_Candle_Twins_Storybook.pdf — the strategy told as a children's
story (ages 7-10). Same rules as MummyTKT_Strategy_Rulebook.pdf; every picture is drawn
from real open/high/low/close values so the shapes stay chart-accurate.

    python docs/rulebook/build_storybook.py
Needs: pip install reportlab matplotlib, and Comic Sans (Windows) — falls back to DejaVu.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Ellipse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
IMG = HERE / "_img_story"
OUT = HERE / "The_Candle_Twins_Storybook.pdf"

GREEN, GREEN_D, RED, RED_D = "#2bb673", "#1b8a54", "#f0566e", "#c23a52"
INK, MUTED, SKY, SUN, MAT = "#2a2340", "#7a7090", "#5b7cfa", "#ffb627", "#ffd86b"
PAGE_BG = "#fff8e8"

# ── Fonts ─────────────────────────────────────────────────────────────────────
WIN = Path("C:/Windows/Fonts")
if (WIN / "comic.ttf").exists():
    REG, BOLD = WIN / "comic.ttf", WIN / "comicbd.ttf"
else:
    _d = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    REG, BOLD = _d / "DejaVuSans.ttf", _d / "DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("Kid", str(REG)))
pdfmetrics.registerFont(TTFont("Kid-Bold", str(BOLD)))
registerFontFamily("Kid", normal="Kid", bold="Kid-Bold", italic="Kid", boldItalic="Kid-Bold")
font_manager.fontManager.addfont(str(REG))
font_manager.fontManager.addfont(str(BOLD))
plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(REG)).get_name()


# ── Drawing the Candle Twins ──────────────────────────────────────────────────
# Every twin is drawn from (open, high, low, close): the shirt (body) runs from open to
# close, the hand touches the high and the shoe touches the low. Nothing is decorative
# beyond those four numbers.

def twin(ax, x, o, h, l, c, w=0.9, face=True, r=1.0):
    """r = data-y units per data-x unit on screen, so round things stay round."""
    bull = c >= o
    col, dark = (GREEN, GREEN_D) if bull else (RED, RED_D)
    top, bot = max(o, c), min(o, c)
    bh = max(top - bot, 0.08 * r)
    lw = 2.8 if w >= 0.7 else 2.0
    if h > top + 0.02:  # stretchy arm up to the High; the hand's top is exactly the High
        hr = w * 0.13
        ax.plot([x, x], [top, h - 2 * hr * r], color=dark, lw=lw, solid_capstyle="round", zorder=3)
        ax.add_patch(Ellipse((x, h - hr * r), 2 * hr, 2 * hr * r, fc="#ffd9b0", ec=dark, lw=1.2, zorder=4))
    if l < bot - 0.02:  # stretchy leg down to the Low; the shoe's sole is exactly the Low
        sh = w * 0.13 * r
        ax.plot([x, x], [bot, l + sh], color=dark, lw=lw, solid_capstyle="round", zorder=3)
        ax.add_patch(Ellipse((x + w * 0.1, l + sh / 2), w * 0.42, sh, fc=INK, ec=INK, zorder=4))
    ax.add_patch(FancyBboxPatch((x - w / 2, bot), w, bh, boxstyle=f"round,pad=0,rounding_size={min(w / 4, bh / (2 * r))}",
                                mutation_aspect=r, fc=col, ec=dark, lw=1.6, zorder=5))
    if not face:
        return
    s = min(w, bh / (0.75 * r))  # face size in x units; must fit in the shirt
    if s < 0.22:
        return
    ey = top - (0.3 * s) * r
    for dx in (-0.21 * s, 0.21 * s):
        ax.add_patch(Ellipse((x + dx, ey), 0.3 * s, 0.3 * s * r, fc="white", ec=dark, lw=0.8, zorder=6))
        ax.add_patch(Ellipse((x + dx + 0.03 * s, ey + (0.02 if bull else -0.03) * s * r), 0.14 * s, 0.14 * s * r, fc=INK, zorder=7))
    my = ey - 0.24 * s * r
    if bull:  # Ben: big happy smile and rosy cheeks
        ax.add_patch(Arc((x, my + 0.05 * s * r), 0.42 * s, 0.3 * s * r, theta1=200, theta2=340, color=INK, lw=1.5, zorder=7))
        for dx in (-0.36 * s, 0.36 * s):
            ax.add_patch(Ellipse((x + dx, my + 0.03 * s * r), 0.14 * s, 0.14 * s * r, fc="#ff9eb0", ec="none", alpha=0.85, zorder=6))
    else:  # Bella: determined eyebrows and a cheeky grin
        for dx, sgn in ((-0.21 * s, 1), (0.21 * s, -1)):
            ax.plot([x + dx - 0.13 * s, x + dx + 0.13 * s],
                    [ey + (0.24 + sgn * 0.05) * s * r, ey + (0.24 - sgn * 0.05) * s * r], color=INK, lw=1.5, zorder=7)
        ax.add_patch(Arc((x + 0.04 * s, my + 0.04 * s * r), 0.34 * s, 0.2 * s * r, theta1=190, theta2=350, color=INK, lw=1.5, zorder=7))


def speed_lines(ax, x, y0, y1, w=0.9):
    for i, f in enumerate((0.25, 0.5, 0.75)):
        y = y0 + (y1 - y0) * f
        ax.plot([x + w / 2 + 0.12, x + w / 2 + 0.4 + 0.1 * i], [y, y], color=RED, lw=1.4, alpha=0.6, zorder=2)


def scene(name, twins, levels=(), mats=(), bubbles=(), tags=(), ylim=(0, 10), xpad=(1.0, 3.2), floors=True,
          size=(7.4, 4.3), sx=1.6, speed=()):
    """twins: (o,h,l,c) or (o,h,l,c,w) or None for a gap, placed sx apart.
    levels: (y, text, color, i0, i1) — i0/i1 are twin indexes the line spans.
    mats: (lo, hi, text). bubbles: (i, y, text, (dx, dy)) with dy in floors. tags: (x, y, text, color)."""
    n = len(twins)
    x0, x1 = -xpad[0], (n - 1) * sx + xpad[1]
    fig = plt.figure(figsize=size, dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    r = ((ylim[1] - ylim[0]) / size[1]) / ((x1 - x0) / size[0])
    ax.add_patch(FancyBboxPatch((x0, ylim[0]), x1 - x0, ylim[1] - ylim[0], boxstyle="round,pad=0,rounding_size=0.3",
                                mutation_aspect=r, fc="#f3efff", ec="#d9d0f5", lw=1.2, zorder=0))
    if floors:
        for y in range(int(ylim[0]) + 1, int(ylim[1]) + 1):
            if y < ylim[1] - 0.2:
                ax.plot([x0 + 0.1, x1 - 0.1], [y, y], color="#e2dbf7", lw=0.8, zorder=1)
                ax.text(x0 + 0.12, y + 0.05 * r, f"floor {y}", fontsize=5.5, color="#b4a6dc", zorder=1)
    for lo, hi, text in mats:
        ax.add_patch(FancyBboxPatch((x0 + 0.1, lo), x1 - x0 - 0.2, hi - lo, boxstyle="round,pad=0,rounding_size=0.1",
                                    mutation_aspect=r, fc=MAT, ec="#e6a700", lw=0.9, ls=(0, (3, 2)), alpha=0.55, zorder=1.5))
        if text:
            ax.text(x1 - 0.2, lo + 0.04 * r, text, ha="right", va="bottom", fontsize=6.5, color="#9a6b00", zorder=2)
    for lv in levels:
        y, text, col = lv[0], lv[1], lv[2]
        i0 = lv[3] if len(lv) > 3 and lv[3] is not None else None
        i1 = lv[4] if len(lv) > 4 and lv[4] is not None else None
        xa = x0 + 0.1 if i0 is None else i0 * sx - 0.6
        xb = (n - 1) * sx + 0.6 if i1 is None else i1 * sx + 0.6
        ax.plot([xa, xb], [y, y], ls="--", lw=1.6, color=col, zorder=2)
        ax.text(xb + 0.12, y, text, ha="left", va="center", fontsize=7.5, color=col, fontweight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=col, lw=0.8))
    for i, t in enumerate(twins):
        if t is None:
            continue
        twin(ax, i * sx, *t, r=r)
    for i in speed:
        o, h, l, c = twins[i][:4]
        speed_lines(ax, i * sx, c, o, twins[i][4] if len(twins[i]) > 4 else 0.9)
    for i, y, text, (dx, dy) in bubbles:
        ax.annotate(text, xy=(i * sx, y), xytext=(i * sx + dx, y + dy), fontsize=7.6, color=INK, ha="center", va="center", zorder=9,
                    annotation_clip=False,
                    bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.8", fc="white", ec=INK, lw=1),
                    arrowprops=dict(arrowstyle="wedge,tail_width=0.6", fc="white", ec=INK, lw=1, shrinkA=0, shrinkB=2))
    for x, y, text, col in tags:
        ax.text(x, y, text, fontsize=8.5, color=col, ha="center", va="center", fontweight="bold", zorder=9)
    ax.set_xlim(x0 - 0.05, x1 + 0.05)
    ax.set_ylim(ylim[0] - 0.05, ylim[1] + 0.05)
    ax.axis("off")
    path = IMG / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)
    return path


def make_images():
    IMG.mkdir(exist_ok=True)
    G = 1.1   # giant (Daily) width
    L = 0.75  # little (H4) width
    im = {}
    im["cover"] = scene("cover", [(2, 7.6, 1.2, 6.6, 1.2), (6.6, 7.7, 1.6, 2.4, 1.2)], sx=2.4,
        bubbles=[(0, 7.4, "Up we go!", (-0.4, 1.2)), (1, 7.6, "Wheee! Down I slide!", (1.1, 1.0))],
        ylim=(0.6, 9.4), xpad=(1.8, 2.6), speed=[1], floors=False, size=(6.4, 3.8))
    im["meet"] = scene("meet", [(2, 2, 2, 7, 1.2), (7, 7, 2, 2, 1.2)], sx=4.2,
        levels=[(2, "Open: Ben starts here", GREEN_D, 0, 0), (7, "Close: Ben finishes here", GREEN_D, 0, 0)],
        tags=[(4.2, 7.55, "Open: Bella starts here", RED_D), (4.2, 1.45, "Close: Bella finishes here", RED_D)],
        ylim=(0.6, 8.6), xpad=(1.4, 1.8), speed=[1])
    im["arms"] = scene("arms", [(3, 8.6, 1.4, 6, 1.2), (6.6, 8.2, 1.8, 3.4, 1.2)], sx=4.2,
        bubbles=[(0, 8.5, "My hand reached floor 8.6:\nthat's my HIGH!", (1.9, 0.3)),
                 (0, 1.45, "My toe touched floor 1.4:\nthat's my LOW!", (2.0, -0.2)),
                 (1, 3.2, "...then SNAP! Back to\nmy closing spot.", (2.2, 0.9))],
        ylim=(0.6, 9.8), xpad=(1.4, 4.0))
    im["bell"] = scene("bell", [(3, 7.4, 2.6, 5.5, 1.0), None, (5.3, 8.4, 4.9, 7.6, 1.0)], sx=1.9,
        levels=[(6, "the big line", SKY)],
        bubbles=[(0, 7.3, "My arms poked through...\nbut my shirt finished BELOW.\nThe line is NOT broken.", (-0.2, 1.7)),
                 (2, 8.3, "My shirt finished ABOVE.\nBROKEN!", (2.3, 0.6))],
        ylim=(1.6, 10.2), xpad=(1.8, 3.4))
    im["roof"] = scene("roof", [(2, 7.2, 1.5, 6, 1.0), (6, 6.6, 2.6, 3, 1.0), None, (8, 8.3, 2.2, 4, 1.0), (4, 7, 3.6, 6.8, 1.0)], sx=1.7,
        levels=[(6, "Rooftop", SKY, 0, 1), (4, "Valley floor", RED_D, 3, 4)],
        bubbles=[(0, 7.15, "My arm doesn't count.\nThe rooftop is the\ntop of my SHIRT!", (-0.1, 1.7))],
        ylim=(1.0, 10.0), xpad=(1.4, 3.4), speed=[1, 3])
    im["handoff"] = scene("handoff", [(1.5, 4.4, 1.1, 4, L), (4, 6.9, 3.6, 6.5, L), (6.5, 8.9, 6.1, 8.5, L)], sx=1.7,
        levels=[(4, "hand-off step", SKY, 0, 1), (6.5, "hand-off step", SKY, 1, 2)],
        bubbles=[(0, 4.2, "Your turn!", (-0.2, 1.4)), (1, 6.7, "Your turn!", (-0.4, 1.3))],
        ylim=(0.6, 9.6), xpad=(1.2, 3.6))
    little = [(1, 2.5, 0.5, 2.2, 0.5), (2.2, 3.6, 2, 3.4, 0.5), (3.4, 3.6, 2.6, 2.9, 0.5), (2.9, 5.2, 2.8, 5, 0.5),
              (5, 7, 4.8, 6.8, 0.5), (6.8, 9, 6.5, 8, 0.5)]
    im["giants"] = scene("giants", [(1, 9, 0.5, 8, 1.4), None] + little, sx=1.05,
        bubbles=[(0, 8.8, "I'm ONE whole day!", (0.4, 1.0)), (5, 5.25, "We're the six Little Twins\nof that same day.", (-0.6, 3.6))],
        ylim=(0, 10.6), xpad=(1.3, 1.6))
    im["breakout"] = scene("breakout", [(1, 5.6, 0.6, 5, G), (5, 5.3, 2.6, 3, G), (3, 6.3, 2.8, 5.2, G), (5.0, 7.9, 4.7, 7.4, G)], sx=1.8,
        levels=[(5.6, "a Giant roof (fingertip)", SKY, 0)],
        bubbles=[(2, 6.25, "My arm went past,\nbut my shirt didn't.\nNot yet!", (-1.6, 2.4)), (3, 7.85, "My SHIRT closed above.\nBREAKOUT!", (-0.4, 1.4))],
        ylim=(0.2, 10.2), xpad=(1.4, 3.8), speed=[1])
    im["house"] = scene("house", [(2.0, 5.0, 1.2, 4.6, G), (4.6, 9.0, 4.4, 8.6, G), (8.6, 8.8, 3.2, 3.6, G), (3.6, 7.4, 3.4, 7.0, G),
                                  (7.0, 7.1, 4.4, 4.8, G), (4.8, 6.2, 4.6, 5.9, G)], sx=1.5,
        levels=[(9.0, "Big House roof", "#b4a6dc", 1), (7.4, "smaller house roof", "#b4a6dc", 3), (6.2, "NEWEST house roof", SKY, 5),
                (4.4, "NEWEST house floor", SKY, 4), (3.2, "smaller house floor", "#b4a6dc", 2), (1.2, "Big House floor", "#b4a6dc", 0)],
        ylim=(0.4, 10.2), xpad=(1.4, 4.6), speed=[2, 4])
    im["trampoline"] = scene("trampoline", [(5.1, 5.6, 4.9, 5.3, L), (5.3, 6.8, 5.2, 6.6, L), (6.6, 6.8, 5.8, 6.0, L), (6.0, 6.1, 4.8, 5.6, L)], sx=1.6,
        levels=[(5, "Trampoline", SKY)], mats=[(4.6, 5.4, "wiggle mat")],
        bubbles=[(0, 5.55, "Still sitting on it.\nDoesn't count yet.", (-0.3, 2.2)), (1, 6.75, "I closed above the mat:\nwent out to play!", (0.7, 1.9)),
                 (3, 4.85, "Back for a BOUNCE!", (1.9, -1.2))],
        ylim=(2.8, 9.6), xpad=(1.6, 3.4), speed=[2, 3])
    im["stones"] = scene("stones", [(3, 6.2, 2.8, 5.8, G), (5.8, 7.3, 5.6, 7, G), (7, 8.5, 6.8, 8.2, G), (8.2, 9.5, 8, 9.2, G)], sx=1.8,
        levels=[(5, "Trampoline", SKY), (7, "stone 1", GREEN_D, 1, 2), (8.2, "stone 2", GREEN_D, 2, 3)], mats=[(4.6, 5.4, "")],
        bubbles=[(0, 3.0, "Breakout day.\nI don't start a stone.", (1.4, -1.6))],
        ylim=(0.6, 10.4), xpad=(1.4, 3.2))
    im["spots"] = scene("spots", [(9.6, 9.8, 8.9, 9.0, L), (9.0, 9.1, 6.8, 7.3, L)], sx=1.6,
        levels=[(8.2, "stone 2", GREEN_D), (7, "stone 1", GREEN_D), (5, "Trampoline", SKY), (2, "other side of the house", RED_D)],
        mats=[(7.8, 8.6, ""), (6.6, 7.4, ""), (4.6, 5.4, ""), (2.4, 4.6, "inside the house that broke")],
        bubbles=[(1, 6.85, "I touched stone 2 AND stone 1.\nThe deepest one counts:\nstone 1!", (3.0, -2.6))],
        ylim=(1.2, 10.6), xpad=(1.4, 5.2), speed=[1])
    im["hold"] = scene("hold", [(8.2, 8.3, 6.9, 7.5, L), (7.5, 8.2, 7.5, 8.0, L), (8.0, 8.1, 6.0, 6.2, L), (6.2, 6.3, 4.9, 5.6, L)], sx=1.6,
        levels=[(7, "stone", GREEN_D), (5, "Trampoline", SKY)], mats=[(6.6, 7.4, ""), (4.6, 5.4, "")],
        bubbles=[(0, 6.95, "Touched!\nHolding on.", (-0.4, -2.0)), (1, 8.15, "Not touching,\nstill holding!", (0.2, 1.3)),
                 (2, 6.05, "Oops! My shirt closed\nbelow the mat. Let go!", (1.8, -2.6)),
                 (3, 4.95, "New spot\ntakes over!", (1.9, -1.4))],
        ylim=(2.2, 9.8), xpad=(1.6, 3.6), speed=[0, 2, 3])
    im["goldbell"] = scene("goldbell", [(7.6, 8.8, 7.5, 8.6, L), (8.6, 8.7, 6.9, 7.5, L), (7.5, 8.4, 7.4, 8.2, L), (8.2, 9.6, 8.1, 9.3, L)], sx=1.6,
        levels=[(8.6, "little rooftop", SKY, 0), (7, "stone", GREEN_D)], mats=[(6.6, 7.4, "")],
        bubbles=[(1, 6.95, "Visit!", (-0.6, -1.4)), (2, 8.35, "Not past\nthe rooftop yet.", (0.2, 2.0)), (3, 9.5, "DING DING!", (1.6, 0.5))],
        tags=[(5.6, 10.5, "THE GOLDEN BELL!", SUN)],
        ylim=(5.2, 11.0), xpad=(1.4, 3.6), speed=[1])
    im["inout"] = scene("inout", [(9, 10, 8.9, 9.8, L), (9.8, 9.9, 8.6, 8.8, L), (8.8, 8.9, 7.7, 7.8, L), (7.8, 7.9, 6.8, 7.2, L),
                                  (7.2, 8.3, 7.1, 8.2, L), (8.2, 8.3, 7.6, 7.8, L), (7.8, 8.9, 7.7, 8.7, L)], sx=1.25,
        levels=[(9.8, "outside roof", SKY, 0), (8.2, "inside roof", "#8a5cf6", 4), (7, "stone", GREEN_D)], mats=[(6.6, 7.4, "")],
        bubbles=[(3, 6.85, "The visit starts here.", (-1.2, -1.2)), (6, 8.65, "I broke the INSIDE roof!", (-1.2, 2.0))],
        ylim=(5.0, 11.4), xpad=(1.4, 3.4), speed=[1, 2, 3])
    im["encore1"] = scene("encore1", [(8.4, 9.5, 8.3, 9.4, L), (9.4, 10.0, 9.3, 9.9, L), (9.9, 10.0, 9.0, 9.2, L), (9.2, 9.3, 8.4, 8.9, L)], sx=1.6,
        levels=[(8.6, "little trampoline", SKY)], mats=[(8.2, 9.0, "")],
        bubbles=[(0, 9.45, "Golden Bell!", (-0.4, 1.3)), (3, 8.45, "Touch and close above:\nENCORE BELL!", (2.0, -1.4))],
        ylim=(6.4, 11.4), xpad=(1.4, 3.6), speed=[2, 3], size=(7.4, 3.0))
    im["encore2"] = scene("encore2", [(8, 8.9, 7.9, 8.8, L), (8.8, 9.7, 8.7, 9.6, L), (9.6, 9.7, 8.6, 9.1, L)], sx=1.6,
        levels=[(8.8, "little hand-off step", SKY, 0)], mats=[(8.4, 9.2, "")],
        bubbles=[(1, 9.65, "We made the step together.", (-0.6, 1.2)), (2, 8.65, "I came LATER, touched it,\nclosed above: ENCORE!", (1.6, -1.5))],
        ylim=(6.4, 11.4), xpad=(1.4, 4.0), speed=[2], size=(7.4, 3.0))
    im["wobble"] = scene("wobble", [(9.2, 9.3, 7.4, 7.6, L), (7.6, 8.1, 7.5, 8.0, L), (8.0, 8.1, 7.6, 7.7, L), (7.7, 8.7, 7.6, 8.5, L)], sx=1.6,
        levels=[(8.4, "newest little valley floor", RED_D), (8.0, "new little rooftop", SKY, 1)],
        bubbles=[(0, 7.45, "I closed below the newest\nlittle floor: WOBBLE!\n(no bell)", (1.6, -0.6)), (3, 8.65, "Back above the new rooftop:\nENCORE!", (0.4, 0.8))],
        ylim=(6.4, 10.2), xpad=(1.4, 5.6), speed=[0, 2])
    im["gameover"] = scene("gameover", [(2.5, 4.7, 2.3, 4.5, G), (4.5, 4.6, 3.3, 3.5, G), (3.5, 6.8, 3.4, 6.5, G), (6.5, 6.6, 4.0, 4.2, G), (4.2, 4.3, 2.3, 2.6, G)], sx=1.8,
        levels=[(4.5, "Trampoline (the broken roof)", SKY, 0), (3.3, "other side of the house", RED_D, 1)],
        bubbles=[(2, 6.75, "BREAKOUT!", (-0.6, 1.3)), (3, 6.6, "Back inside the house.\nStill OK!", (0.9, 1.6)),
                 (4, 2.35, "My shirt closed below the floor:\nNEW GAME, going DOWN!", (2.2, -0.9))],
        ylim=(0.6, 9.6), xpad=(1.4, 4.2), speed=[1, 3, 4])
    im["mirror"] = scene("mirror", [(8, 8.3, 3.6, 4, G), (4, 6.3, 3.8, 6, G), (6, 6.1, 2.4, 2.8, G)], sx=1.9,
        levels=[(4, "a Giant floor (toe)", RED_D, 0)],
        bubbles=[(2, 2.45, "My turn! Everything flips.\nBREAKOUT DOWN!", (2.3, 0.0))],
        ylim=(1.2, 9.0), xpad=(1.4, 4.4), speed=[0, 2])
    im["peek"] = scene("peek", [(6, 6.4, 2.6, 3, 1.0), (3, 7.2, 2.8, 5.6, 1.0)], sx=2.0,
        levels=[(6, "top of Bella's shirt", RED_D)],
        bubbles=[(1, 7.15, "I PEEKED over the line...", (-2.6, 1.0)), (1, 5.5, "...and held my shirt\nback at or below it!", (2.4, -1.4))],
        ylim=(1.6, 9.0), xpad=(2.4, 4.4), speed=[0])
    im["hug"] = scene("hug", [(6, 6.5, 3.0, 3.4, 1.0), (3.4, 7.3, 2.4, 7.0, 1.0)], sx=2.0,
        levels=[(6.5, "Bella's highest fingertip", RED_D), (3.0, "Bella's lowest toe", RED_D)],
        bubbles=[(1, 2.45, "My toe dipped below\nher lowest toe...", (2.4, -0.3)), (1, 6.95, "...and my shirt closed above\nher highest fingertip. BIG HUG!", (-1.6, 1.4))],
        ylim=(1.0, 9.4), xpad=(2.6, 4.6), speed=[0])
    im["spot"] = scene("spot", [(5.8, 6.0, 4.0, 4.2, L), (4.2, 6.3, 4.1, 5.6, L), None, (9.3, 9.4, 8.0, 8.2, L), (8.2, 9.6, 8.1, 9.0, L)], sx=1.4,
        levels=[(5, "YOUR SPOT", "#8a5cf6")], mats=[(4.0, 6.0, "your wiggle room")],
        bubbles=[(1, 6.25, "Peek-and-Hold right at\nyour spot: RING!", (-1.4, 1.8)), (4, 9.55, "Too far away.\nShhh, no ring.", (1.9, 0.4))],
        ylim=(2.6, 11.0), xpad=(1.4, 3.4), speed=[0, 3])
    im["moral"] = scene("moral", [(2, 7.6, 1.2, 6.6, 1.2), (6.6, 7.1, 1.6, 2.4, 1.2)], sx=2.4,
        bubbles=[(0, 7.4, "Wait for the bell!", (-0.5, 1.4)), (1, 7.0, "Shirts count, not arms!", (1.2, 1.6))],
        ylim=(0, 9.6), xpad=(2.0, 2.8), floors=False, size=(5.6, 3.4))
    return im


# ── The story ─────────────────────────────────────────────────────────────────
# (title, colour, image key, [paragraphs]). Paragraphs are short on purpose.

def chapters():
    return [
        ("Meet the Candle Twins", GREEN_D, "meet", [
            "In Candle Town there is a very tall building. Each level is a <b>floor</b>. The higher the floor, the higher the price.",
            "Two twins live here. <b>Bullish Ben</b> wears a bright <b>green shirt</b>. He is happy, and he loves to <b>climb</b>.",
            "Ben always starts on a low floor called his <b>Open</b>. Then up, up, UP he goes, to a higher floor called his <b>Close</b>.",
            "<b>Bearish Bella</b> wears a bright <b>red shirt</b>. She is speedy, and she loves to <b>slide</b>.",
            "Bella starts on a high floor (her <b>Open</b>) and zooms DOWN to a lower floor (her <b>Close</b>). Wheee!",
            "Their shirt always stretches from where they started to where they finished. That's the twin's <b>body</b>.",
        ]),
        ("Stretchy Arms and Stretchy Legs", SKY, "arms", [
            "The twins have a secret. Their arms and legs are <b>STRETCHY</b>!",
            "While they move, they reach out to see how far they can go. Ben's arm shoots up, up, up. Bella's leg stretches down, down, down.",
            "The highest floor a fingertip touches is called the <b>High</b>. The lowest floor a toe touches is called the <b>Low</b>.",
            "But stretching is only exploring. When time is up, <b>SNAP!</b> The arms and legs spring back, and the twin stands at the <b>Close</b>.",
            "Grown-ups call the arms and legs <b>wicks</b>.",
        ]),
        ("The Closing Bell", SUN, "bell", [
            "Every twin gets a turn. When the turn ends, the <b>Closing Bell</b> rings. Ding!",
            "Only the spot where the <b>shirt finishes</b> counts. Arms and legs can wave and wiggle all they like. They never decide anything.",
            "Look! A line is painted on the wall. The first Ben stretched his arm right through it... but his shirt finished <b>below</b> it. Not broken!",
            "The second Ben finished with his whole shirt <b>above</b> the line. Now it's <b>broken</b>.",
            "<b>Golden rule:</b> lines are only broken by shirts, and only when the bell rings.",
        ]),
        ("Rooftops and Valleys", "#8a5cf6", "roof", [
            "When Ben climbs and Bella slides <b>right after him</b>, they make a pointy <b>rooftop</b>, like the letter A.",
            "The rooftop line sits at the <b>top of Ben's shirt</b>. That's where Ben closed. His stretchy arm doesn't count!",
            "Grown-ups call it an <b>A-shape</b>, and it acts like a ceiling. Prices bump into it from below.",
            "When Bella slides and Ben climbs <b>right after her</b>, they make a <b>valley</b>, like the letter V.",
            "The valley floor sits at the <b>bottom of Bella's shirt</b>, where she closed. That's a <b>V-shape</b>, and it acts like a floor.",
            "Little Twins always use the <b>newest</b> rooftop and the <b>newest</b> valley.",
            "Giant Twins (you'll meet them soon) measure their rooftop from the <b>highest fingertip</b> of the pair, and their valley from the <b>lowest toe</b>.",
        ]),
        ("The Hand-off Step", GREEN_D, "handoff", [
            "Sometimes two Bens climb <b>one after the other</b>, like a relay race.",
            "The first Ben finishes his climb and shouts, \"Your turn!\" The second Ben starts right there.",
            "That spot, where the first twin <b>closed</b> and the next one <b>opened</b>, is a <b>Hand-off Step</b>. Grown-ups call it an <b>OC</b> (Open-Close).",
            "Three Bens in a row make <b>two</b> hand-off steps. Two Bellas sliding in a row make one too, going down.",
        ]),
        ("Giants and Little Twins", "#ff7a59", "giants", [
            "The twins come in sizes! <b>Giant Twins</b> each take a whole day. Grown-ups call them the <b>Daily</b> candles.",
            "<b>Little Twins</b> take four hours each. Grown-ups call them the <b>H4</b> candles.",
            "Six Little Twins fit inside one Giant day. Look: the first Little Twin opens where the Giant opens. The last one closes where the Giant closes.",
            "The highest Little fingertip is the Giant's High. The lowest Little toe is the Giant's Low. Same day, same moves, just different sizes.",
            "<b>Giants decide the direction. Little Twins find the moment.</b>",
        ]),
        ("Houses Inside Houses", "#8a5cf6", "house", [
            "The Giant Twins live in a <b>Big House</b>. Its floor is the lowest spot a Giant's toe reached before Ben broke out through a rooftop. Grown-ups call it the <b>external low</b>.",
            "While the Giants keep climbing, the roof keeps rising with them. It's <b>still being built</b>. When a Giant slides back down past the last valley, the roof is finished. That's the <b>external high</b>.",
            "Inside the Big House, a <b>smaller house</b> can be built in exactly the same way. And inside that one, an even smaller one, as small as you like!",
            "Candle Town only paints the <b>newest</b> house on the wall. Its roof and floor are called the <b>External high and low</b>.",
            "When a house breaks, every house inside it disappears, and the house around it is the one that counts again.",
        ]),
        ("The Great Breakout", SKY, "breakout", [
            "A Giant Ben climbs and pokes his arm past a roof. At the Closing Bell his shirt finishes... still below it. <b>Not yet!</b>",
            "The next Giant Ben climbs higher. At the Closing Bell his <b>shirt is above the roof</b>.",
            "<b>BREAKOUT!</b> Now Candle Town knows the direction: <b>UP</b>.",
            "It is always the roof or floor of the <b>newest house</b>. The newest breakout is the one that matters.",
            "A breakout is not a trade yet. It's the <b>start</b> of the adventure.",
        ]),
        ("The Old Ceiling Becomes a Trampoline", "#ff7a59", "trampoline", [
            "Here's some magic. The roof that got broken flips into a <b>Trampoline</b>! The old ceiling is now a floor to bounce on. Grown-ups call it the <b>Daily Breaker</b>.",
            "The trampoline has a cushion around it called the <b>Wiggle Mat</b>. It's 5 <b>pips</b> thick on each side. (Pips are the tiniest steps a price can take.)",
            "But first, the Little Twins must <b>go out to play</b>. A Little Twin has to close <b>above the Trampoline's Wiggle Mat</b>.",
            "A twin still sitting on the trampoline hasn't left, so it doesn't count.",
            "Only after they've gone out to play can a twin come back for a <b>bounce</b>. That's when it's a real <b>visit</b>.",
        ]),
        ("Stepping Stones", GREEN_D, "stones", [
            "After the breakout day, more Giant Bens may keep climbing. Each pair that climbs one after the other makes a <b>Stepping Stone</b>. That's a Giant hand-off step.",
            "Both Giants in the pair must close <b>above the breakout line</b>. The stone must also sit <b>clear of the Trampoline's mat</b>.",
            "The breakout day itself doesn't get to start a stone.",
            "Candle Town keeps <b>every</b> stepping stone it finds, and watches them all, until the next Giant breakout.",
        ]),
        ("The Safe Spots", SKY, "spots", [
            "Now the Little Twins go looking for a safe place to land. Bella slides down... and stretches her leg to touch a Wiggle Mat.",
            "If her toe (or shirt) touches the safe spot's <b>exact line</b> (almost touching doesn't count), and her shirt <b>doesn't close through it</b>, she has made a <b>visit</b>. Grown-ups call it a <b>reaction</b>.",
            "There are three kinds of safe spots. Candle Town checks them in this order:",
            "<b>1.</b> The <b>deepest stepping stone</b> the twin touched. <b>2.</b> The <b>Trampoline</b>. <b>3.</b> <b>Inside the house that just broke</b>: her shirt closes below the trampoline's mat but still above the other side of that house.",
            "It doesn't matter which spot the twins reach first. Any of them can be the safe spot.",
        ]),
        ("Hold On Tight!", "#ff7a59", "hold", [
            "Once a twin has made a visit, the visit <b>stays alive</b>. Later twins don't have to touch the spot again.",
            "The visit only ends if a twin's shirt <b>closes back through the spot</b>, below its mat. Then everyone lets go.",
            "But don't worry! If the twins land on the <b>next</b> safe spot, the adventure carries on from there.",
            "Not touching is fine. <b>Closing through</b> is what lets go.",
        ]),
        ("The Golden Bell", SUN, "goldbell", [
            "While a visit is alive, the Little Twins build little rooftops (little A-shapes) of their own.",
            "Then it happens. A Little Twin closes his shirt <b>above the newest little rooftop</b>. (It's almost always Ben!)",
            "<b>DING DING DING!</b> That's the <b>Golden Bell</b>. Grown-ups call it the <b>Origin</b>, and it's the main alert!",
            "It doesn't have to be the twin who visited. Any <b>later</b> Little Twin can ring it. The twin who just finished building a rooftop can't break it at the same moment.",
            "The Golden Bell rings <b>only once</b> for each Giant breakout.",
        ]),
        ("Outside Roof or Inside Roof?", "#8a5cf6", "inout", [
            "The Golden Bell always uses the <b>newest</b> little rooftop. But where was it built?",
            "If it was built <b>before</b> the visit started, it's an <b>Outside roof</b>. Grown-ups say <b>External</b>.",
            "If it was built <b>during</b> the visit, it's an <b>Inside roof</b>. Grown-ups say <b>Internal</b>.",
            "Each grown-up can choose which bells they want on their phone: outside, inside, or both.",
        ]),
        ("Encore Bells!", GREEN_D, "encore1", [
            "After the Golden Bell, the Little Twins keep climbing. Every new good bounce rings an <b>Encore Bell</b>. Grown-ups call these <b>continuations</b>.",
            "<b>The little trampoline.</b> The little rooftop that the Golden Bell broke becomes a little trampoline. If a later twin <b>starts above it</b>, comes down to touch its exact line and closes <b>above</b> it, ENCORE!",
            "<b>The little hand-off step.</b> When two Little Bens climb one after the other, they make a little step. If a <b>later</b> twin starts above it, touches it and closes above, ENCORE! (A twin climbing up through it from below doesn't count.)",
            "Each visit to a spot rings <b>once</b>. The twins must leave and come back to ring it again.",
        ]),
        (None, None, "encore2", []),
        ("The Wobble", "#ff7a59", "wobble", [
            "Sometimes the Little Twins slip. A twin closes <b>below the newest little valley floor</b>.",
            "That's a <b>Wobble</b>. They're out of line, and every little hand-off step is forgotten. No bell rings for a wobble.",
            "But if a later twin climbs back and closes <b>above the newest little rooftop</b>, ENCORE! The climb is back on.",
            "Encore Bells keep ringing like this until the next Giant breakout.",
        ]),
        ("A Brand-New Game", RED_D, "gameover", [
            "Giants can slide back <b>inside the house that just broke</b>, below the trampoline. That's okay! That's where visits happen.",
            "But if a Giant's shirt closes past the <b>other side</b> of that house (the newest house's floor), that's a <b>breakout the other way</b>.",
            "The old game ends and a <b>brand-new game</b> begins, going DOWN. Any new Giant breakout starts a new game.",
        ]),
        ("Bella's Turn: The Mirror World", RED_D, "mirror", [
            "Everything you learned works for Bella too. Just flip it upside down, like a mirror!",
            "A Giant Bella's shirt closes <b>below the newest house's floor</b>. BREAKOUT DOWN!",
            "The broken floor becomes a <b>ceiling</b>. Stepping stones are made by two Giant Bellas sliding one after the other.",
            "The Golden Bell rings when a Little Twin closes <b>below the newest little valley floor</b>. A Giant closing <b>above a roof</b> starts a new game going up.",
        ]),
        ("The Tiny Twins' Secret Signals: Peek-and-Hold", "#8a5cf6", "peek", [
            "Now meet the <b>Tiny Twins</b>. They take just one or two hours each (grown-ups say <b>H1</b> and <b>H2</b>). They help grown-ups pick the exact moment to step in.",
            "<b>Peek-and-Hold</b> (grown-ups call it a <b>PCL</b>): Bella slides first. Then Ben climbs.",
            "Ben's stretchy arm <b>peeks above the top of Bella's shirt</b>... but at the bell, his shirt finishes <b>at or below</b> that line. He peeked, and he held.",
            "Mirror version: Ben climbs first. Then Bella's leg peeks <b>below the bottom of Ben's shirt</b>, and her shirt finishes at or above it.",
        ]),
        ("The Big Hug", GREEN_D, "hug", [
            "The <b>Big Hug</b> (grown-ups call it an <b>Engulfing Sweep</b>) is a super-move!",
            "Bella slides first. Then Ben's leg stretches <b>below Bella's lowest toe</b>, sweeping underneath her.",
            "Then Ben climbs so high that his shirt closes <b>above Bella's highest fingertip</b>. He has wrapped her up in a big hug!",
            "This time it's the <b>arms and legs</b> (the High and Low) that Ben has to beat, not just her shirt.",
            "Mirror version: Ben climbs first. Bella's arm reaches above his highest fingertip, then her shirt closes below his lowest toe.",
        ]),
        ("Only at Your Spot", SKY, "spot", [
            "Tiny signals happen all over the building. Most of them aren't for you.",
            "So a grown-up picks <b>their own spot</b> and a direction (up or down). Candle Town only rings the Tiny bell when a signal closes <b>inside their wiggle room</b>. That's 20 pips each way, unless they choose different.",
            "Once it rings, that spot's bell is done.",
            "Signals far away from your spot? Shhh. No ring.",
        ]),
    ]


MORAL = [
    "<b>A trade is READY when the story goes in this order:</b>",
    "<b>1.</b> A <b>Giant</b> twin's shirt closes past the roof or floor of the newest house. Breakout!",
    "<b>2.</b> A <b>Little</b> twin visits a <b>safe spot</b> (a stepping stone, the trampoline, or inside the house that just broke) and doesn't close through it.",
    "<b>3.</b> A Little twin's shirt closes past the <b>newest little rooftop</b>. The <b>Golden Bell</b> rings!",
    "<b>4.</b> At <b>your spot</b>, a Tiny twin shows a <b>Peek-and-Hold</b> or a <b>Big Hug</b>.",
    "<b>The game changes when</b> a Giant's shirt closes past the other side of the house. Then a brand-new game starts the other way.",
    "<b>And always remember:</b> arms and legs can wiggle all they like. Only <b>shirts</b> count, and only when the <b>bell</b> rings.",
]


# ── Pages ─────────────────────────────────────────────────────────────────────

def build():
    im = make_images()
    st = {
        "cover_t": ParagraphStyle("ct", fontName="Kid-Bold", fontSize=36, leading=42, alignment=TA_CENTER, textColor=colors.HexColor(INK)),
        "cover_s": ParagraphStyle("cs", fontName="Kid", fontSize=15, leading=21, alignment=TA_CENTER, textColor=colors.HexColor(MUTED)),
        "ch": ParagraphStyle("ch", fontName="Kid-Bold", fontSize=11, leading=14, textColor=colors.HexColor(MUTED)),
        "p": ParagraphStyle("p", fontName="Kid", fontSize=14, leading=20, textColor=colors.HexColor(INK), spaceAfter=7),
        "moral": ParagraphStyle("m", fontName="Kid", fontSize=13.5, leading=19.5, textColor=colors.HexColor(INK), spaceAfter=8),
        "small": ParagraphStyle("sm", fontName="Kid", fontSize=10, leading=14, textColor=colors.HexColor(MUTED), spaceAfter=5),
    }
    W = A4[0] - 40 * mm

    def deco(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(PAGE_BG))
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#ffd27a"))
        canvas.setLineWidth(3)
        canvas.roundRect(9 * mm, 9 * mm, A4[0] - 18 * mm, A4[1] - 18 * mm, 10 * mm, fill=0, stroke=1)
        if doc.page > 1:
            canvas.setFont("Kid", 9)
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.drawCentredString(A4[0] / 2, 13 * mm, f"~ {doc.page} ~")
        canvas.restoreState()

    def picture(path, max_h):
        p = Image(str(path))
        s = min(W / p.drawWidth, max_h / p.drawHeight)
        p.drawWidth, p.drawHeight = p.drawWidth * s, p.drawHeight * s
        return p

    def title(text, col):
        return Paragraph(text, ParagraphStyle("t", fontName="Kid-Bold", fontSize=23, leading=28, textColor=colors.HexColor(col), spaceAfter=6))

    story = [Spacer(1, 22 * mm),
             Paragraph("The Candle Twins", st["cover_t"]), Spacer(1, 3 * mm),
             Paragraph("and the Golden Bell", ParagraphStyle("c2", parent=st["cover_t"], fontSize=24, leading=30, textColor=colors.HexColor(SUN))),
             Spacer(1, 8 * mm), picture(im["cover"], 105 * mm), Spacer(1, 8 * mm),
             Paragraph("A Candle Town story about how<br/>MummyTKT's Bias Pointer finds its trades", st["cover_s"]),
             Spacer(1, 4 * mm),
             Paragraph("For curious readers aged 7 to 10 (and their grown-ups)", st["cover_s"]),
             PageBreak()]

    num = 0
    for t, col, key, paras in chapters():
        if t is None:  # extra picture for the chapter before
            story += [Spacer(1, 2 * mm), picture(im[key], 62 * mm), Spacer(1, 4 * mm)]
            continue
        num += 1
        story.append(PageBreak()) if num > 1 else None
        h = 70 * mm if key == "encore1" else 98 * mm
        block = [Paragraph(f"CHAPTER {num}", st["ch"]), title(t, col), picture(im[key], h), Spacer(1, 5 * mm)]
        block += [Paragraph(p, st["p"]) for p in paras]
        story.append(KeepTogether(block[:5]))
        story += block[5:]

    story += [PageBreak(), title("The Moral of the Story", SUN), picture(im["moral"], 70 * mm), Spacer(1, 5 * mm)]
    story += [Paragraph(p, st["moral"]) for p in MORAL]
    story += [Spacer(1, 4 * mm),
              Paragraph("<b>Ready doesn't mean sure.</b> Even when every bell rings, the twins can still surprise us. "
                        "That's why grown-ups always plan what to do if they're wrong.", st["moral"])]

    gloss = [("Bullish Ben (green shirt)", "a bullish candle: close above open"),
             ("Bearish Bella (red shirt)", "a bearish candle: close below open"),
             ("Shirt", "candle body (open to close)"),
             ("Stretchy arms and legs", "upper and lower wicks (to the high and low)"),
             ("Closing Bell", "candle close; nothing is judged before it"),
             ("Rooftop / Valley floor", "A-shape / V-shape level (Giants: wicks; Little twins: bodies)"),
             ("Newest house (roof / floor)", "the most recent External high / low (Daily)"),
             ("Hand-off Step", "OC level (close of candle 1 = open of candle 2)"),
             ("Giant / Little / Tiny Twins", "Daily / H4 / H1 and H2 candles"),
             ("Wiggle Mat", "tolerance band for moving away and for a visit failing (5 pips; entry alerts 20 pips); touches must be exact"),
             ("Great Breakout", "Daily close beyond the most recent External high/low"),
             ("Trampoline", "Daily Breaker (the broken level)"),
             ("Stepping Stones", "post-breakout Daily OCs (all watched)"),
             ("Visit", "reaction / retest of a Daily zone"),
             ("Golden Bell", "Origin alert (first H4 confirmation)"),
             ("Outside / Inside roof", "External / Internal H4 break"),
             ("Encore Bell", "continuation alert"),
             ("Wobble", "H4 out of line (chart label: OUT OF LINE)"),
             ("Brand-new game", "the next Daily breakout replaces the setup"),
             ("Peek-and-Hold / Big Hug", "PCL / Engulfing Sweep entry patterns")]
    cell = ParagraphStyle("cell", fontName="Kid", fontSize=9.6, leading=12.5, textColor=colors.HexColor(INK))
    tbl = Table([[Paragraph(f"<b>{a}</b>", cell), Paragraph(b, cell)] for a, b in gloss], colWidths=[62 * mm, W - 62 * mm])
    tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#ecd9a8")),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story += [PageBreak(), title("For Grown-Ups", MUTED),
              Paragraph("Every picture in this book is drawn from real open, high, low and close values. The rules match the "
                        "<b>MummyTKT Strategy Rulebook</b> exactly. Here is the story word for each real term:", st["small"]),
              Spacer(1, 2 * mm), tbl, Spacer(1, 5 * mm),
              Paragraph("Directional bias education only, not financial advice. Trading carries real risk and is for adults.", st["small"])]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
                            title="The Candle Twins and the Golden Bell", author="MummyTKT's Bias Pointer",
                            subject="The Bias Pointer strategy as a children's story")
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
    return OUT


if __name__ == "__main__":
    print(build())
