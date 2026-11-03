"""The pullback line through the whole story (user, 2026-11-03), drawn for confirmation BEFORE any code change.
Buys (sells mirror). H4 candles, body levels, body closes. The lines are computed by the rule itself
(a simulation on the drawn candles), so the picture shows exactly what the script would do.
Output: Documents/Pullback_Flow.svg (+ PNG)."""
import html
import random

esc = html.escape
W, H = 2200, 1250
L, R, T, B = 60, 1500, 120, 1010
G, RD, BL, OR, GR, INK = "#16a34a", "#dc2626", "#0284c7", "#ea580c", "#6b7280", "#111827"

WAY = [(0, 95.5), (2, 97.2), (4, 101.5), (6, 106.0), (7, 104.6), (8, 105.3), (10, 102.8), (13, 108.2),
       (14, 110.0), (15, 108.2), (16, 108.9), (18, 107.2), (21, 113.4), (22, 114.6), (24, 111.2), (25, 112.1),
       (28, 106.0), (29, 105.4), (31, 108.4), (34, 103.9), (35, 103.4), (37, 106.2), (40, 101.4),
       (41, 101.1), (44, 107.4), (45, 108.3), (47, 105.6), (50, 110.4), (51, 111.0)]


def candles(way, seed=21, noise=0.12, wick=0.4):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for i in range(a, b):
            path.append(pa + (pb - pa) * (i - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 0.4
    for p in path:
        o, c = prev, p + random.uniform(-noise, noise)
        out.append((o, max(o, c) + random.uniform(0.1, wick), min(o, c) - random.uniform(0.1, wick), c))
        prev = c
    return out


cs = candles(WAY)
n = len(cs)
bh = lambda i: max(cs[i][0], cs[i][3])
bl = lambda i: min(cs[i][0], cs[i][3])
cl = lambda i: cs[i][3]

# ── the rule, run on the candles ────────────────────────────────────────────────────────────────
# direction w; ext = the leg's top (w>0) since the line; formed = price pulled back from it (a candle body
# closed below the body of the candle that made the top); line = the low that broke the last high.
# close beyond a FORMED top = continuation: line -> the lowest point between that top and the break.
# close beyond the line = flip: line -> the leg's extreme (the high that broke the low), w flips.
OLD_HI = 98.8                    # the Daily external high that breaks (Daily breakout)
D_LO = min(cs[i][2] for i in range(3))
w, ext, ext_i, formed = 1, bh(0), 0, False
line, line_i = bl(0), 0
segs, events = [], []            # segs: (i0, i1, price, kind)  events: (i, kind, price)
flips = 0
for i in range(1, n):
    gt = (lambda a, b: a > b) if w > 0 else (lambda a, b: a < b)
    top_body = bh if w > 0 else bl
    low_body = bl if w > 0 else bh
    if gt(cl(i), ext) and formed:
        # continuation: the low that broke the high becomes the line
        k = min(range(ext_i + 1, i + 1), key=low_body) if w > 0 else max(range(ext_i + 1, i + 1), key=low_body)
        segs.append((line_i, i, line, 'line'))
        line, line_i = low_body(k), k
        events.append((i, 'cont', ext, ext_i))
        ext, ext_i, formed = top_body(i), i, False
        continue
    if gt(top_body(i), ext):
        ext, ext_i, formed = top_body(i), i, False
    elif gt(low_body(ext_i), cl(i)):
        formed = True            # a body closed back beyond the body of the top candle: a real pullback
    if gt(line, cl(i)):
        # flip: the high that broke the low becomes the line
        segs.append((line_i, i, line, 'line'))
        flips += 1
        events.append((i, 'flip%d' % flips, line, line_i))
        k = max(range(line_i, i + 1), key=top_body) if w > 0 else min(range(line_i, i + 1), key=top_body)
        w = -w
        line, line_i = (bh(k) if w < 0 else bl(k)), k
        ext, ext_i, formed = (bl(i) if w < 0 else bh(i)), i, False
segs.append((line_i, n - 1, line, 'line'))

# ── drawing ──────────────────────────────────────────────────────────────────────────────────────
lo, hi = 93.5, 117.5
dx = (R - L) / (n + 2)
X = lambda i: L + dx * (i + 0.5)
Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
     '<text x="60" y="52" font-size="29" font-weight="800" fill="#111">THE PULLBACK LINE THROUGH THE WHOLE STORY · buys (sells are the mirror) · my reading, please confirm</text>',
     '<text x="60" y="86" font-size="17" fill="#444">H4 candles, levels on bodies, breaks are body closes. Blue = the pullback line at each moment (it only steps when a HIGH or the LINE breaks).</text>']

flip1 = next(e for e in events if e[1] == 'flip1')
flip2 = next((e for e in events if e[1] == 'flip2'), None)
TOP = max(bh(i) for i in range(flip1[3], flip1[0] + 1))
MID = (TOP + D_LO) / 2
# Daily range + premium / discount from the Daily pullback on
o.append(f'<rect x="{X(flip1[0]):.1f}" y="{Y(TOP):.1f}" width="{X(n) - X(flip1[0]):.1f}" height="{Y(MID) - Y(TOP):.1f}" fill="{RD}" opacity="0.05"/>')
o.append(f'<rect x="{X(flip1[0]):.1f}" y="{Y(MID):.1f}" width="{X(n) - X(flip1[0]):.1f}" height="{Y(D_LO) - Y(MID):.1f}" fill="{G}" opacity="0.05"/>')
for p, tx, col, d in ((TOP, "Daily range high", INK, ""), (MID, "Daily 0.5 · premium above / discount below", GR, ' stroke-dasharray="8 6"'),
                      (D_LO, "Daily external low", INK, "")):
    x0 = X(flip1[0]) if p != D_LO else X(0)
    o.append(f'<line x1="{x0:.1f}" x2="{X(n):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="1.6"{d}/>')
    o.append(f'<text x="{X(n) + 10:.1f}" y="{Y(p) + 5:.1f}" font-size="14" font-weight="700" fill="{col}">{esc(tx)}</text>')
o.append(f'<line x1="{X(0):.1f}" x2="{X(3):.1f}" y1="{Y(OLD_HI):.1f}" y2="{Y(OLD_HI):.1f}" stroke="{INK}" stroke-width="1.6"/>')
# H4 range after the realignment
if flip2:
    RLO = min(bl(i) for i in range(flip2[3], flip2[0] + 1))
    o.append(f'<rect x="{X(flip2[0]):.1f}" y="{Y(TOP):.1f}" width="{X(n) - X(flip2[0]):.1f}" height="{Y(RLO) - Y(TOP):.1f}" fill="{OR}" opacity="0.07"/>')
    o.append(f'<line x1="{X(flip2[0]):.1f}" x2="{X(n):.1f}" y1="{Y(RLO):.1f}" y2="{Y(RLO):.1f}" stroke="{OR}" stroke-width="2.2"/>')
    o.append(f'<text x="{X(n) + 10:.1f}" y="{Y(RLO) + 22:.1f}" font-size="14" font-weight="700" fill="{OR}">H4 range low</text>')
    o.append(f'<text x="{X(n) + 10:.1f}" y="{Y(TOP) + 22:.1f}" font-size="14" font-weight="700" fill="{OR}">= H4 range high</text>')
# candles
for i, (op, h, l, c) in enumerate(cs):
    col = "#2563eb" if c >= op else "#6b7280"
    y1, y2 = sorted((Y(op), Y(c)))
    o.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}" stroke-width="1.4"/>')
    o.append(f'<rect x="{X(i) - dx * .32:.1f}" y="{y1:.1f}" width="{dx * .64:.1f}" height="{max(y2 - y1, 1.5):.1f}" fill="{col}" rx="1"/>')
# the pullback line, step by step
for i0, i1, p, _ in segs:
    o.append(f'<line x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{BL}" stroke-width="3"/>')
    o.append(f'<circle cx="{X(i0):.1f}" cy="{Y(p):.1f}" r="6" fill="#fff" stroke="{BL}" stroke-width="2.4"/>')


def tag(i, p, tx, col, below=False):
    w_ = 16 + len(tx) * 7.4
    x0 = X(i) - w_ / 2
    y0 = Y(p) + 14 if below else Y(p) - 40
    o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_:.1f}" height="26" rx="6" fill="{col}"/>')
    o.append(f'<text x="{X(i):.1f}" y="{y0 + 18:.1f}" font-size="14" font-weight="800" fill="#fff" text-anchor="middle">{esc(tx)}</text>')


def num(i, p, k):
    o.append(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="15" fill="#111"/><text x="{X(i):.1f}" y="{Y(p) + 5.5:.1f}" font-size="16" font-weight="800" fill="#fff" text-anchor="middle">{k}</text>')


iDB = next(i for i in range(n) if cl(i) > OLD_HI)
tag(iDB, cs[iDB][1], "Daily bullish breakout", INK)
num(iDB - 2, OLD_HI + 2.5, 1)
k = 2
for (i, kind, lvl, li) in events:
    if kind == 'cont':
        o.append(f'<line x1="{X(li):.1f}" x2="{X(i):.1f}" y1="{Y(lvl):.1f}" y2="{Y(lvl):.1f}" stroke="{G if i < flip1[0] or (flip2 and i > flip2[0]) else RD}" stroke-width="1.4" stroke-dasharray="4 4"/>')
        up = not (flip1[0] < i < (flip2[0] if flip2 else n))
        o.append(f'<text x="{(X(li) + X(i)) / 2:.1f}" y="{Y(lvl) + (-8 if up else 20):.1f}" font-size="13" font-weight="700" fill="{G if up else RD}" text-anchor="middle">{"H4 bullish cont" if up else "H4 bearish cont"}</text>')
tag(flip1[0], cs[flip1[0]][2], "Pullback break · Daily pullback confirmed", RD, below=True)
if flip2:
    tag(flip2[0], cs[flip2[0]][1], "H4 pullback · back in alignment with Daily", G)

# numbered steps on the chart
first_cont = next(e for e in events if e[1] == 'cont')
num(first_cont[0] + 1, first_cont[2] + 3.0, 2)
num(flip1[0] + 2, flip1[2] - 2.6, 3)
bear_conts = [e for e in events if e[1] == 'cont' and flip1[0] < e[0] < (flip2[0] if flip2 else n)]
if bear_conts:
    num(bear_conts[0][0] + 1, bear_conts[0][2] - 3.2, 4)
if flip2:
    num(flip2[0] + 1, flip2[2] - 2.6, 5)
    after = [e for e in events if e[1] == 'cont' and e[0] > flip2[0]]
    if after:
        num(after[0][0] + 1, after[0][2] + 3.0, 6)

# the story panel
PX = 1700
o.append(f'<rect x="{PX - 24}" y="110" width="{W - PX + 4}" height="1110" rx="14" fill="#f8fafc" stroke="#e2e8f0"/>')
o.append(f'<text x="{PX}" y="148" font-size="20" font-weight="800" fill="#111">THE RULE</text>')
notes = [
    ("1", "Daily breakout. H4 runs with it."),
    ("2", "In a bullish move lows break highs. The pullback line is the low that broke the last high. Until that high breaks, the low stands; everything inside is inconsequential. When the high breaks, the line moves to the low that broke it."),
    ("3", "An H4 close below the pullback line = the Daily pullback is confirmed. The Daily range is set (premium / discount). The new pullback line is the last high that broke that low: the top of the leg."),
    ("4", "While breaks down continue, the line moves to the highest point of the leg that broke the low."),
    ("5", "An H4 close above that line = back in alignment with the Daily, the H4 range. The new pullback line is the last low that broke the high to flip us bullish again (the H4 range low)."),
    ("6", "From here it repeats: each high broken moves the line up to the low that broke it."),
    ("?", "A tiny pause in a run is not a high: a high counts once a candle body closes back below the body of the candle that made it (a real pullback). Is that right?"),
]
yy = 186
for kk, s in notes:
    q = kk == "?"
    o.append(f'<circle cx="{PX + 10}" cy="{yy - 6}" r="13" fill="{"#b45309" if q else "#111"}"/><text x="{PX + 10}" y="{yy - 0.5}" font-size="14" font-weight="800" fill="#fff" text-anchor="middle">{kk}</text>')
    words, line_, lines = s.split(), "", []
    for w_ in words:
        if len(line_) + len(w_) > 40:
            lines.append(line_)
            line_ = w_
        else:
            line_ = (line_ + " " + w_).strip()
    lines.append(line_)
    for j, ln in enumerate(lines):
        o.append(f'<text x="{PX + 34}" y="{yy + j * 21}" font-size="15.5" fill="{"#92400e" if q else "#1f2937"}">{esc(ln)}</text>')
    yy += len(lines) * 21 + 22
o.append('</svg>')
open("C:/Users/u/Documents/Pullback_Flow.svg", "w", encoding="utf-8").write("\n".join(o))
print("ok events", [(e[0], e[1], round(e[2], 2)) for e in events])
