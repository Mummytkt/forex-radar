"""Picture of the merged Bias Pointer + Pullback Story model (user, 2026-10-31), buys and
the mirrored sells. H4 candles with the Daily levels on top; an M15 inset for the entry.
Output: Documents/Aligned_Story_Buys.svg / Aligned_Story_Sells.svg (+ PNG)."""
import html
import random
import re
import textwrap

W, H = 2120, 1180
L, R, T, B = 60, 1380, 110, 880
esc = html.escape

WAY = [(0, 86), (4, 92), (6, 90), (10, 97), (12, 95), (16, 101.6), (18, 98.2), (22, 104), (25, 101.6), (29, 108),
       (32, 105.2), (36, 112), (38, 113), (41, 107.5), (42, 104.4), (45, 109), (49, 102), (51, 105), (55, 96.7),
       (57, 99), (58, 97.9), (61, 106.2), (64, 102.4), (66, 104.2), (72, 113.6), (76, 116.5)]

SWAP = {"bullish": "bearish", "long": "short", "longs": "shorts", "demand": "supply", "high": "low", "highs": "lows",
        "discount": "premium", "buy": "sell", "buys": "sells", "HL": "LH", "HH": "LL", "up": "down", "higher": "lower",
        "below": "above", "above": "below", "lower": "higher", "BUY": "SELL", "BUYS": "SELLS", "Buy": "Sell",
        "resistance": "support"}
SWAP.update({v: k for k, v in list(SWAP.items()) if v not in SWAP})


def swap(t):
    def rep(m):
        w = m.group(0)
        r = SWAP.get(w) or SWAP.get(w.lower())
        if r is None:
            return w
        if w.isupper() and len(w) > 2:
            return r.upper()
        return r.capitalize() if w[0].isupper() and not w.isupper() else r
    t = t.replace("V-shape", "").replace("A-shape", "")
    t = re.sub(r"[A-Za-z]+", rep, t)
    return t.replace("", "A-shape").replace("", "V-shape")


def candles(way, seed, noise=0.45, wick=1.0):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for t in range(a, b):
            path.append(pa + (pb - pa) * (t - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 0.6
    for p in path:
        o, c = prev, p + random.uniform(-noise, noise)
        out.append((o, max(o, c) + random.uniform(0.15, wick), min(o, c) - random.uniform(0.15, wick), c))
        prev = c
    return out


def build(bull):
    t = (lambda s: s) if bull else swap
    G, RD, PU = "#16a34a", "#dc2626", "#7c3aed"
    WITH, AGAINST = (G, RD) if bull else (RD, G)
    cs = candles(WAY, 21)
    n = len(cs)
    lo, hi = 82, 120
    dx = (R - L) / (n + 3)
    X = lambda i: L + dx * (i + 0.5)
    Y = (lambda p: B - (p - lo) / (hi - lo) * (B - T)) if bull else (lambda p: T + (p - lo) / (hi - lo) * (B - T))
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    a(f'<text x="{L}" y="44" font-size="28" font-weight="800" fill="#111">THE DAILY → H4 → M15 STORY · {"BUYS" if bull else "SELLS"}</text>')
    a(f'<text x="{L}" y="72" font-size="16" fill="#444">{esc(t("Bias Pointer external breakout, H4 continuations, the Daily pullback, H4 back in line inside the Daily range, then the M15 entry. H4 candles; Daily levels on top."))}</text>')

    def box(i0, i1, p1, p2, col, txt, op=0.16, where='in', dash=''):
        ya, yb = sorted((Y(p1), Y(p2)))
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<rect x="{X(i0) - dx / 2:.1f}" y="{ya:.1f}" width="{X(i1) - X(i0) + dx:.1f}" height="{yb - ya:.1f}" fill="{col}" opacity="{op}" stroke="{col}" stroke-opacity="0.7"{d}/>')
        if txt:
            if where == 'in':
                a(f'<text x="{X(i1) + dx / 2 - 4:.1f}" y="{(ya + yb) / 2 + 4:.1f}" font-size="12" font-weight="700" fill="{col}" text-anchor="end">{esc(t(txt))}</text>')
            else:
                a(f'<text x="{X(i1) + dx:.1f}" y="{(ya + yb) / 2 + 4:.1f}" font-size="12" font-weight="700" fill="{col}">{esc(t(txt))}</text>')

    def line(i0, i1, p, col, dash, w, txt, where='end', size=12, op=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{w}" opacity="{op}"{d}/>')
        if txt:
            if where == 'end':
                a(f'<text x="{X(i1) + 6:.1f}" y="{Y(p) + 4:.1f}" font-size="{size}" font-weight="700" fill="{col}" opacity="{op}">{esc(t(txt))}</text>')
            else:
                above = (where == 'above') == bull
                a(f'<text x="{(X(i0) + X(i1)) / 2:.1f}" y="{Y(p) - 6 if above else Y(p) + 15:.1f}" font-size="{size}" font-weight="700" fill="{col}" text-anchor="middle" opacity="{op}">{esc(t(txt))}</text>')

    # Daily range after the pullback: low 86 (the low that caused the breakout) → high 113; 0.5 = 99.5
    ya, yb = sorted((Y(86), Y(99.5)))
    a(f'<rect x="{X(42):.1f}" y="{ya:.1f}" width="{X(n + 1) - X(42):.1f}" height="{yb - ya:.1f}" fill="{WITH}" opacity="0.05"/>')
    ya, yb = sorted((Y(99.5), Y(113)))
    a(f'<rect x="{X(42):.1f}" y="{ya:.1f}" width="{X(n + 1) - X(42):.1f}" height="{yb - ya:.1f}" fill="{AGAINST}" opacity="0.04"/>')

    # Daily levels in the discount (marked once the Daily pullback is confirmed)
    box(42, n, 96.0, 98.2, WITH, "Daily demand (box)", 0.20)
    box(42, n, 91.8, 93.8, WITH, "Daily bullish FVG (box)", 0.12)
    line(42, n, 97.3, WITH, "", 1.6, "Daily V-shape (line)", 'end', 11.5)
    line(42, n, 94.8, WITH, "6 3", 1.6, "Daily OC (line)", 'end', 11.5)
    line(42, 50, 101.0, "#9ca3af", "4 4", 1.4, "Daily OC: a Daily close went through it → removed", 'below', 11, 0.9)

    # H4 levels inside the H4 range (after the H4 breakout): an H4 close through one removes it
    box(59, n, 102.0, 103.4, WITH, "H4 demand (box)", 0.24)
    line(59, n, 104.0, WITH, "2 3", 1.4, "H4 V-shape (line)", 'end', 11)

    # candles
    for i, (op, h, l, c) in enumerate(cs):
        up = (c >= op) if bull else (c < op)
        a(f'<line x1="{X(i):.1f}" y1="{Y(h):.1f}" x2="{X(i):.1f}" y2="{Y(l):.1f}" stroke="#1e3a8a" stroke-width="1.1"/>')
        y1, y2 = sorted((Y(op), Y(c)))
        a(f'<rect x="{X(i) - dx * 0.32:.1f}" y="{y1:.1f}" width="{dx * 0.64:.1f}" height="{max(y2 - y1, 1.3):.1f}" fill="{"#ffffff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')

    # Daily structure
    line(2, 16, 100, "#111", "", 2.2, "Daily external high (Bias Pointer)", 'above', 12)
    line(16, n, 100, "#111", "8 5", 1.6, "Daily Breaker (line)", 'end', 11.5)
    line(0, n, 86, "#111", "", 2.2, "Daily range low", 'end', 12)
    line(38, n, 113, "#111", "", 2.2, "Daily range high (target)", 'end', 12)
    line(42, n, 99.5, "#888", "6 6", 1.3, "Daily range 0.5", 'end', 11)

    # H4 continuations: BOS lines and the "last H4 low" line that moves up
    for (p0, i0, i1) in ((97, 10, 16), (104, 22, 29), (108, 29, 36)):
        line(i0, i1, p0 if p0 != 97 else 97, WITH, "1.5 3", 1.4, "H4 BOS up", 'above', 11)
    for (p, i0, i1) in ((98.2, 18, 25), (101.6, 25, 32), (105.2, 32, 42)):
        line(i0, i1, p, "#0284c7", "", 2.4, "", 'end')
    a(f'<text x="{X(25):.1f}" y="{Y(101.6) + (17 if bull else -9):.1f}" font-size="12" font-weight="700" fill="#0284c7">{esc(t("last H4 low (moves up after each H4 BOS up)"))}</text>')
    line(32, 42, 105.2, AGAINST, "1.5 3", 1.6, "H4 BOS down: Daily pullback confirmed", 'below', 12)

    # H4 back in line: the external break of the lower high formed before the reaction
    line(51, 61, 105, WITH, "", 2, "H4 external BOS up", 'above', 12)
    a(f'<rect x="{X(61) - 64:.1f}" y="{Y(109.6) - (22 if bull else -2):.1f}" width="128" height="22" rx="5" fill="{WITH}"/>')
    a(f'<text x="{X(61):.1f}" y="{Y(109.6) - (6 if bull else -18):.1f}" font-size="12.5" font-weight="800" fill="#fff" text-anchor="middle">{esc("Daily + H4 aligned")}</text>')
    # the H4 range: Daily high ↔ the H4 low before the breakout
    line(55, n, 96.7, "#f59e0b", "", 2, "H4 range low", 'below', 11)
    a(f'<line x1="{X(61):.1f}" y1="{Y(96.7):.1f}" x2="{X(61):.1f}" y2="{Y(113):.1f}" stroke="#f59e0b" stroke-dasharray="3 4" opacity="0.6"/>')
    a(f'<text x="{X(61) + 6:.1f}" y="{Y(112) + 4:.1f}" font-size="11.5" font-weight="700" fill="#f59e0b">{esc(t("H4 range"))}</text>')
    # M15 entry tag in the H4 demand
    a(f'<rect x="{X(68) - 70:.1f}" y="{Y(101.6) - (0 if bull else 22):.1f}" width="140" height="22" rx="5" fill="{PU}"/>')
    a(f'<text x="{X(68):.1f}" y="{Y(101.6) + (15 if bull else -7):.1f}" font-size="12.5" font-weight="800" fill="#fff" text-anchor="middle">{esc("M15 entry confirmed")}</text>')

    # numbered steps on the chart
    STEPS = [(1, 16, 101.6, "1"), (2, 25, 101.6, "2"), (3, 42, 104.4, "3"), (4, 47, 96.5, "4"), (5, 55, 96.7, "5"),
             (6, 58, 103.0, "6"), (7, 63, 99.6, "7"), (8, 72, 113.6, "8")]
    for _, i, p, s_ in STEPS:
        up_ = s_ in ("1", "3", "6", "8")
        yy = Y(p) + ((-30 if up_ else 30) if bull else (30 if up_ else -30))
        a(f'<circle cx="{X(i):.1f}" cy="{yy:.1f}" r="12" fill="{PU}"/><text x="{X(i):.1f}" y="{yy + 5:.1f}" font-size="13" font-weight="800" fill="#fff" text-anchor="middle">{s_}</text>')

    # the story panel
    PX = 1640
    a(f'<rect x="{PX}" y="{T - 30}" width="{W - PX - 20}" height="{B - T + 50}" rx="10" fill="#f8f7fc" stroke="#e4e0f3"/>')
    a(f'<text x="{PX + 18}" y="{T}" font-size="18" font-weight="800" fill="#4c1d95">{esc(t("THE STORY (BUYS)"))}</text>')
    STORY = [
        "Daily external breakout up (the Bias Pointer's external high / low).",
        "H4 keeps breaking its external highs: continuations. A line tracks the last H4 low and moves up after each H4 BOS up: that is where the pullback would show.",
        "The last H4 low breaks: the Daily pullback is confirmed. The last high is the Daily range high; the 0.5 line splits premium and discount.",
        "The Daily levels in the discount are marked: boxes for FVGs and demand, lines for V-shapes, OCs and the Breaker. A Daily close through one removes it (an H4 close doesn't).",
        "Price reacts at one of them (here the Daily demand).",
        "The reaction gives an H4 external breakout up: tagged Daily + H4 aligned. Target: the Daily range high. The H4 range is now the Daily high ↔ the H4 low before the breakout. If that low breaks first, H4 is still bearish (a continuation down) inside the bullish Daily.",
        "Inside the H4 range the H4 levels are marked (an H4 close through one removes it). An M15 sweep and break at one: M15 entry confirmed.",
        "Price returns to the Daily high and beyond.",
    ]
    yy = T + 34
    for k, it in enumerate(STORY):
        lines_ = textwrap.wrap(t(it), 50)
        a(f'<circle cx="{PX + 28}" cy="{yy - 5}" r="11" fill="{PU}"/><text x="{PX + 28}" y="{yy}" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">{k + 1}</text>')
        for j, ln in enumerate(lines_):
            a(f'<text x="{PX + 48}" y="{yy + 16 * j}" font-size="13.2" fill="#222">{esc(ln)}</text>')
        yy += 16 * len(lines_) + 16

    # M15 inset: the sweep and break inside the H4 demand
    iy = B + 30
    ix0, ix1 = L, L + 560
    a(f'<rect x="{ix0}" y="{iy}" width="{ix1 - ix0}" height="{H - iy - 20}" rx="10" fill="#fbfbfd" stroke="#e5e7eb"/>')
    a(f'<text x="{ix0 + 14}" y="{iy + 24}" font-size="14" font-weight="800" fill="#111">{esc(t("7 · M15 inside the H4 demand: sweep and break"))}</text>')
    IW = [(0, 106), (3, 104.2), (4, 104.8), (7, 103.1), (8, 103.7), (10, 102.6), (11, 103.4), (12, 103.2), (13, 102.3), (14, 103.5), (15, 104.9), (18, 107)]
    ic = candles(IW, 7, 0.15, 0.35)
    ni = len(ic)
    idx = (ix1 - ix0 - 160) / (ni + 2)
    IX = lambda i: ix0 + 20 + idx * (i + 0.5)
    ilo, ihi = 101.6, 107.6
    itop, ibot = iy + 36, H - 34
    IY = (lambda p: ibot - (p - ilo) / (ihi - ilo) * (ibot - itop)) if bull else (lambda p: itop + (p - ilo) / (ihi - ilo) * (ibot - itop))
    z1, z2 = sorted((IY(102.0), IY(103.4)))
    a(f'<rect x="{IX(0):.1f}" y="{z1:.1f}" width="{IX(ni) - IX(0):.1f}" height="{z2 - z1:.1f}" fill="{WITH}" opacity="0.18"/>')
    a(f'<text x="{IX(ni):.1f}" y="{(z1 + z2) / 2 + 4:.1f}" font-size="11.5" font-weight="700" fill="{WITH}">{esc(t("H4 demand"))}</text>')
    for i, (op, h, l, c) in enumerate(ic):
        up = (c >= op) if bull else (c < op)
        a(f'<line x1="{IX(i):.1f}" y1="{IY(h):.1f}" x2="{IX(i):.1f}" y2="{IY(l):.1f}" stroke="#1e3a8a"/>')
        y1, y2 = sorted((IY(op), IY(c)))
        a(f'<rect x="{IX(i) - idx * 0.32:.1f}" y="{y1:.1f}" width="{idx * 0.64:.1f}" height="{max(y2 - y1, 1):.1f}" fill="{"#fff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')
    a(f'<line x1="{IX(10):.1f}" y1="{IY(102.6):.1f}" x2="{IX(13):.1f}" y2="{IY(102.6):.1f}" stroke="{AGAINST}" stroke-dasharray="3 3"/>')
    a(f'<text x="{IX(13) + 6:.1f}" y="{IY(102.6) + (14 if bull else -6):.1f}" font-size="11.5" font-weight="700" fill="{AGAINST}">{esc(t("sweep of the low"))}</text>')
    a(f'<line x1="{IX(11):.1f}" y1="{IY(103.8):.1f}" x2="{IX(15):.1f}" y2="{IY(103.8):.1f}" stroke="{WITH}" stroke-width="1.6"/>')
    a(f'<text x="{IX(15) + 6:.1f}" y="{IY(103.8) + 4:.1f}" font-size="11.5" font-weight="700" fill="{WITH}">{esc(t("break of the last lower high = M15 entry confirmed"))}</text>')

    # legend
    lx = ix1 + 30
    LEG = [("box", WITH, "FVG / demand / supply zones: boxes"), ("line", WITH, "V-shape / A-shape, OC, Breaker: lines"),
           ("line", "#0284c7", "last H4 low (pullback readiness)"), ("line", "#f59e0b", "H4 range low"),
           ("tag", G, "Daily + H4 aligned"), ("tag", PU, "M15 entry confirmed")]
    for k, (kind, col, txt) in enumerate(LEG):
        yy = iy + 30 + k * 30
        if kind == "box":
            a(f'<rect x="{lx}" y="{yy - 10}" width="34" height="16" fill="{col}" opacity="0.25" stroke="{col}"/>')
        elif kind == "line":
            a(f'<line x1="{lx}" y1="{yy - 2}" x2="{lx + 34}" y2="{yy - 2}" stroke="{col}" stroke-width="2.4"/>')
        else:
            a(f'<rect x="{lx}" y="{yy - 12}" width="34" height="18" rx="4" fill="{col}"/>')
        a(f'<text x="{lx + 44}" y="{yy + 3}" font-size="13" fill="#222">{esc(t(txt))}</text>')
    a(f'<text x="{lx}" y="{iy + 30 + 6 * 30 + 6}" font-size="13" fill="#555">{esc(t("A level dies only on a close of its own timeframe: Daily levels on a Daily close, H4 levels on an H4 close."))}</text>')
    a(f'<text x="{lx}" y="{iy + 30 + 6 * 30 + 26}" font-size="13" fill="#555">{esc("Plans: W → D → H4 · D → H4 → M15 · H4 → M15 → M5 (the same story one level up or down).")}</text>')
    a('</svg>')
    name = 'Aligned_Story_Buys' if bull else 'Aligned_Story_Sells'
    open(f'C:/Users/u/Documents/{name}.svg', 'w', encoding='utf-8').write('\n'.join(o))
    print(name, n)


build(True)
build(False)
