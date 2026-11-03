"""What a pullback is (user, 2026-11-03, EURUSD M15 30-31 Dec 2019, plan H4-M15-M5): my reading drawn for the
user's confirmation BEFORE any code change. Buys (sells mirror). Output: Documents/Pullback_Definition.svg (+ PNG)."""
import html
import random

esc = html.escape
PW, PH = 1060, 470              # one panel
W, H = PW * 2 + 60, PH * 2 + 150
G, RD, BL, OR, GR = "#16a34a", "#dc2626", "#0284c7", "#ea580c", "#6b7280"


def candles(way, seed, noise=0.10, wick=0.35):
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


def panel(ox, oy, title, sub, way, seed, marks, verdict, vcol):
    cs = candles(way, seed)
    n = len(cs)
    lo = min(c[2] for c in cs) - 1.5
    hi = max(c[1] for c in cs) + 2.2
    L, R, T, B = ox + 30, ox + PW - 250, oy + 92, oy + PH - 30
    dx = (R - L) / (n + 1)
    X = lambda i: L + dx * (i + 0.5)
    Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
    o = [f'<rect x="{ox}" y="{oy}" width="{PW}" height="{PH}" rx="14" fill="#fff" stroke="#e5e7eb"/>',
         f'<text x="{ox + 24}" y="{oy + 38}" font-size="21" font-weight="800" fill="#111">{esc(title)}</text>',
         f'<text x="{ox + 24}" y="{oy + 64}" font-size="14.5" fill="#444">{esc(sub)}</text>']
    for i, (op, h, l, c) in enumerate(cs):
        up = c >= op
        col = "#2563eb" if up else "#6b7280"
        y1, y2 = sorted((Y(op), Y(c)))
        o.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}" stroke-width="1.3"/>')
        o.append(f'<rect x="{X(i) - dx * .32:.1f}" y="{y1:.1f}" width="{dx * .64:.1f}" height="{max(y2 - y1, 1.4):.1f}" fill="{col}" rx="1"/>')
    hb = lambda i: max(cs[i][0], cs[i][3])
    lb = lambda i: min(cs[i][0], cs[i][3])
    for m in marks:
        k = m[0]
        if k == 'line':          # ('line', i0, i1, price-fn, colour, text, dash)
            _, i0, i1, pf, col, tx, dash = m
            p = pf(hb, lb)
            d = ' stroke-dasharray="7 5"' if dash else ''
            o.append(f'<line x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="2.4"{d}/>')
            o.append(f'<text x="{X(i1) + 8:.1f}" y="{Y(p) + 5:.1f}" font-size="13.5" font-weight="700" fill="{col}">{esc(tx)}</text>')
        elif k == 'note':        # ('note', i, price-fn, text, colour, dy)
            _, i, pf, tx, col, dy = m
            p = pf(hb, lb)
            o.append(f'<text x="{X(i):.1f}" y="{Y(p) + dy:.1f}" font-size="13" font-weight="700" fill="{col}" text-anchor="middle">{esc(tx)}</text>')
        elif k == 'dot':
            _, i, pf, col = m
            o.append(f'<circle cx="{X(i):.1f}" cy="{Y(pf(hb, lb)):.1f}" r="7" fill="none" stroke="{col}" stroke-width="2.4"/>')
    o.append(f'<rect x="{ox + PW - 232}" y="{oy + 100}" width="212" height="{PH - 140}" rx="10" fill="{vcol}" opacity="0.08"/>')
    yy = oy + 128
    for ln in verdict:
        o.append(f'<text x="{ox + PW - 218}" y="{yy}" font-size="14" fill="#111">{esc(ln)}</text>')
        yy += 21
    return o


o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#f3f4f6"/>',
     '<text x="30" y="48" font-size="28" font-weight="800" fill="#111">WHAT A PULLBACK IS · my reading of your 5 screenshots (buys; sells are the mirror)</text>',
     '<text x="30" y="80" font-size="17" fill="#444">Story-timeframe candles (M15 in the H4 → M15 → M5 plan, H4 in the Daily plan). Breaks are body closes. Please confirm or correct before I change the script.</text>']

# 1. a real pullback, then the HIGH breaks -> that low becomes the pullback line
w1 = [(0, 100), (5, 106), (6, 105.4), (9, 108.5), (12, 106.0), (14, 104.6), (16, 105.4), (19, 109.8), (22, 111.5)]
o += panel(30, 110, "1 · The low that broke the high = the pullback line",
           "A pullback from the high, then a close above that high: only now the pullback's low becomes the line.",
           w1, 3, [('line', 9, 19, lambda hb, lb: 108.5, GR, 'the high', True),
                   ('dot', 14, lambda hb, lb: 104.3, BL),
                   ('line', 14, 23, lambda hb, lb: 104.3, BL, 'pullback line', False),
                   ('note', 19, lambda hb, lb: 110.0, 'close above the high', G, -14)],
           ["The move from this low", "broke the high, so it is", "the new pullback line.", "", "It moves again only when", "a later pullback's move", "breaks the next high."], G)

# 2. an internal break inside the pullback -> nothing moves
w2 = [(0, 100), (5, 106), (6, 105.4), (9, 108.5), (11, 106.4), (12, 107.0), (14, 105.2), (16, 106.6), (17, 106.1), (20, 107.4), (22, 106.6)]
o += panel(30 + PW + 0, 110, "2 · A break inside the pullback is internal",
           "Price breaks a lower high but stays below the high: the line must NOT move.",
           w2, 5, [('line', 9, 23, lambda hb, lb: 108.5, GR, 'the high (not broken)', True),
                   ('line', 0, 23, lambda hb, lb: 99.6, BL, 'pullback line stays', False),
                   ('dot', 14, lambda hb, lb: 104.9, OR),
                   ('note', 18, lambda hb, lb: 107.6, 'internal break, not tracked', OR, -12)],
           ["Your 30 Dec 08:15 chart:", "the line jumped to 1.11969", "after an 'M15 bullish cont'", "that never took the high", "(1.12110). Wrong.", "", "A close below 1.11969 then", "gave a false Pullback break."], RD)

# 3. a tiny pause in a run is not a pullback
w3 = [(0, 100), (3, 99.3), (6, 101.8), (9, 104.5), (10, 104.2), (13, 107.4), (14, 107.1), (17, 110.3), (19, 111.2)]
o += panel(30, 110 + PH + 20, "3 · A tiny pause in a run is not a pullback",
           "One small candle against the run makes no high and no low.",
           w3, 9, [('line', 0, 20, lambda hb, lb: 98.9, BL, 'pullback line stays', False),
                   ('dot', 10, lambda hb, lb: 103.9, OR),
                   ('dot', 14, lambda hb, lb: 106.8, OR),
                   ('note', 12, lambda hb, lb: 103.4, 'pauses, not pullbacks', OR, 22)],
           ["Your 30 Dec 04:45 chart:", "1.11908 is a pause in the", "run. The line stays at", "1.11741, the low that broke", "the high.", "", "Same as 1.11254 (Feb) and", "the 1-2 Apr 2020 chart."], RD)

# 4. pullback confirmed: a close below the pullback line
w4 = [(0, 100), (4, 105.5), (6, 104.4), (9, 108.6), (12, 106.6), (13, 107.2), (16, 103.4), (19, 101.2)]
o += panel(30 + PW + 0, 110 + PH + 20, "4 · Pullback confirmed: a close below the line",
           "Only a close below the real pullback line confirms the pullback (the range starts here).",
           w4, 4, [('line', 6, 17, lambda hb, lb: 104.1, BL, 'pullback line', False),
                   ('note', 16, lambda hb, lb: 103.0, 'Pullback break', RD, 26),
                   ('line', 9, 20, lambda hb, lb: 108.9, OR, 'range high', False)],
           ["Inside a range with no", "pullback (your 30 Dec", "20:15 circle), internal", "breaks change nothing.", "", "The range high, the range", "low and the line only move", "on a REAL pullback + break."], G)

o += ['<text x="30" y="%d" font-size="17" font-weight="800" fill="#b45309">My question: what makes a dip a REAL pullback (panel 1) rather than a pause (panel 3)?</text>' % (H - 34),
      '<text x="30" y="%d" font-size="15" fill="#444">a) its move breaks the last low inside the run first   b) at least one full A-shape and V-shape (colour change both ways)   c) your own words</text>' % (H - 10)]
o.append('</svg>')
p = "C:/Users/u/Documents/Pullback_Definition.svg"
open(p, "w", encoding="utf-8").write("\n".join(o))
print("ok", p)
