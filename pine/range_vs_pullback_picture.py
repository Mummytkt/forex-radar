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


# run it: pullback line (internal, the last level of the leg) + range (external)
pl_segs, rg_segs, ev = [], [], []
w = 1
pl, pli = seed(0, 0, 1)
pl_start = 0
rlo, rloi = bl(0), 0          # the range low: the low the move came from (the low that broke the last external high)
rhi, rhii = None, None        # the range high: set when a pullback confirms the top
leg0 = 0                      # first candle of the current leg
i = 1
while i < n:
    gtw = (lambda a, b: a > b) if w > 0 else (lambda a, b: a < b)
    nl, nli = seed(leg0, i, w)
    if nli > pli:
        pl_segs.append((pli, i, pl))
        pl, pli = nl, nli
        ev.append((i, 'cont', w))
    # external breaks of the range
    if rhi is not None and cl(i) > rhi:
        rg_segs.append((rloi, i, rlo, 'lo'))
        rg_segs.append((rhii, i, rhi, 'hi'))
        k = min(range(rhii, i + 1), key=bl)
        rlo, rloi = bl(k), k
        ev.append((i, 'rh_broken', rhi))
        rhi, rhii = None, None
    # the pullback line broken by a body close: the leg reverses
    if gtw(pl, cl(i)):
        pl_segs.append((pli, i, pl))
        ev.append((i, 'pb%d' % w, pl))
        k = max(range(pli, i + 1), key=bh) if w > 0 else min(range(pli, i + 1), key=bl)
        if w > 0 and rhi is None:
            rhi, rhii = bh(k), k                 # the top becomes the range high: we have a range
            ev.append((i, 'range', rhi))
        w = -w
        leg0 = k
        pl, pli = seed(leg0, i, w)
    i += 1
pl_segs.append((pli, n - 1, pl))
if rhi is not None:
    rg_segs.append((rhii, n - 1, rhi, 'hi'))
rg_segs.append((rloi, n - 1, rlo, 'lo'))

# ── drawing ──────────────────────────────────────────────────────────────────────────────────────
lo, hi = 98.5, 113.0
dx = (R - L) / (n + 2)
X = lambda i: L + dx * (i + 0.5)
Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#fff"/>',
     '<text x="60" y="52" font-size="29" font-weight="800" fill="#111">RANGE LOW / HIGH  vs  PULLBACK LINE · buys (sells mirror) · my reading, please confirm</text>',
     f'<text x="60" y="88" font-size="18" fill="#444"><tspan fill="{OR}" font-weight="800">Orange = range low / high</tspan> (moves only when an external high or low breaks).   '
     f'<tspan fill="{BL}" font-weight="800">Blue = pullback line</tspan> (the last level of the current leg).</text>']
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
    o.append(f'<line x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{OR}" stroke-width="3"/>')
    label(X(i0) + 6, Y(p), f"range {'high' if side == 'hi' else 'low'} {p:.2f}", OR, above=side == 'hi')
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


for i, kind, val in ev:
    if kind == 'pb1':
        tag(i, cs[i][2], "PL broken: pullback confirmed · we have a range", RD, below=True)
    elif kind == 'pb-1':
        tag(i, cs[i][1], "PL broken: pullback over · back with the Daily", G)
    elif kind == 'rh_broken':
        tag(i, cs[i][1] + 0.9, "range high broken (external) · range low moves up", G)
o.append(f'<text x="{X(n) + 10:.1f}" y="{Y(lo + 0.6):.1f}" font-size="13" fill="{GR}">PL0 = the start</text>')

# the rule panel
PX = 1700
o.append(f'<rect x="{PX - 24}" y="120" width="{W - PX + 4}" height="1140" rx="14" fill="#f8fafc" stroke="#e2e8f0"/>')
notes = [
    ("THE TWO LEVELS", None),
    ("Range low (orange)", "The low that broke the last EXTERNAL high. It stays while we keep breaking highs inside the leg. It moves only when the range high (an external high) breaks: then to the low that broke it."),
    ("Range high (orange)", "The top of the leg, once a pullback confirms it. Price plays inside the range until one side breaks."),
    ("Pullback line (blue)", "The last level formed in the current leg: the last low that broke a high inside the leg (sells: the last high that broke a low). It steps with every high broken in the leg."),
    ("A real pullback", "The level only counts after a proper reversal (a body closed back beyond the body of the candle that made the high). One small candle is not a pullback."),
    ("Pullback confirmed", "A body close beyond the pullback line = a proper break of structure: the pullback is confirmed and we have the range."),
    ("Inside the bearish pullback", "The pullback line is the last high that broke a low: the candle that broke the low pulled back first. A close above it = the pullback is over, back with the Daily."),
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
