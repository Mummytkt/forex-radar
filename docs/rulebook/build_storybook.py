"""
Builds docs/rulebook/The_Candle_Twins_Storybook.pdf — "Pip and the Golden Bell", the
strategy told as a once-upon-a-time bedtime story (ages 6-10; rewritten 25 Oct 2026 so
children can follow it: one family, one dream, Grandma = Weekly, Papa = Daily, Pip = H4). Same rules as MummyTKT_Strategy_Rulebook.pdf; every picture is drawn
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
    im["breakout"] = scene("breakout", [(1, 5.6, 0.6, 5, G), (5, 5.3, 2.6, 3, G), (3, 6.3, 2.8, 4.9, G), (4.9, 7.9, 4.7, 7.4, G)], sx=1.8,
        levels=[(5.0, "a Giant roof (top of the shirt)", SKY, 0)],
        bubbles=[(2, 6.25, "My arm went past,\nbut my shirt didn't.\nNot yet!", (-1.6, 2.4)), (3, 7.85, "My SHIRT closed above.\nBREAKOUT!", (-0.4, 1.4))],
        ylim=(0.2, 10.2), xpad=(1.4, 3.8), speed=[1])
    im["house"] = scene("house", [(2.0, 5.0, 1.2, 4.6, G), (4.6, 9.0, 4.4, 8.6, G), (8.6, 8.8, 3.2, 3.6, G), (3.6, 7.4, 3.4, 7.0, G),
                                  (7.0, 7.1, 4.4, 4.8, G), (4.8, 6.2, 4.6, 5.9, G)], sx=1.5,
        levels=[(8.6, "Big House roof", "#b4a6dc", 1), (7.0, "smaller house roof", "#b4a6dc", 3), (5.9, "NEWEST house roof", SKY, 5),
                (4.8, "NEWEST house floor", SKY, 4), (3.6, "smaller house floor", "#b4a6dc", 2), (2.0, "Big House floor", "#b4a6dc", 0)],
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
        levels=[(4, "a Giant floor (bottom of the shirt)", RED_D, 0)],
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
    W_, P_, K_ = 1.9, 1.15, 0.62   # Grandma Wendy (Weekly), Papa Dan (Daily), little Pip (H4)
    im["family"] = scene("family", [(2.0, 9.4, 1.4, 8.8, W_), (2.0, 6.8, 1.6, 6.2, P_), (2.0, 4.2, 1.8, 3.8, K_)], sx=2.7,
        bubbles=[(0, 9.3, "I'm Grandma Wendy.\nOne step takes me\na whole WEEK!", (2.0, 0.7)),
                 (1, 6.7, "I'm Papa Dan.\nOne step takes me\na whole DAY.", (2.0, 0.4)),
                 (2, 4.1, "I'm Pip! I take SIX\nquick steps every day!", (1.5, 1.6))],
        ylim=(0.6, 11.6), xpad=(1.6, 3.4), floors=False, size=(7.0, 4.4))
    im["cover"] = scene("cover", [(2.0, 9.4, 1.4, 8.8, W_), (2.0, 6.8, 1.6, 6.2, P_), (2.0, 4.2, 1.8, 3.8, K_)], sx=2.4,
        bubbles=[(2, 4.1, "Can I ring the\nGolden Bell?", (1.5, 1.6))],
        ylim=(0.6, 10.6), xpad=(1.6, 2.6), floors=False, size=(6.2, 4.0))
    im["grandma"] = scene("grandma", [(4.0, 5.8, 3.6, 5.4, 1.6), (5.4, 8.2, 5.2, 7.8, 1.6), (7.8, 8.1, 6.0, 6.3, 1.6)], sx=2.3,
        levels=[(6.0, "old garden fence = now her bench", SKY, 0)], mats=[(5.75, 6.25, "")],
        bubbles=[(1, 8.15, "I jumped my old fence!\nThis year we go UP!", (-0.4, 1.1)),
                 (2, 6.05, "Now I'll rest on\nmy bench a while.", (1.9, -1.6))],
        ylim=(2.4, 10.4), xpad=(1.8, 5.2))
    im["papa_bench"] = scene("papa_bench", [(8.6, 8.9, 7.6, 7.8, 0.85), (7.8, 8.0, 6.6, 6.8, 0.85), (6.8, 7.5, 6.7, 7.4, 0.85),
                                            (7.4, 7.5, 6.2, 6.4, 0.85), (6.4, 6.5, 4.6, 4.8, 0.85), (4.8, 4.9, 3.0, 3.3, 0.85),
                                            (3.3, 5.4, 3.2, 5.2, 0.85), (5.2, 6.9, 5.1, 6.7, 0.85), (6.7, 8.2, 6.6, 7.9, 0.85)], sx=1.2,
        levels=[(7.4, "the fence Papa built on the way down", SKY, 2)], mats=[(2.8, 3.2, "Grandma's bench")],
        bubbles=[(3, 7.5, "I built a little\nfence up here.", (-1.8, 1.9)),
                 (5, 3.0, "My foot touched Grandma's\nbench, and I didn't fall through!", (2.6, -0.9)),
                 (8, 8.2, "I jumped my OLD fence!\nGrandma: \"PROPER JUMP!\"", (-1.2, 1.5))],
        ylim=(1.6, 10.6), xpad=(1.4, 4.0), speed=[0, 1, 3, 4, 5])
    im["cushions"] = scene("cushions", [(1.6, 2.8, 1.4, 2.6, 0.9), (2.6, 5.6, 2.5, 5.4, 0.9), (5.4, 6.2, 3.6, 6.0, 0.9),
                                        (6.0, 8.6, 5.9, 8.4, 0.9), (8.4, 9.0, 6.8, 8.8, 0.9), None,
                                        (8.8, 8.9, 6.4, 6.5, 0.55), (6.5, 6.6, 3.3, 3.6, 0.55), (3.6, 5.0, 3.5, 4.9, 0.55),
                                        (4.9, 6.6, 4.8, 6.5, 0.55)], sx=1.05,
        mats=[(2.8, 3.6, "soft cushion"), (6.2, 6.8, "soft cushion")],
        bubbles=[(4, 9.0, "We climbed so fast we\nleft soft cushions behind!", (-2.6, 1.2)),
                 (7, 3.3, "I fell right through into the\nLOWER cushion. I bounce here!", (2.0, -1.3)),
                 (9, 6.6, "Climbing back into a cushion\nfrom underneath? No bell!", (0.6, 2.4))],
        ylim=(0.6, 11.6), xpad=(1.2, 3.4), speed=[6, 7])
    im["castle"] = scene("castle", [(6.0, 7.6, 5.9, 7.4, 1.0), (7.4, 8.6, 7.2, 8.4, 1.0), (8.4, 9.8, 8.2, 9.5, 1.0),
                                    (9.5, 9.6, 8.9, 9.1, 1.0), (9.1, 10.6, 9.0, 10.4, 1.0)], sx=1.7,
        levels=[(9.0, "the great castle wall", "#8a5cf6", 0)],
        bubbles=[(2, 9.75, "I jumped the CASTLE WALL!\nSame way: the game goes on!", (-1.9, 1.3)),
                 (3, 8.95, "A new trampoline!\nPip bounces here: ENCORE!", (2.0, -1.8))],
        ylim=(4.6, 12.2), xpad=(1.5, 3.8), speed=[3])
    return im


# ── The story ─────────────────────────────────────────────────────────────────
# (title, colour, image key, [paragraphs]). Paragraphs are short on purpose.

def chapters():
    return [
        ("Once Upon a Time", GREEN_D, "meet", [
            "<b>Once upon a time</b>, in a land of very tall towers, there was a kingdom called <b>Candle Kingdom</b>.",
            "In the tallest tower lived the <b>candle people</b>. Every floor of the tower had a number, and everybody in the kingdom wanted to "
            "know one thing: <i>will the candle people go UP the tower, or DOWN?</i>",
            "When a candle person climbs <b>up</b>, they wear a <b>green coat</b>. When they slide <b>down</b>, they wear a <b>red coat</b>.",
            "Each candle person gets one turn. They start on one floor, and when the <b>Evening Bell</b> rings, they stop on another. "
            "Their coat stretches all the way from where they started to where they stopped.",
        ]),
        ("Coats Count, Arms Don't!", SKY, "arms", [
            "Candle people have a funny secret: their arms and legs are <b>stretchy</b>!",
            "While they walk, they stretch way up and way down to peek at other floors. But when the Evening Bell rings... <b>SNAP!</b> "
            "Their arms and legs spring right back.",
            "So the most important rule in all of Candle Kingdom is this:",
            "<b>Only where your COAT stops counts. Arms and legs never count.</b>",
            "Can you say it with me? <b>\"Coats count, arms don't!\"</b>",
        ]),
        ("A Very Special Family", "#8a5cf6", "family", [
            "At the very top of the tower lived a family.",
            "<b>Grandma Wendy</b> was the biggest of them all. She is wise and she is slow: one of her steps takes a <b>whole week</b>.",
            "<b>Papa Dan</b> is big and strong. One of his steps takes a <b>whole day</b>.",
            "And <b>little Pip</b>, Papa's daughter, is quick as a mouse. She takes <b>six small steps every day</b>.",
            "Pip had one big dream. On the roof of the tower hung the shiny <b>Golden Bell</b>, and Pip wanted to ring it more than anything.",
            "But the Golden Bell has a rule: <b>it only rings when the family is going the same way, in the right order.</b> "
            "Let's find out how Pip did it!",
        ]),
        ("Fences and Jumps", SUN, "breakout", [
            "Whenever a candle person climbs up (green) and the very next one slides down (red), they leave a little <b>fence</b> "
            "at the top of the green coat.",
            "A new fence is still a bit wobbly. It becomes a <b>real, strong fence</b> once a later candle walks down below it.",
            "Now, to <b>jump</b> a fence, your <b>coat</b> must stop above it when the bell rings. Poking your arm over the top doesn't count! "
            "(Remember: coats count, arms don't.)",
            "When Papa Dan jumps one of his fences, everyone shouts: <b>\"BREAKOUT!\"</b>",
        ]),
        ("Grandma Wendy Decides", "#e67700", "grandma", [
            "One week, Grandma Wendy did something she hadn't done for a long, long time. She jumped right over her big old garden fence!",
            "<b>\"This year,\"</b> she announced, <b>\"we are going UP!\"</b>",
            "But Grandma never rushes. After a big jump she always comes back to rest on a <b>bench</b>: her old fence, a soft cushion, "
            "or one of her favourite resting spots.",
            "And who do you think watches Grandma's bench very, very carefully? <b>Papa Dan.</b>",
        ]),
        ("Papa Touches Grandma's Bench", RED_D, "papa_bench", [
            "Papa Dan had been sliding <b>down</b>, red day after red day. On the way down, he stopped for a moment and built a little <b>fence</b>.",
            "Then one evening, Papa's foot touched <b>Grandma's bench</b>... and he did <b>not</b> fall through!",
            "Grandma smiled. <b>\"Remember this moment, Papa. This is your first touch.\"</b>",
            "Papa started to climb. Up, up, up... until his coat stopped <b>above the fence he had built on the way down</b>.",
            "<b>\"PROPER JUMP!\"</b> cheered Grandma. <b>\"That fence was there before you touched my bench.\"</b>",
            "If Papa had jumped a brand-new fence, one he built <b>after</b> touching the bench, Grandma would only have nodded: "
            "\"That's nice, Papa, but that's a baby fence. I'll keep waiting for a proper jump.\" Papa's jump still counts. It just isn't Grandma's proper jump.",
        ]),
        ("The Trampoline", SKY, "trampoline", [
            "Something magical happened to the fence Papa jumped. It turned into a <b>trampoline</b>!",
            "But first, Papa had to go out to play: his coat had to stop clearly above the trampoline's <b>wiggle mat</b>.",
            "Now it was <b>Pip's turn</b>. Her job was to come back down, touch the trampoline, and <b>not fall through</b>. That's called a <b>bounce</b>.",
            "Papa has other safe spots too: little <b>stepping stones</b> he left as he climbed, his old <b>dips and steps</b> inside the house he "
            "jumped out of, and his <b>soft cushions</b>. Pip may bounce on any of them.",
        ]),
        ("The Soft Cushions", "#8a5cf6", "cushions", [
            "Sometimes Papa climbs so fast that he leaves a gap. Three Papas stand in a row, and the third one's feet don't reach the first one's head. "
            "That empty space becomes a <b>soft cushion</b>.",
            "Cushions have their own rules:",
            "<b>1.</b> You may only land on a cushion by <b>dropping in from above</b>.",
            "<b>2.</b> If you fall right through it into a <b>lower cushion</b>, the lower one is where you bounce.",
            "<b>3.</b> Climbing back up into a cushion <b>from underneath</b> never counts.",
            "<b>4.</b> A cushion only <b>pops</b> when Papa's coat stops below the whole cushion.",
        ]),
        ("Pip Rings the Golden Bell", SUN, "goldbell", [
            "While Pip bounced, she built little fences of her own.",
            "The fence that matters is Pip's <b>outside fence</b>: the one she built <b>before</b> she first touched Papa's safe spot.",
            "Pip took a deep breath. She climbed... and climbed... and her coat stopped <b>above her outside fence</b>.",
            "<b>DING! DING! DING!</b> The <b>Golden Bell</b> rang across Candle Kingdom!",
            "<b>Papa jumped. Pip bounced. Pip jumped. The family was going UP!</b>",
            "Grown-ups call this ring the <b>Origin</b>. It's the most important bell of all.",
        ]),
        ("Outside Fences and Inside Fences", "#8a5cf6", "inout", [
            "Fences Pip builds <b>after</b> she touches the safe spot are <b>inside fences</b>.",
            "Jumping an inside fence doesn't ring the Golden Bell. Pip just keeps waiting for her <b>outside fence</b>. "
            "(Grown-ups can switch inside bells on if they want them.)",
        ]),
        ("Encore! Encore!", GREEN_D, "encore1", [
            "After the Golden Bell, Pip kept climbing, and the bells kept ringing!",
            "Every new fence she jumped, every bounce on her own little trampoline or step, every <b>big hug</b>: <b>ENCORE!</b>",
            "And every time she went back to bounce on one of Papa's safe spots and jumped her outside fence again: <b>ENCORE!</b>",
            "Right after a big jump, if Pip's very next step left a <b>little gap</b> behind her, a tiny bell tinkled: "
            "<i>\"A little gap was left behind!\"</i>",
            "And Papa gave hugs too! When one of Papa's big day-steps went his way and wrapped right around the step before it, "
            "that was <b>Papa's big hug</b>, and a deep bell rang at the end of the day: <i>\"Papa hugged it all!\"</i>",
        ]),
        ("Papa Jumps the Castle Wall", "#8a5cf6", "castle", [
            "One day, Papa climbed so high that his coat stopped above the <b>great castle wall</b> at the very top of the old house.",
            "<b>\"Do we have to start all over again?\"</b> asked Pip.",
            "<b>\"No!\"</b> laughed Papa. <b>\"We're still going UP. The game goes on!\"</b>",
            "There was no new Golden Bell. Instead, the castle wall became a <b>brand-new trampoline</b>, and when Pip bounced on it and "
            "jumped her fence: <b>ENCORE!</b>",
            "Grandma just nodded from her bench. \"Still going my way.\"",
        ]),
        ("The Wobble", "#ff7a59", "wobble", [
            "Sometimes, even clever Pip slips. Her coat stops <b>below her newest little dip</b>. <b>Wobble!</b>",
            "While Pip wobbles, no bells ring at all.",
            "To get back in line, she must <b>bounce on Papa's safe spot again</b> and <b>jump her fence</b>. Then: ENCORE! The climb is back on.",
        ]),
        ("When the Wind Changes", RED_D, "gameover", [
            "If Papa's coat ever stops <b>below the bottom of the house</b> he jumped out of, the wind has changed.",
            "The old game ends, and a <b>brand-new game</b> begins: this time going <b>DOWN</b>. Everything happens the mirror way, in red coats.",
            "And if Papa ever jumps the opposite way to Grandma? Pip can still ring her bell, but it comes with a little warning: "
            "<b>\"Careful! Grandma is going the other way.\"</b>",
        ]),
        ("Tiny Tia's Secret Signals", SKY, "peek", [
            "Pip has a tiny sister called <b>Tia</b>. Tia's steps are the smallest of all.",
            "Grown-ups who want to trade pick their own spot on the tower and wait for Tia to give a <b>secret signal</b> right there: "
            "a <b>Peek-and-Hold</b> (she peeks over a line and holds back) or a <b>Big Hug</b> (she wraps up the candle before her).",
            "Signals far away from their spot? Shhh. No ring.",
        ]),
    ]


MORAL = [
    "<b>And so, Pip learned the Golden Bell's secret:</b>",
    "<b>1.</b> Grandma rests on her bench. (When she does, Papa's jump can be a <b>proper jump</b>.)",
    "<b>2.</b> <b>Papa jumps</b> a fence. It becomes his trampoline.",
    "<b>3.</b> <b>Pip bounces</b> on one of Papa's safe spots and doesn't fall through.",
    "<b>4.</b> <b>Pip jumps her outside fence.</b> DING! DING! DING!",
    "<b>And never forget the kingdom's golden rule:</b> coats count, arms don't. Only where the coat stops, when the bell rings.",
    "<b>And they bounced happily ever after. The End.</b>",
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
             Paragraph("Pip", st["cover_t"]), Spacer(1, 3 * mm),
             Paragraph("and the Golden Bell", ParagraphStyle("c2", parent=st["cover_t"], fontSize=24, leading=30, textColor=colors.HexColor(SUN))),
             Spacer(1, 8 * mm), picture(im["cover"], 105 * mm), Spacer(1, 8 * mm),
             Paragraph("A Candle Kingdom bedtime story", st["cover_s"]),
             Spacer(1, 4 * mm),
             Paragraph("For children aged 6 to 10 and the grown-ups who read to them", st["cover_s"]),
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

    story += [PageBreak(), title("The Golden Bell's Secret", SUN), picture(im["family"], 70 * mm), Spacer(1, 5 * mm)]
    story += [Paragraph(p, st["moral"]) for p in MORAL]
    story += [Spacer(1, 4 * mm),
              Paragraph("<b>Ready doesn't mean sure.</b> Even when every bell rings, the twins can still surprise us. "
                        "That's why grown-ups always plan what to do if they're wrong.", st["moral"])]

    gloss = [("Green coat / red coat", "bullish candle (close above open) / bearish candle (close below open)"),
             ("Coat", "candle body (open to close): only the close counts, at the candle close"),
             ("Stretchy arms and legs", "wicks (high and low): never decide anything"),
             ("Grandma Wendy / Papa Dan / Pip / Tia", "Weekly / Daily / H4 / H1 and H2 candles"),
             ("Fence (real once a later candle walks below it)", "A-shape (V-shape = a dip, for sells); counts once a later candle trades below its bearish candle"),
             ("Jumping a fence", "a candle closing beyond the level (breakout)"),
             ("Grandma's big jump / her bench", "Weekly breakout / a Weekly key level (Weekly Breaker, Weekly V/A, OC or FVG)"),
             ("Papa's first touch of the bench", "first Daily touch of the Weekly level: the Weekly reaction's External start"),
             ("Proper jump / baby fence", "Weekly-confirmed External / Internal (in line while Internal is off)"),
             ("Trampoline / going out to play", "Daily Breaker / moving away (close beyond the Breaker ± 5 pips)"),
             ("Bounce on a safe spot", "Daily reaction: exact H4 touch that holds at a Daily level"),
             ("Stepping stones / dips and steps / soft cushions", "post-breakout Daily OCs / V-shapes and OCs in the broken range / Daily FVGs"),
             ("Cushion rules", "FVG: dip in from above only; a deeper FVG takes over; no re-entry from below; only a Daily close through it kills it"),
             ("Outside / inside fence", "External / Internal H4 level (formed before / after the first touch of the Daily level)"),
             ("Golden Bell", "Origin alert"),
             ("Encore bell", "continuation alert (in-line breakout, Breaker, OC, engulfing, Daily reaction + H4 breakout, back in line)"),
             ("Little gap bell", "H4 FVG after breakout (liquidity marker)"),
             ("A used spot", "a level that already rang its bell: only the first touch counts, Pip never bounces there for a bell again"),
             ("Papa's big hug", "Daily engulfing: a Daily candle covering the one before it, in Papa's direction"),
             ("Castle wall jumped, same way", "same-direction Daily breakout: H4 keeps riding, no new Origin"),
             ("Wobble", "H4 out of line"),
             ("Wind changes", "Daily breakout the other way: everything resets"),
             ("Grandma going the other way", "Daily setup AGAINST the Weekly"),
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
                            title="Pip and the Golden Bell", author="MummyTKT's Bias Pointer",
                            subject="The Bias Pointer strategy as a children's story")
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
    return OUT


if __name__ == "__main__":
    print(build())
