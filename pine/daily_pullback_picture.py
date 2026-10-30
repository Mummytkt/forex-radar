"""Picture: the Daily → H4 pullback story (the user's explanation, 2026-10-30), buy and
the mirrored sell. H4 candles; Daily levels drawn on top.
Output: Documents/Daily_H4_Story_Buys.svg / Daily_H4_Story_Sells.svg (+ PNG)."""
import html
import random
import re
import textwrap

W, H = 1900, 1060
L, R, T, B = 60, 1330, 110, 900
esc = html.escape

WAY = [(0, 115), (4, 109), (6, 111.5), (10, 83), (12, 86), (14, 84), (19, 95), (21, 91.5), (26, 101.5), (28, 98.5),
       (33, 108.5), (35, 104.5), (39, 113), (42, 107), (44, 110), (48, 101.5), (51, 106), (55, 97), (57, 100.5),
       (61, 94.5), (63, 96.2), (64, 95.4), (66, 102), (69, 98.6), (73, 107.6), (77, 100.6), (83, 118)]

SWAP = {"bullish": "bearish", "long": "short", "longs": "shorts", "demand": "supply", "high": "low", "highs": "lows",
        "discount": "premium", "buy": "sell", "HL": "LH", "HH": "LL", "up": "down", "higher": "lower", "below": "above",
        "above": "below", "lower": "higher", "BUY": "SELL", "Buy": "Sell", "BUYS": "SELLS", "resistance": "support"}
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
    return re.sub(r"[A-Za-z]+", rep, t)


def candles(seed=9):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(WAY, WAY[1:]):
        for t in range(a, b):
            path.append(pa + (pb - pa) * (t - a) / (b - a))
    path.append(WAY[-1][1])
    out, prev = [], path[0] + 0.8
    for p in path:
        o, c = prev, p + random.uniform(-0.4, 0.4)
        out.append((o, max(o, c) + random.uniform(0.2, 1.1), min(o, c) - random.uniform(0.2, 1.1), c))
        prev = c
    return out


def build(bull):
    t = (lambda s: s) if bull else swap
    G, RD = "#16a34a", "#dc2626"
    UPC, DNC = (G, RD) if bull else (RD, G)       # with the Daily / against it
    cs = candles()            # drawn in buy terms; the sell picture flips the screen
    n = len(cs)
    lo, hi = 78, 122
    dx = (R - L) / (n + 4)
    X = lambda i: L + dx * (i + 0.5)
    Y = (lambda p: B - (p - lo) / (hi - lo) * (B - T)) if bull else (lambda p: T + (p - lo) / (hi - lo) * (B - T))
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    a(f'<text x="{L}" y="44" font-size="28" font-weight="800" fill="#111">DAILY → H4 STORY · {"BUYS" if bull else "SELLS"}</text>')
    a(f'<text x="{L}" y="72" font-size="16" fill="#444">{esc(t("A Daily breakout, its pullback on H4, the H4 pullback back in line with the Daily, then entries from H4 POIs with an LTF confirmation. H4 candles; Daily levels drawn on top."))}</text>')

    def zone(i0, i1, p1, p2, col, txt, op=0.14, tpos='top'):
        ya, yb = sorted((Y(p1), Y(p2)))
        a(f'<rect x="{X(i0) - dx / 2:.1f}" y="{ya:.1f}" width="{X(i1) - X(i0) + dx:.1f}" height="{yb - ya:.1f}" fill="{col}" opacity="{op}" stroke="{col}" stroke-opacity="0.5"/>')
        if txt:
            top = (tpos == 'top') == bull
            a(f'<text x="{X(i0) + 2:.1f}" y="{(ya - 6) if top else (yb + 15):.1f}" font-size="12.5" font-weight="700" fill="{col}">{esc(t(txt))}</text>')

    def line(i0, i1, p, col, dash, w, txt, where='end', size=12.5):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{w}"{d}/>')
        if txt:
            if where == 'end':     # inside the chart, at the right end, on the outer side of the line
                a(f'<text x="{X(i1) - 4:.1f}" y="{Y(p) - 6 if bull else Y(p) + 15:.1f}" font-size="{size}" font-weight="700" fill="{col}" text-anchor="end">{esc(t(txt))}</text>')
            else:   # mid-above / mid-below in buy terms
                above = (where == 'above') == bull
                a(f'<text x="{(X(i0) + X(i1)) / 2:.1f}" y="{Y(p) - 6 if above else Y(p) + 15:.1f}" font-size="{size}" font-weight="700" fill="{col}" text-anchor="middle">{esc(t(txt))}</text>')

    # the Daily range after the breakout: external low 83 → new high 113; EQ 98
    ya, yb = sorted((Y(83), Y(113)))
    a(f'<rect x="{X(26):.1f}" y="{ya:.1f}" width="{X(n + 2) - X(26):.1f}" height="{yb - ya:.1f}" fill="#7c3aed" opacity="0.035"/>')
    zone(0, 46, 111, 115, DNC, "supply / resistance above the breakout zone (where the pullback may start)", 0.16, 'bottom')
    zone(24, n + 2, 96, 100, UPC, "Daily breakout zone (Daily demand)", 0.10, 'bottom')
    zone(68, n + 2, 98.0, 100.4, UPC, "H4 demand POI (after H4 lines up)", 0.22, 'bottom')

    for i, (op, h, l, c) in enumerate(cs):
        up = (c >= op) if bull else (c < op)      # rising on screen = a bullish candle
        a(f'<line x1="{X(i):.1f}" y1="{Y(h):.1f}" x2="{X(i):.1f}" y2="{Y(l):.1f}" stroke="#1e3a8a" stroke-width="1.1"/>')
        y1, y2 = sorted((Y(op), Y(c)))
        a(f'<rect x="{X(i) - dx * 0.32:.1f}" y="{y1:.1f}" width="{dx * 0.64:.1f}" height="{max(y2 - y1, 1.3):.1f}" fill="{"#ffffff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')

    # Daily lines
    line(4, n + 2, 100, "#111", "8 5", 2.2, "Daily external high (broken)")
    line(10, n + 2, 83, "#111", "", 2.2, "Daily external low (the range's floor)")
    line(26, n + 2, 113, "#111", "", 2.2, "Daily high (the target)")
    line(26, n + 2, 98, "#888", "6 6", 1.2, "Daily range EQ", 'end', 11.5)
    # H4 structure
    line(35, 48, 104.5, DNC, "1.5 3", 1.6, "H4 BOS down (last H4 higher low)", 'below', 12)
    line(51, 73, 106, DNC, "", 2, "main H4 high", 'above', 12)
    line(57, 66, 100.5, UPC, "3 3", 1.5, "H4 CHoCH up", 'above', 12)
    line(51, 73, 106, UPC, "1.5 3", 1.6, "")
    a(f'<text x="{X(73):.1f}" y="{Y(106) + (-24 if bull else 34):.1f}" font-size="12.5" font-weight="800" fill="{UPC}" text-anchor="middle">{esc(t("H4 BOS up"))}</text>')

    # numbered notes: (n, bar, price, box x, box y (buy), text)
    NOTES = [
        (1, 26, 101.5, 120, 160, "Daily external breakout: a Daily candle breaks the external high (wick by default, body as an option). After a breakout, a pullback is expected."),
        (2, 39, 113, 400, 135, "Look for where that pullback may start: the opposite levels above the breakout zone: V-shape / resistance, OC, FVG, supply."),
        (3, 48, 101.5, 700, 160, "Price reacts there and gives an H4 bearish breakout (body close below the last H4 higher low): the Daily pullback is confirmed."),
        (4, 51, 106, 1010, 150, "After every breakout a pullback is expected. This high is the main H4 level: H4 stays bearish until it is taken out."),
        (5, 61, 94.5, 560, 790, "Price is back at the Daily breakout zone, still inside the Daily external range (discount)."),
        (6, 66, 102, 850, 800, "H4 bullish CHoCH: the H4 pullback starts. It is in line with the Daily (continuation). Careful: the main H4 high can still push price down."),
        (7, 73, 107.6, 880, 640, "The main H4 high is taken out (body close): H4 is now aligned with the Daily = the Bias Pointer's H4 External breakout (BUY CONFIRMED)."),
        (8, 77, 100.6, 1110, 760, "Entries follow the trend from the H4 POIs with an LTF confirmation (M15 / M5 sweep, sweep and break). Target: the Daily high, then beyond."),
    ]
    for num, i, p, bx, by, txt in NOTES:
        lines = textwrap.wrap(t(txt), 40)
        bw, bh = 280, 24 + 15 * len(lines)
        if not bull:
            by = (T + B) - by - bh
        bx = min(max(bx, L), R - bw)
        by = min(max(by, T - 20), B - bh)
        px, py = X(i), Y(p)
        ex = min(max(px, bx), bx + bw)
        ey = by if py < by else by + bh if py > by + bh else py
        a(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#bbb"/>')
        a(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="{bh}" rx="6" fill="#fff" stroke="#cfcfcf"/>')
        a(f'<circle cx="{bx + 15:.1f}" cy="{by + 15:.1f}" r="10" fill="#7c3aed"/><text x="{bx + 15:.1f}" y="{by + 19:.1f}" font-size="12" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
        for k, ln in enumerate(lines):
            a(f'<text x="{bx + 32:.1f}" y="{by + 19 + 15 * k:.1f}" font-size="12" fill="#222">{esc(ln)}</text>')

    # the story strip + timeframe stacks
    sy = B + 30
    STEPS = [("Daily breakout", "#111"), ("pullback expected", "#666"), ("reaction above + H4 BOS down = Daily pullback", DNC),
             ("H4 CHoCH up = H4 pullback, with the Daily", UPC), ("main H4 high taken = aligned", UPC), ("H4 POI + LTF confirmation = entry", "#7c3aed")]
    x = L
    for k, (txt, col) in enumerate(STEPS):
        s_ = t(txt)
        wdt = len(s_) * 7.2 + 24
        a(f'<rect x="{x:.0f}" y="{sy}" width="{wdt:.0f}" height="32" rx="8" fill="{col}" opacity="0.12"/>')
        a(f'<text x="{x + 12:.0f}" y="{sy + 21}" font-size="13" font-weight="700" fill="{col}">{esc(s_)}</text>')
        x += wdt + (22 if k < len(STEPS) - 1 else 0)
        if k < len(STEPS) - 1:
            a(f'<text x="{x - 16:.0f}" y="{sy + 21}" font-size="15" fill="#999">→</text>')
    a(f'<text x="{L}" y="{sy + 64}" font-size="14" fill="#333">{esc("The same story one level up or down: W → D → H4 (higher timeframes) · D → H4 → M15 (swing) · H4 → M15 → M5 (day trading).")}</text>')
    a(f'<text x="{L}" y="{sy + 88}" font-size="14" fill="#333">{esc(t("All of it happens inside the Daily external range: a close below the Daily external low ends the buy story."))}</text>')

    # side panel: how it maps
    PX = 1370
    a(f'<rect x="{PX}" y="{T - 20}" width="{W - PX - 20}" height="{B - T + 40}" rx="10" fill="#f8f7fc" stroke="#e4e0f3"/>')
    a(f'<text x="{PX + 20}" y="{T + 12}" font-size="18" font-weight="800" fill="#4c1d95">{esc(t("HOW TO READ IT (BUYS)"))}</text>')
    PANEL = [
        "Daily: the Bias Pointer's External high / low. A break is a wick beyond the level by default (body close as an option).",
        "The Daily pullback is H4 going against the Daily: an H4 BOS down after a Daily breakout up.",
        "H4 after its breakout: a pullback is expected. The H4 CHoCH up starts it and lines up with the Daily.",
        "H4 is still bearish until its main high is taken out. Until then, the main H4 high can push price down.",
        "Main H4 high taken out = H4 aligned with the Daily. On the Bias Pointer this is the Daily reaction + H4 External breakout.",
        "Entries: H4 POIs (demand) with an M15 / M5 confirmation (sweep, sweep and break), in the Daily direction.",
        "Only inside the Daily external range. A close below the Daily external low ends it.",
    ]
    yy = T + 46
    for k, it in enumerate(PANEL):
        lines_ = textwrap.wrap(t(it), 52)
        a(f'<circle cx="{PX + 26}" cy="{yy - 4}" r="9" fill="#7c3aed"/><text x="{PX + 26}" y="{yy}" font-size="11" font-weight="700" fill="#fff" text-anchor="middle">{k + 1}</text>')
        for j, ln in enumerate(lines_):
            a(f'<text x="{PX + 44}" y="{yy + 16 * j}" font-size="13.5" fill="#222">{esc(ln)}</text>')
        yy += 16 * len(lines_) + 18
    a('</svg>')
    name = 'Daily_H4_Story_Buys' if bull else 'Daily_H4_Story_Sells'
    open(f'C:/Users/u/Documents/{name}.svg', 'w', encoding='utf-8').write('\n'.join(o))
    print(name, n)


build(True)
build(False)
