"""Range low/high vs pullback line (user, 2026-11-03): two different levels, drawn for confirmation.
Buys (sells mirror), story-timeframe candles, body levels, body closes. Both lines are computed by the rule
on the drawn candles. Output: Documents/Range_vs_Pullback.svg (+ PNG)."""
import html
import random

esc = html.escape
W, H = 2200, 1300
L, R, T, B = 60, 1560, 130, 1060
BL, OR, G, RD, GR, INK = "#0284c7", "#ea580c", "#16a34a", "#dc2626", "#6b7280", "#111827"

WAY = [(0, 100.0), (3, 104.2), (4, 103.6), (6, 102.4), (9, 106.2), (10, 105.6), (12, 104.8), (15, 108.3),
       (16, 107.8), (18, 107.0), (21, 110.2), (23, 108.4), (25, 109.2), (28, 106.4), (30, 107.6), (33, 104.4),
       (35, 105.6), (38, 103.0), (40, 105.9), (43, 108.2), (44, 107.6), (46, 106.7), (50, 111.6)]


def candles(way, seed=4, noise=0.10, wick=0.35):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for i in range(a, b):
            path.append(pa + (pb - pa) * (i - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 0.4
    for p in path:
        o, c = prev, p + random.uniform(-noise, noise)
        out.append((o, max(o, c) + random.uniform(0.08, wick), min(o, c) - random.uniform(0.08, wick), c))
        prev = c
    return out


cs = candles(WAY)
n = len(cs)
bh = lambda i: max(cs[i][0], cs[i][3])
bl = lambda i: min(cs[i][0], cs[i][3])
cl = lambda i: cs[i][3]


def seed(i0, i1, w):
    """the pullback-line rule over candles i0..i1 in direction w: returns (line, line_i, ext, ext_i, eo, fm, dip, dip_i)"""
    top = bh if w > 0 else bl
    far = bl if w > 0 else bh
    gt = (lambda a, b: a > b) if w > 0 else (lambda a, b: a < b)
    ln, li = far(i0), i0
    ex, ei, eo, fm, dp, di = top(i0), i0, far(i0), False, None, None
    for j in range(i0 + 1, i1 + 1):
        if fm and gt(cl(j), ex):
            if dp is None or gt(dp, far(j)):
                dp, di = far(j), j
            ln, li = dp, di
            ex, ei, eo, fm, dp, di = top(j), j, far(j), False, None, None
        elif gt(top(j), ex):
            ex, ei, eo, fm, dp, di = top(j), j, far(j), False, None, None
        else:
            if gt(eo, cl(j)):
                fm = True
            if dp is None or gt(dp, far(j)):
                dp, di = far(j), j
    return ln, li


# run it. Each leg keeps its list of pullback lines (every low that broke a high, sells: every high that
# broke a low). The pullback line = the LAST one; the trailing range edge = the one BEFORE it (the low price
# must take after the pullback line to confirm the range). A body close beyond the pullback line = pullback
# confirmed: range edge on the far side = the extreme before the break (the top), the near side = the one before.
pl_segs, rg_segs, ev = [], [], []
w = 1
leg0 = 0
pl, pli = seed(0, 0, 1)
edge, edgei = pl, pli          # the trailing range edge (buys: range low)
prev_pl, prev_pli = None, None
fixed = []                     # range edges fixed at a pullback confirmation: (i0, value, side, from_i)
i = 1
while i < n:
    gtw = (lambda a, b: a > b) if w > 0 else (lambda a, b: a < b)
    nl, nli = seed(leg0, i, w)
    if nli > pli:
        pl_segs.append((pli, i, pl))
        # the old pullback line becomes the trailing range edge
        rg_segs.append((edgei, i, edge, 'lo' if w > 0 else 'hi'))
        edge, edgei = pl, pli
        pl, pli = nl, nli
        ev.append((i, 'step', w))
    if gtw(pl, cl(i)):
        pl_segs.append((pli, i, pl))
        rg_segs.append((edgei, i, edge, 'lo' if w > 0 else 'hi'))
        k = max(range(pli, i + 1), key=bh) if w > 0 else min(range(pli, i + 1), key=bl)
        far = bh(k) if w > 0 else bl(k)
        ev.append((i, 'pb%d' % w, pl, far, edge, k, edgei))
        fixed.append((k, i, far, 'hi' if w > 0 else 'lo'))
        fixed.append((edgei, i, edge, 'lo' if w > 0 else 'hi'))
        w = -w
        leg0 = k
        pl, pli = seed(leg0, i, w)
        edge, edgei = far, k     # the new leg's trailing edge starts at the extreme
    i += 1
pl_segs.append((pli, n - 1, pl))
rg_segs.append((edgei, n - 1, edge, 'lo' if w > 0 else 'hi'))

# ── drawing ──────────────────────────────────────────────────────────────────────────────────────
lo, hi = 98.5, 113.0
dx = (R - L) / (n + 2)
X = lambda i: L + dx * (i + 0.5)
Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#fff"/>',
     '<text x="60" y="52" font-size="29" font-weight="800" fill="#111">PULLBACK LINE AND RANGE LOW · your explanation, as I understand it</text>',
     f'<text x="60" y="88" font-size="18" fill="#444"><tspan fill="{OR}" font-weight="800">Orange dashed = the range low waiting</tspan> (the pullback line BEFORE the last one).   '
     f'<tspan fill="{BL}" font-weight="800">Blue = pullback line</tspan> (the LAST low that broke a high).  Thick orange = the range once the pullback is confirmed.</text>']
for i, (op, h, l, c) in enumerate(cs):
    col = "#2563eb" if c >= op else "#6b7280"
    y1, y2 = sorted((Y(op), Y(c)))
    o.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}" stroke-width="1.5"/>')
    o.append(f'<rect x="{X(i) - dx * .32:.1f}" y="{y1:.1f}" width="{dx * .64:.1f}" height="{max(y2 - y1, 1.6):.1f}" fill="{col}" rx="1.5"/>')


def label(x, y, txt, col, above=True):
    w_ = 14 + len(txt) * 7.6
    yy = y - 27 if above else y + 6
    o.append(f'<rect x="{x:.1f}" y="{yy:.1f}" width="{w_:.1f}" height="22" rx="5" fill="{col}"/>')
    o.append(f'<text x="{x + 7:.1f}" y="{yy + 16:.1f}" font-size="14" font-weight="800" fill="#fff">{esc(txt)}</text>')


for i0, i1, p, side in rg_segs:
    o.append(f'<line x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{OR}" stroke-width="2" stroke-dasharray="8 5"/>')
for k0, i1, p, side in fixed:
    o.append(f'<line x1="{X(i1):.1f}" x2="{X(n):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{OR}" stroke-width="3.4"/>')
    label(X(n) - 190, Y(p), f"range {'high' if side == 'hi' else 'low'} {p:.2f}", OR, above=side == 'hi')
for k, (i0, i1, p) in enumerate(pl_segs, 1):
    o.append(f'<line x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{BL}" stroke-width="2.6"/>')
    o.append(f'<circle cx="{X(i0):.1f}" cy="{Y(p):.1f}" r="5.5" fill="#fff" stroke="{BL}" stroke-width="2.2"/>')
    if k > 1:
        label(X(i0) + 8, Y(p), f"PL{k - 1} {p:.2f}", BL, above=True)


def tag(i, p, txt, col, below=False):
    w_ = 18 + len(txt) * 7.6
    x0 = min(X(i) - w_ / 2, R + 40 - w_)
    y0 = Y(p) + 16 if below else Y(p) - 46
    o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_:.1f}" height="28" rx="6" fill="{col}"/>')
    o.append(f'<text x="{x0 + w_ / 2:.1f}" y="{y0 + 19:.1f}" font-size="14.5" font-weight="800" fill="#fff" text-anchor="middle">{esc(txt)}</text>')


for e in ev:
    if e[1] == 'pb1':
        tag(e[0], cs[e[0]][2], "PL3 broken: pullback confirmed · range = PL2 ... the top", RD, below=True)
    elif e[1] == 'pb-1':
        tag(e[0], cs[e[0]][1] + 0.4, "PL6 broken (sells mirror?): range = the bottom ... PL5", G)
o.append(f'<text x="{X(n) + 10:.1f}" y="{Y(lo + 0.6):.1f}" font-size="13" fill="{GR}">PL0 = the start</text>')

# the rule panel
PX = 1700
o.append(f'<rect x="{PX - 24}" y="120" width="{W - PX + 4}" height="1140" rx="14" fill="#f8fafc" stroke="#e2e8f0"/>')
notes = [
    ("AS I UNDERSTAND IT (buys)", None),
    ("Pullback line (blue)", "The LAST low that broke a high. Every new high made from a new low moves it to that low (PL1, PL2, PL3). Internal lows that broke a high count too, so the line steps faster when there are some."),
    ("Range low waiting (orange dashed)", "The pullback line BEFORE the last one. When PL2 makes a new high, PL1 becomes the range low. When PL3 makes a new high, PL2 becomes the range low."),
    ("Why", "Once the pullback line is taken out, the high before that break is the range high, and the range low is the low price must take next: the previous pullback line."),
    ("Pullback confirmed", "A body close below PL3 = the pullback is confirmed: range high = the immediate high before the break (the top), range low = PL2."),
    ("Sells (mirror)", "The same in the bearish leg: pullback line = the last high that broke a low (PL4, PL5, PL6), the one before it waits as the range high. I drew the bearish leg this way too: please check that part."),
]
yy = 160
for head, body in notes:
    o.append(f'<text x="{PX}" y="{yy}" font-size="{19 if body is None else 16}" font-weight="800" fill="{OR if head.startswith("Range") else BL if head.startswith(("Pullback", "A real", "Inside")) else INK}">{esc(head)}</text>')
    yy += 26
    if body:
        words, line_, lines = body.split(), "", []
        for w_ in words:
            if len(line_) + len(w_) > 46:
                lines.append(line_)
                line_ = w_
            else:
                line_ = (line_ + " " + w_).strip()
        lines.append(line_)
        for ln in lines:
            o.append(f'<text x="{PX}" y="{yy}" font-size="15.5" fill="#1f2937">{esc(ln)}</text>')
            yy += 21
        yy += 16
o.append('</svg>')
open("C:/Users/u/Documents/Range_vs_Pullback.svg", "w", encoding="utf-8").write("\n".join(o))
print("events", [(e[0], e[1], round(e[2], 2) if isinstance(e[2], float) else e[2]) for e in ev])
print("pl", [(a, b, round(p, 2)) for a, b, p in pl_segs])
print("rg", [(a, b, round(p, 2), s) for a, b, p, s in rg_segs])
