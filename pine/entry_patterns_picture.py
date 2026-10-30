"""Picture: entry confirmations at an H4 level (buy and sell).
Row 1 buy at an H4 A-shape level (broken, retested from above); row 2 the mirror sell
at an H4 V-shape level. Columns: the H4 level · the 1H / 2H sweep · the 15m / 5m sweep
and break. Output: Documents/Entry_Confirmations_H4_level.svg (+ PNG via headless browser)."""
import html

W, H = 2120, 1400
BULL_F, LINE = "#ffffff", "#1e3a8a"
G, RD, PU, GR = "#16a34a", "#dc2626", "#7c3aed", "#6b7280"
esc = html.escape
o = []
a = o.append
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
a('<text x="40" y="44" font-size="28" font-weight="800" fill="#111">ENTRY CONFIRMATIONS AT AN H4 LEVEL</text>')
a('<text x="40" y="72" font-size="16" fill="#444">The H4 level is set in the level watch. The confirmation forms on a LOWER timeframe AT that level: '
  'a 1H / 2H sweep, or a 15m / 5m sweep and break. The first one to form is the entry.</text>')


def mirror(cs, L):
    return [(2 * L - op, 2 * L - lo, 2 * L - hi, 2 * L - c) for op, hi, lo, c in cs]


def panel(x0, y0, w, h, title, sub, cs, pmin, pmax, marks, bull):
    n = len(cs)
    dx = w / (n + 4)
    X = lambda i: x0 + dx * (i + 1)
    Y = lambda p: y0 + 46 + (pmax - p) / (pmax - pmin) * (h - 60)
    a(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="10" fill="#fbfbfd" stroke="#e5e7eb"/>')
    a(f'<text x="{x0 + 14}" y="{y0 + 24}" font-size="16" font-weight="800" fill="#111">{esc(title)}</text>')
    a(f'<text x="{x0 + 14}" y="{y0 + 42}" font-size="12.5" fill="#555">{esc(sub)}</text>')
    # zones / lines first, candles on top, text last
    for m in marks:
        if m[0] == 'band':
            _, p1, p2, col, txt = m
            ya, yb = sorted((Y(p1), Y(p2)))
            a(f'<rect x="{x0 + 6}" y="{ya:.1f}" width="{w - 12}" height="{yb - ya:.1f}" fill="{col}" opacity="0.13"/>')
            if txt:
                a(f'<text x="{x0 + w - 10}" y="{ya - 5:.1f}" font-size="12" font-weight="700" fill="{col}" text-anchor="end">{esc(txt)}</text>')
        if m[0] == 'line':
            _, i0, i1, p, col, dash, txt, below = m
            d = f' stroke-dasharray="{dash}"' if dash else ''
            a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="1.6"{d}/>')
            if txt:
                a(f'<text x="{X(i1) + 4:.1f}" y="{Y(p) + (14 if below else -5):.1f}" font-size="12" fill="{col}" font-weight="600">{esc(txt)}</text>')
    for i, (op, hi, lo, c) in enumerate(cs):
        up = c >= op
        a(f'<line x1="{X(i):.1f}" y1="{Y(hi):.1f}" x2="{X(i):.1f}" y2="{Y(lo):.1f}" stroke="{LINE}" stroke-width="1.3"/>')
        ya, yb = sorted((Y(op), Y(c)))
        a(f'<rect x="{X(i) - dx * 0.32:.1f}" y="{ya:.1f}" width="{dx * 0.64:.1f}" height="{max(yb - ya, 1.5):.1f}" fill="{BULL_F if up else LINE}" stroke="{LINE}" stroke-width="1.3"/>')
    for m in marks:
        if m[0] == 'hi':      # highlight a candle
            _, i, col, txt, above = m
            op, hi, lo, c = cs[i]
            a(f'<rect x="{X(i) - dx * 0.55:.1f}" y="{Y(hi) - 6:.1f}" width="{dx * 1.1:.1f}" height="{Y(lo) - Y(hi) + 12:.1f}" rx="5" fill="none" stroke="{col}" stroke-width="2"/>')
            if txt:
                ty = Y(hi) - 14 if above else Y(lo) + 24
                for k, ln in enumerate(txt.split('\n')):
                    a(f'<text x="{X(i):.1f}" y="{ty + 15 * k - (15 * (len(txt.split(chr(10))) - 1) if above else 0):.1f}" font-size="12.5" font-weight="700" fill="{col}" text-anchor="middle">{esc(ln)}</text>')
        if m[0] == 'note':    # free text at (candle index, price)
            _, i, p, txt, col, anchor = m
            for k, ln in enumerate(txt.split('\n')):
                a(f'<text x="{X(i):.1f}" y="{Y(p) + 15 * k:.1f}" font-size="12.5" fill="{col}" text-anchor="{anchor}" font-weight="600">{esc(ln)}</text>')
        if m[0] == 'arrow':   # entry arrow at candle i
            _, i, p, col, txt = m
            x, y = X(i), Y(p)
            if bull:
                a(f'<path d="M {x:.1f} {y:.1f} l -8 14 l 16 0 z" fill="{col}"/>')
                a(f'<text x="{x:.1f}" y="{y + 30:.1f}" font-size="12.5" font-weight="800" fill="{col}" text-anchor="middle">{esc(txt)}</text>')
            else:
                a(f'<path d="M {x:.1f} {y:.1f} l -8 -14 l 16 0 z" fill="{col}"/>')
                a(f'<text x="{x:.1f}" y="{y - 20:.1f}" font-size="12.5" font-weight="800" fill="{col}" text-anchor="middle">{esc(txt)}</text>')


def row(y0, bull):
    L = 110.0
    f = (lambda cs: cs) if bull else (lambda cs: mirror(cs, L))
    m = (lambda p: p) if bull else (lambda p: 2 * L - p)
    w = (lambda b, s: b) if bull else (lambda b, s: s)
    # ── H4: the A-shape level, broken, price returns ──
    h4 = [(100, 104, 99, 103), (103, 107, 102, 106), (106, 111.2, 105, 110), (110, 110.8, 105, 106),
          (106, 107, 103, 104), (104, 106, 101, 102), (102, 105, 101, 104), (104, 109, 103, 108),
          (108, 114, 107, 113), (113, 117, 112, 116), (116, 118, 113, 114), (114, 115, 111.5, 112), (112, 113, 109.6, 111)]
    lo4, hi4 = (97, 120) if bull else (100, 123)
    panel(40, y0, 640, 470, w("H4 · the level (buy)", "H4 · the level (sell)"),
          w("An H4 A-shape: bullish candle, then bearish; level = the bullish body top.", "An H4 V-shape: bearish candle, then bullish; level = the bearish body bottom."),
          f(h4), lo4, hi4, [
              ('band', m(110.6), m(109.4), PU, "the level ± your tolerance (the level watch)"),
              ('line', 2, 13, m(110), PU, '', '', False),
              ('hi', 2, GR, w("A-shape", "V-shape"), bull),
              ('hi', 8, G if bull else RD, w("H4 close above\nthe level: broken", "H4 close below\nthe level: broken"), bull),
              ('note', 12, m(106.5) if bull else m(106.5) + 0, w("price is back at\nthe level → watch\nthe lower TFs", "price is back at\nthe level → watch\nthe lower TFs"), PU, 'middle'),
          ], bull)
    # ── 1H / 2H: the sweep ──
    s1 = [(114, 114.6, 112.6, 113), (113, 113.4, 111.5, 111.7), (111.7, 112.2, 110.7, 110.9), (110.9, 113.1, 109.7, 112.8),
          (112.8, 114.1, 112.4, 113.8), (113.8, 115.2, 113.5, 114.9)]
    lo1, hi1 = (108.8, 116.2) if bull else (103.8, 111.2)
    panel(720, y0, 640, 470, w("1H / 2H · SWEEP", "1H / 2H · SWEEP"),
          w("A bullish candle sweeps the bearish candle before it, at the level.", "A bearish candle sweeps the bullish candle before it, at the level."),
          f(s1), lo1, hi1, [
              ('band', m(110.6), m(109.4), PU, "H4 level"),
              ('line', 2, 5, m(110.7), RD if bull else G, '4 3', w("the bearish candle's low (swept)", "the bullish candle's high (swept)"), not bull),
              ('line', 2, 5, m(112.2), GR, '2 3', w("its high", "its low"), bull),
              ('hi', 2, RD if bull else G, w("1 · bearish\ncandle", "1 · bullish\ncandle"), bull),
              ('hi', 3, G if bull else RD, w("2 · bullish candle:\nwick below 1's low,\nbody closes above 1", "2 · bearish candle:\nwick above 1's high,\nbody closes below 1"), not bull),
              ('arrow', 4, m(112.4) - (0 if bull else 0), G if bull else RD, w("entry: next open", "entry: next open")),
              ('note', 3, m(109.0) if bull else m(109.0), w("stop below the sweep wick", "stop above the sweep wick"), GR, 'start'),
          ], bull)
    # ── 15m / 5m: sweep and break ──
    s2 = [(112.8, 113.0, 112.2, 112.3), (112.3, 112.5, 111.7, 111.8), (111.8, 112.3, 111.6, 112.1), (112.1, 112.2, 111.2, 111.3),
          (111.3, 111.5, 110.4, 110.6), (110.6, 111.15, 110.5, 111.0), (111.0, 111.05, 110.6, 110.7), (110.7, 110.8, 109.85, 110.55),
          (110.55, 111.0, 110.45, 110.95), (110.95, 111.65, 110.9, 111.55), (111.55, 112.25, 111.4, 112.1), (112.1, 112.7, 111.95, 112.6)]
    lo2, hi2 = (109.3, 113.4) if bull else (106.6, 110.7)
    panel(1400, y0, 680, 470, w("15m / 5m · SWEEP AND BREAK", "15m / 5m · SWEEP AND BREAK"),
          w("At the level: a low, a wick sweeps it, then a body close breaks the last lower high.", "At the level: a high, a wick sweeps it, then a body close breaks the last higher low."),
          f(s2), lo2, hi2, [
              ('band', m(110.6), m(109.4), PU, "H4 level"),
              ('line', 4, 8, m(110.4), RD if bull else G, '4 3', w("1 · the low at the level", "1 · the high at the level"), not bull),
              ('line', 5, 10, m(111.15), G if bull else RD, '2 3', w("3 · last lower high: BREAK", "3 · last higher low: BREAK"), bull),
              ('hi', 7, RD if bull else G, w("2 · SWEEP:\nwick below the low,\ncloses back above", "2 · SWEEP:\nwick above the high,\ncloses back below"), not bull),
              ('hi', 9, G if bull else RD, w("body close above\nthe lower high", "body close below\nthe higher low"), bull),
              ('arrow', 10, m(111.2), G if bull else RD, "entry: next open"),
              ('note', 7, m(109.45) if bull else m(109.45), w("stop below the sweep", "stop above the sweep"), GR, 'start'),
          ], bull)


a('<text x="40" y="112" font-size="20" font-weight="800" fill="#15803d">BUY</text>')
row(124, True)
a('<text x="40" y="626" font-size="20" font-weight="800" fill="#b91c1c">SELL (the mirror)</text>')
row(638, False)

# ── the level watch: several formations on one level ──
by = 1130
a(f'<rect x="40" y="{by}" width="2040" height="240" rx="10" fill="#f8f7fc" stroke="#e4e0f3"/>')
a(f'<text x="60" y="{by + 32}" font-size="18" font-weight="800" fill="#4c1d95">One level, several watches: the first to form is the entry</text>')
items = [
    "Level watch: the H4 level price (e.g. the A-shape body top), Buy or Sell, and a tolerance (how close to the level the pattern must form).",
    "Tick the formations to watch on it, each with its own timeframe:  ☐ 1H sweep   ☐ 2H sweep   ☐ 15m sweep and break   ☐ 5m sweep and break.",
    "Each formation is checked on its own timeframe's candles, only while price is at the level (inside the tolerance band).",
    "Whichever forms first sends the alert (with the timeframe and pattern in it). You choose: stop the other watches on that level, or keep them running.",
    "Sweep = the 1H / 2H candle pattern (one bullish candle sweeping one bearish candle). Sweep and break = the 15m / 5m structure (a low, its sweep, then the break of the last lower high).",
]
for k, t in enumerate(items):
    a(f'<circle cx="68" cy="{by + 62 + k * 34}" r="5" fill="{PU}"/><text x="82" y="{by + 67 + k * 34}" font-size="15" fill="#222">{esc(t)}</text>')
a('</svg>')
open('C:/Users/u/Documents/Entry_Confirmations_H4_level.svg', 'w', encoding='utf-8').write('\n'.join(o))
print('ok')
