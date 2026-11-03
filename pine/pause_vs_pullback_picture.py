"""Pause vs pullback (user asked, 2026-11-03): when does a high COUNT, so that breaking it moves the pullback
line? Two panels, buys. Output: Documents/Pause_vs_Pullback.svg (+ PNG)."""
import html

esc = html.escape
W, H = 1900, 760
BL, OR, G, GR, INK = "#0284c7", "#ea580c", "#16a34a", "#6b7280", "#111827"
# hand-made candles (open, high, low, close)
PAUSE = [(100, 101.3, 99.8, 101.1), (101.1, 102.6, 100.9, 102.4), (102.4, 103.9, 102.2, 103.7),
         (103.7, 104.1, 103.1, 103.4),                                   # the small grey candle (a pause)
         (103.4, 105.4, 103.3, 105.2), (105.2, 106.7, 105.0, 106.5), (106.5, 107.9, 106.3, 107.7)]
PULL = [(100, 101.3, 99.8, 101.1), (101.1, 102.6, 100.9, 102.4), (102.4, 103.9, 102.2, 103.7),
        (103.7, 104.0, 102.3, 102.5), (102.5, 102.8, 101.4, 101.7),        # two grey candles: a real pullback
        (101.7, 103.2, 101.5, 103.0), (103.0, 105.0, 102.8, 104.8), (104.8, 106.4, 104.6, 106.2)]


def panel(ox, title, sub, cs, top_i, low_i, brk_i, counts, notes):
    o = [f'<rect x="{ox}" y="110" width="900" height="610" rx="14" fill="#fff" stroke="#e5e7eb"/>',
         f'<text x="{ox + 26}" y="152" font-size="23" font-weight="800" fill="{G if counts else OR}">{esc(title)}</text>',
         f'<text x="{ox + 26}" y="182" font-size="15.5" fill="#444">{esc(sub)}</text>']
    lo, hi = 98.8, 108.8
    L, R, T, B = ox + 40, ox + 560, 220, 690
    dx = (R - L) / (len(cs) + 1)
    X = lambda i: L + dx * (i + 0.5)
    Y = lambda p: B - (p - lo) / (hi - lo) * (B - T)
    top_body = max(cs[top_i][0], cs[top_i][3])
    top_low = min(cs[top_i][0], cs[top_i][3])
    # the body bottom of the high candle: the test line
    o.append(f'<line x1="{X(top_i) - dx * .5:.1f}" x2="{X(len(cs) - 1) + dx * .5:.1f}" y1="{Y(top_low):.1f}" y2="{Y(top_low):.1f}" stroke="{GR}" stroke-width="1.4" stroke-dasharray="6 5"/>')
    o.append(f'<text x="{X(len(cs) - 1) + dx * .6:.1f}" y="{Y(top_low) + 5:.1f}" font-size="13" fill="{GR}">bottom of the high candle\'s body</text>')
    o.append(f'<line x1="{X(top_i):.1f}" x2="{X(brk_i):.1f}" y1="{Y(top_body):.1f}" y2="{Y(top_body):.1f}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="3 4"/>')
    o.append(f'<text x="{X(top_i) - 10:.1f}" y="{Y(top_body) - 10:.1f}" font-size="14" font-weight="700" fill="{INK}" text-anchor="end">the high</text>')
    for i, (op, h, l, c) in enumerate(cs):
        col = "#2563eb" if c >= op else "#6b7280"
        y1, y2 = sorted((Y(op), Y(c)))
        o.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}" stroke-width="1.6"/>')
        o.append(f'<rect x="{X(i) - dx * .3:.1f}" y="{y1:.1f}" width="{dx * .6:.1f}" height="{max(y2 - y1, 2):.1f}" fill="{col}" rx="2"/>')
    if counts:
        pl = min(cs[low_i][0], cs[low_i][3])
        o.append(f'<line x1="{X(low_i):.1f}" x2="{X(len(cs) - 1) + dx * .5:.1f}" y1="{Y(pl):.1f}" y2="{Y(pl):.1f}" stroke="{BL}" stroke-width="3"/>')
        o.append(f'<rect x="{X(low_i) + 12:.1f}" y="{Y(pl) + 8:.1f}" width="250" height="24" rx="6" fill="{BL}"/>')
        o.append(f'<text x="{X(low_i) + 22:.1f}" y="{Y(pl) + 25:.1f}" font-size="14" font-weight="800" fill="#fff">new pullback line (moves here)</text>')
    else:
        o.append(f'<circle cx="{X(low_i):.1f}" cy="{Y(cs[low_i][3]):.1f}" r="14" fill="none" stroke="{OR}" stroke-width="2.6"/>')
        o.append(f'<line x1="{X(0):.1f}" x2="{X(len(cs) - 1) + dx * .5:.1f}" y1="{Y(99.9):.1f}" y2="{Y(99.9):.1f}" stroke="{BL}" stroke-width="3"/>')
        o.append(f'<text x="{X(1):.1f}" y="{Y(99.9) + 24:.1f}" font-size="14" font-weight="800" fill="{BL}">pullback line STAYS at the low that broke the earlier high</text>')
    yy = 250
    for ln in notes:
        o.append(f'<text x="{ox + 590}" y="{yy}" font-size="15.5" fill="#1f2937">{esc(ln)}</text>')
        yy += 25
    return o


o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#f3f4f6"/>',
     '<text x="40" y="52" font-size="28" font-weight="800" fill="#111">WHEN DOES A HIGH COUNT? · the question I could not explain in words</text>',
     '<text x="40" y="86" font-size="17" fill="#444">Buys. A high only matters if price really pulled back from it. The test I suggest: a later candle closes BELOW the bottom of the high candle\'s body (grey dashed line).</text>']
o += panel(40, "A · A pause: the high does NOT count",
           "One small grey candle stays above the grey dashed line.", PAUSE, 2, 3, 4, False,
           ["The grey candle never closed", "below the body of the candle", "that made the high.", "", "So nothing pulled back:", "no high, no low.", "", "Like your 1.11908 (30 Dec):", "the line should NOT move", "to this little candle."])
o += panel(960, "B · A real pullback: the high COUNTS",
           "A grey candle closes below the grey dashed line.", PULL, 2, 4, 6, True,
           ["A candle closed below the body", "of the candle that made the high:", "that is a real pullback.", "", "When price later closes above", "that high, the line moves to", "the lowest point of the pullback", "(the low that broke the high).", "", "Is this the right test?"])
o.append('</svg>')
open("C:/Users/u/Documents/Pause_vs_Pullback.svg", "w", encoding="utf-8").write("\n".join(o))
print("ok")
