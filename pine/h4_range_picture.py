"""MTF Storyline: the H4 range after the Daily pullback, as the user explained it (2026-11-02).
Drawn BEFORE any code change, for the user's confirmation. Buys (sells mirror).
Output: Documents/MTF_H4_Range_Buys.svg (+ PNG)."""
import html
import random

W, H = 2240, 1120
L, R, T, B = 60, 1380, 110, 860
esc = html.escape
WAY = [(0, 88), (3, 94), (5, 92), (8, 98.5), (10, 97), (13, 101.5), (15, 100.3), (18, 104.5), (20, 103.4),
       (24, 112), (26, 109.5), (27, 110.4), (31, 103), (33, 105.8), (34, 104.6), (36, 107.4), (38, 104.4),
       (40, 106.6), (42, 105.2), (45, 108.6), (47, 106.2), (50, 100.6), (52, 102.6), (53, 101.8), (56, 106.4),
       (58, 104.8), (62, 113.6), (66, 116)]


def candles(way, seed, noise=0.12, wick=0.5):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for i in range(a, b):
            path.append(pa + (pb - pa) * (i - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 0.6
    for p in path:
        o, c = prev, p + random.uniform(-noise, noise)
        out.append((o, max(o, c) + random.uniform(0.15, wick), min(o, c) - random.uniform(0.15, wick), c))
        prev = c
    return out


cs = candles(WAY, 5)
n = len(cs)
lo, hi = 85, 118
dx = (R - L) / (n + 3)
X = lambda i: L + dx * (i + 0.5)
Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
hh = lambda i: cs[i][1]
ll = lambda i: cs[i][2]
HI_ = lambda a, b: max(range(a, b + 1), key=hh)
LO_ = lambda a, b: min(range(a, b + 1), key=ll)
first = lambda i0, f: next(i for i in range(i0, n) if f(cs[i][3]))
G, RD, BL, OR, PU = "#16a34a", "#dc2626", "#0284c7", "#ea580c", "#7c3aed"
o = []
a = o.append


def txt(x, y, s, col, size=12, anchor="start", bold=True):
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col}" text-anchor="{anchor}">{esc(s)}</text>')


def hl(i0, i1, p, col, dash="", w=1.8, op=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{w}" opacity="{op}"{d}/>')


def tag(i, p, s, col, below=False):
    w_ = 10 + len(s) * 7.3
    x, y = X(i) - w_ / 2, Y(p) + (14 if below else -34)
    a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="22" rx="5" fill="{col}"/>')
    a(f'<text x="{X(i):.1f}" y="{y + 15.5:.1f}" font-size="12.5" font-weight="800" fill="#fff" text-anchor="middle">{esc(s)}</text>')


def step(i, p, k, q=False):
    a(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="12" fill="{"#b45309" if q else "#111"}"/><text x="{X(i):.1f}" y="{Y(p) + 4.5:.1f}" font-size="13" font-weight="800" fill="#fff" text-anchor="middle">{"?" if q else k}</text>')


a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif"><rect width="{W}" height="{H}" fill="#fff"/>')
txt(L, 46, "MTF STORYLINE · THE H4 RANGE AFTER THE DAILY PULLBACK · BUYS (my reading, please confirm)", "#111", 26)
txt(L, 76, "H4 candles. Breaks are body closes. Orange circles with ? = the points I need you to confirm.", "#444", 16, bold=False)

iTOP = HI_(22, 26); TOP = hh(iTOP)
iPL = LO_(25, 27)                                   # the last low that made a new high (pullback line)
iPB = first(iTOP + 1, lambda c: c < ll(iPL))         # Pullback break
iRL = LO_(iPB, 32)                                   # the drop's low = H4 range low
iCF = first(iRL + 1, lambda c: c > hh(HI_(iRL - 3, iRL)))   # the first H4 break up after it (confirms the low)
iB2 = first(36, lambda c: c < ll(iRL))               # the range low broken
iRL2 = LO_(iB2, 51)
iDC = first(56, lambda c: c > TOP)                   # the range high broken: Daily continues

# candles
for i, (op, h, l, c) in enumerate(cs):
    up = c >= op
    a(f'<line x1="{X(i):.1f}" y1="{Y(h):.1f}" x2="{X(i):.1f}" y2="{Y(l):.1f}" stroke="#1e3a8a" stroke-width="1.1"/>')
    y1, y2 = sorted((Y(op), Y(c)))
    a(f'<rect x="{X(i) - dx * 0.32:.1f}" y="{y1:.1f}" width="{dx * 0.64:.1f}" height="{max(y2 - y1, 1.3):.1f}" fill="{"#ffffff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')

# 1 Daily breakout + the pullback line (as now)
tag(8, hh(8) + 0.4, "Daily bullish breakout", "#111")
hl(iPL, iPB, ll(iPL), BL, "", 2.6)
txt(X(iPL) - 6, Y(ll(iPL)) + 16, "pullback line: the last H4 low that made a new high", BL, 11.5, "end")
step(15, 97.5, 1)
# 2 Pullback break = the H4 pullback (a bearish breakout on H4): the Daily pulls back, the H4 range is set
tag(iPB - 12, 110.5, "Pullback break · Daily pullback · H4 range set", RD)
a(f'<line x1="{X(iPB - 7):.1f}" y1="{Y(110.5) - 12:.1f}" x2="{X(iPB):.1f}" y2="{Y(ll(iPB)):.1f}" stroke="{RD}" stroke-width="1.2"/>')
step(iPB + 1, ll(iPB + 1) - 3.6, 2)
# the H4 range: high = the Daily range high (stays); low = the drop's low
ya, yb = Y(TOP), Y(ll(iRL))
a(f'<rect x="{X(iTOP):.1f}" y="{ya:.1f}" width="{X(iB2) - X(iTOP):.1f}" height="{yb - ya:.1f}" fill="{OR}" opacity="0.06"/>')
hl(iTOP, n, TOP, "#111", "", 2.2)
txt(X(n) + 8, Y(TOP) + 4, "Daily range high = H4 range high (stays)", "#111", 12)
hl(iRL, iB2, ll(iRL), OR, "", 2.4)
txt(X(iRL) + 4, Y(ll(iRL)) + 16, "H4 range low (the drop's low)", OR, 11.5)
step(iRL, ll(iRL) - 3.4, 3, q=True)
txt(X(iRL) + 4, Y(ll(iRL)) + 33, "? fixed once the first H4 External break up confirms it", "#b45309", 11.5)
# 4 inside the range: only the cont breaks are tracked, no lines move
for (i0, i1, p, s_, col) in ((34, 36, hh(HI_(33, 34)), "H4 bullish cont", G), (38, 40, None, "H4 bearish cont", RD), (42, 45, None, "H4 bullish cont", G)):
    pass
hl(HI_(32, 34), 36, hh(HI_(32, 34)), G, "3 3", 1.4)
txt((X(HI_(32, 34)) + X(36)) / 2, Y(hh(HI_(32, 34))) - 6, "H4 bullish cont", G, 11, "middle")
hl(LO_(37, 39), 41, ll(LO_(37, 39)) + 0.6, RD, "3 3", 1.4)
txt((X(LO_(37, 39)) + X(41)) / 2, Y(ll(LO_(37, 39)) + 0.6) + 15, "H4 bearish cont", RD, 11, "middle")
hl(HI_(39, 41), 45, hh(HI_(39, 41)), G, "3 3", 1.4)
txt((X(HI_(39, 41)) + X(45)) / 2, Y(hh(HI_(39, 41))) - 6, "H4 bullish cont", G, 11, "middle")
step(29, 110.2, 4)
txt(X(30), Y(110.6), "inside the range: just the H4 cont breaks, the range does not move", "#555", 11.5, bold=False)
# 5 the range low broken: the H4 bearish move is still in play
hl(iRL, iB2, ll(iRL), RD, "3 3", 1.6)
tag(iB2 - 7, ll(iB2) - 4.0, "H4 range low broken · H4 bearish still in play", RD, below=True)
step(iB2 - 1, ll(iB2) - 1.4, 5)
hl(iRL2, iDC, ll(iRL2), OR, "6 4", 2.2)
txt(X(iRL2) + 6, Y(ll(iRL2)) + 18, "? new H4 range low (the new drop's low), the high still stays", "#b45309", 11.5)
step(iRL2 + 1, ll(iRL2) - 4.6, 6, q=True)
# 7 the range high broken: the Daily continues
tag(iDC, hh(iDC) + 0.6, "H4 range high broken · Daily continues bullish", G)
step(iDC + 2, TOP - 3.0, 7)

# the story
PX = 1880
a(f'<rect x="{PX - 20}" y="96" width="{W - PX}" height="990" rx="12" fill="#f8f7ff" stroke="#ddd6fe"/>')
txt(PX, 128, "MY READING (BUYS)", "#4c1d95", 18)
notes = [
    ("1", "Daily breakout. H4 with it: H4 bullish cont breaks; the pullback line = the last H4 low that made a new high (as now, you said it is right)."),
    ("2", "An H4 close below the pullback line = Pullback break: the Daily pulls back and that is the H4 pullback (a bearish breakout on H4). The H4 range is set now."),
    ("?", "H4 range high = the Daily range high, it stays. H4 range low = the low of the drop, fixed once the first H4 External break up confirms it (instead of moving with each new low)."),
    ("4", "Inside the range nothing moves: only H4 bullish / bearish cont breaks are marked."),
    ("5", "A close below the H4 range low = the H4 bearish move is still in play."),
    ("?", "Then the new H4 range low = the new drop's low (confirmed the same way), the high still stays."),
    ("7", "A close above the H4 range high = the Daily continues: the next Daily breakout starts the story again."),
]
yy = 166
for k, s_ in notes:
    q = k == "?"
    a(f'<circle cx="{PX + 10}" cy="{yy - 5}" r="11" fill="{"#b45309" if q else "#111"}"/><text x="{PX + 10}" y="{yy - 0.5}" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">{k}</text>')
    words, line_, lines = s_.split(), "", []
    for w_ in words:
        if len(line_) + len(w_) > 40:
            lines.append(line_)
            line_ = w_
        else:
            line_ = (line_ + " " + w_).strip()
    lines.append(line_)
    for j, ln in enumerate(lines):
        a(f'<text x="{PX + 30}" y="{yy + j * 17}" font-size="13" fill="{"#92400e" if q else "#222"}">{esc(ln)}</text>')
    yy += len(lines) * 17 + 18
a('</svg>')
open("C:/Users/u/Documents/MTF_H4_Range_Buys.svg", "w", encoding="utf-8").write('\n'.join(o))
print("ok")
