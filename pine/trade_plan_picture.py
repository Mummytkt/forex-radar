"""Draws the HTF -> MTF -> LTF trade plan as candlestick pictures: buys, and sells as
the exact mirror (price flipped, words swapped). Output: Documents/TradePlan_Buys.svg,
TradePlan_Sells.svg (PNG copies made with a headless browser)."""
import random
import textwrap

W, H = 1900, 1120
L, R, T, B = 60, 1330, 110, 860       # chart area
PL, PR = 1370, 1880                    # watchlist panel
LO, HI = -6, 100

# The path (bar, price 0-100) in the buy version
WAY = [(0, 8), (5, 26), (7, 21), (10, 40), (13, 30), (16, 22), (20, 44), (22, 38), (25, 56), (27, 50), (30, 70), (32, 64),
       (36, 80),                                   # HTF weak high
       (41, 58), (45, 72), (51, 48), (55, 60), (61, 38), (65, 47), (71, 26), (74, 33), (78, 24),   # HTF pullback, MTF bearish
       (83, 44), (87, 36), (94, 56), (98, 48), (105, 68), (109, 62), (116, 78), (120, 71), (127, 92)]  # MTF bullish -> weak high


def candles(way, seed, noise=0.9):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for t in range(a, b):
            path.append(pa + (pb - pa) * (t - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 1
    for p in path:
        o = prev
        c = p + random.uniform(-noise, noise)
        h = max(o, c) + random.uniform(0.3, 1.6)
        lo = min(o, c) - random.uniform(0.3, 1.6)
        out.append((o, h, lo, c))
        prev = c
    return out


def wrap(txt, n):
    return textwrap.wrap(txt, n)


def build(bull):
    f = (lambda p: p) if bull else (lambda p: 100 - p)          # mirror the price
    w = (lambda a, b: a) if bull else (lambda a, b: b)           # pick the words
    cs = [tuple(f(v) for v in c) for c in candles(WAY, 11)]
    cs = [(o, max(h, lo), min(h, lo), c) for o, h, lo, c in cs]
    n = len(cs)
    dx = (R - L) / (n + 3)
    X = lambda i: L + dx * (i + 0.5)
    Y = lambda p: B - (p - LO) / (HI - LO) * (B - T)
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    a(f'<text x="{L}" y="44" font-size="28" font-weight="800" fill="#111">HIGH LEVEL TRADE PLAN · {w("BUYS", "SELLS")}</text>')
    a(f'<text x="{L}" y="72" font-size="16" fill="#444">HTF objective → MTF POIs → LTF execution · trade from STRONG structure, target WEAK structure · '
      f'{w("the sell picture is the exact mirror", "the exact mirror of the buy picture")}</text>')

    def hline(i0, i1, p, txt, width=3, dash='', col='#111', side='above', size=13, bold=True):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{width}"{d}/>')
        if txt:
            ty = Y(p) - 7 if side == 'above' else Y(p) + 17
            a(f'<text x="{X(i1):.1f}" y="{ty:.1f}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col}" text-anchor="end">{txt}</text>')

    def zone(i0, i1, p1, p2, col, txt, op=0.18, tsize=12, where='in'):
        y1, y2 = sorted((Y(f(p1)), Y(f(p2))))
        a(f'<rect x="{X(i0) - dx / 2:.1f}" y="{y1:.1f}" width="{X(i1) - X(i0) + dx:.1f}" height="{y2 - y1:.1f}" fill="{col}" opacity="{op}" stroke="{col}" stroke-opacity="0.6"/>')
        if txt:
            if where == 'in':
                a(f'<text x="{X(i1) + dx / 2 - 4:.1f}" y="{(y1 + y2) / 2 + 4:.1f}" font-size="{tsize}" fill="{col}" text-anchor="end" font-weight="600">{txt}</text>')
            elif where == 'right':
                a(f'<text x="{X(i1) + dx:.1f}" y="{(y1 + y2) / 2 + 4:.1f}" font-size="{tsize}" fill="{col}" font-weight="600">{txt}</text>')
            else:   # left, outside
                a(f'<text x="{X(i0) - dx:.1f}" y="{(y1 + y2) / 2 + 4:.1f}" font-size="{tsize}" fill="{col}" text-anchor="end" font-weight="600">{txt}</text>')

    DEM, SUP = ('#16a34a', '#dc2626') if bull else ('#dc2626', '#16a34a')   # buy-side zones / opposing zones

    # premium / discount of the HTF swing range (strong 22 → weak 80), EQ 51
    eq = 51
    y_top, y_eq, y_bot = sorted((Y(f(80)), Y(f(eq)), Y(f(22))))
    # above the EQ is always premium (red), below always discount (green)
    a(f'<rect x="{X(36):.1f}" y="{y_top:.1f}" width="{X(n + 1) - X(36):.1f}" height="{y_eq - y_top:.1f}" fill="#dc2626" opacity="0.045"/>')
    a(f'<rect x="{X(36):.1f}" y="{y_eq:.1f}" width="{X(n + 1) - X(36):.1f}" height="{y_bot - y_eq:.1f}" fill="#16a34a" opacity="0.05"/>')
    hline(36, n + 1, f(eq), "HTF swing EQ 50%", 1.2, '8 6', '#777', 'above', 12, False)
    a(f'<text x="{X(n + 1):.1f}" y="{(y_top + y_eq) / 2:.1f}" font-size="13" fill="#b91c1c" text-anchor="end" font-weight="600">PREMIUM (sell zone)</text>')
    a(f'<text x="{X(n + 1):.1f}" y="{(y_bot + y_eq) / 2:.1f}" font-size="13" fill="#15803d" text-anchor="end" font-weight="600">DISCOUNT (buy zone)</text>')

    # zones
    zone(14, n + 1, 21, 27, DEM, w("HTF demand (discount)", "HTF supply (premium)"), 0.10, 12)
    zone(70, 80, 23, 29, DEM, w("7 · extreme HTF + stacked MTF demand", "7 · extreme HTF + stacked MTF supply"), 0.25, 12, 'left')
    for (i0, i1, p1, p2) in [(44, 50, 69, 73), (54, 60, 57, 61), (64, 70, 44, 48)]:
        zone(i0, i1, p1, p2, SUP, w("MTF supply", "MTF demand"), 0.22, 11, 'right')
    for (i0, i1, p1, p2) in [(86, 97, 34, 38), (97, 108, 46, 50), (108, 119, 60, 64)]:
        zone(i0, i1, p1, p2, DEM, w("MTF demand", "MTF supply"), 0.22, 11, 'right')

    # candles
    for i, (op, h, lo, c) in enumerate(cs):
        x = X(i)
        up = c >= op
        a(f'<line x1="{x:.1f}" y1="{Y(h):.1f}" x2="{x:.1f}" y2="{Y(lo):.1f}" stroke="#1e3a8a" stroke-width="1"/>')
        t, b = max(op, c), min(op, c)
        a(f'<rect x="{x - dx * 0.33:.1f}" y="{Y(t):.1f}" width="{dx * 0.66:.1f}" height="{max(Y(b) - Y(t), 1.2):.1f}" '
          f'fill="{"#ffffff" if up else "#1e3a8a"}" stroke="#1e3a8a" stroke-width="1"/>')

    # HTF structure
    hline(10, 20, f(40), w("HTF BOS", "HTF BOS"), 2, '', '#111', 'above', 12)
    hline(16, n + 1, f(22), w("HTF STRONG LOW (protected)", "HTF STRONG HIGH (protected)"), 3, '', '#111', 'below' if bull else 'above')
    hline(36, n + 1, f(80), '', 3)
    a(f'<text x="{X(84):.1f}" y="{Y(f(80)) + (-8 if bull else 18):.1f}" font-size="13" font-weight="700" fill="#111">{w("HTF WEAK HIGH (target)", "HTF WEAK LOW (target)")}</text>')
    hline(36, 127, f(80), '', 0)

    # MTF structure marks: i-BOS lines
    def brk(i0, i1, p, txt, col):
        a(f'<line x1="{X(i0):.1f}" y1="{Y(f(p)):.1f}" x2="{X(i1):.1f}" y2="{Y(f(p)):.1f}" stroke="{col}" stroke-width="1.4" stroke-dasharray="2 3"/>')
        a(f'<text x="{X(i0) + (X(i1) - X(i0)) * 0.72:.1f}" y="{Y(f(p)) + (16 if (col == "#dc2626") == bull else -6):.1f}" font-size="12" fill="{col}" text-anchor="middle" font-weight="600">{txt}</text>')
    BEARC, BULLC = ('#dc2626', '#16a34a') if bull else ('#16a34a', '#dc2626')
    brk(32, 40, 64, "MTF i-BOS", BEARC)
    brk(65, 91, 47, "MTF i-BOS", BULLC)
    brk(74, 81, 33, "MTF CH", BULLC)
    brk(116, 125, 80, "HTF BOS", BULLC)

    # circles on MTF swing points
    for i, p in [(45, 72), (55, 60), (65, 47), (87, 36), (98, 48), (109, 62), (78, 24)]:
        a(f'<circle cx="{X(i):.1f}" cy="{Y(f(p)):.1f}" r="9" fill="none" stroke="#666" stroke-width="1.2"/>')

    # numbered notes: (bar, price, box dx, box dy, buy text, sell text)
    NOTES = [
        (1, 22, 46, -10, 0, "HTF is bullish. Consider long continuations from MTF POIs after the BOS, but the HTF pullback can start. Quick targets.",
         "HTF is bearish. Consider short continuations from MTF POIs after the BOS, but the HTF pullback can start. Quick targets."),
        (2, 36, 80, -360, 10, "After the HTF BOS expect an HTF swing pullback: HTF supply mitigated, MTF CH / i-BOS, target HTF demand in discount.",
         "After the HTF BOS expect an HTF swing pullback: HTF demand mitigated, MTF CH / i-BOS, target HTF supply in premium."),
        (3, 45, 72, 40, -10, "Wait for an MTF POI to be mitigated before the LTF entry model, or for an MTF CH / i-BOS to form a fresh POI.",
         "Wait for an MTF POI to be mitigated before the LTF entry model, or for an MTF CH / i-BOS to form a fresh POI."),
        (4, 55, 60, 40, -12, "Trade with the MTF order flow (shorts) into HTF discount demand. MTF objective = the HTF pullback.",
         "Trade with the MTF order flow (longs) into HTF premium supply. MTF objective = the HTF pullback."),
        (5, 51, 48, -60, 60, "Don't buy weak lows.", "Don't sell weak highs."),
        (6, 61, 38, -40, 75, "Careful with shorts in HTF discount.", "Careful with longs in HTF premium."),
        (7, 76, 24, -10, 70, "Extreme HTF + stacked MTF demand mitigated: the last area that must hold for the HTF uptrend. Longs can be more aggressive here.",
         "Extreme HTF + stacked MTF supply mitigated: the last area that must hold for the HTF downtrend. Shorts can be more aggressive here."),
        (8, 83, 44, 10, -8, "Late shorts here are against the swing POI: the swing pullback is likely complete.",
         "Late longs here are against the swing POI: the swing pullback is likely complete."),
        (9, 94, 56, -30, -40, "MTF i-BOS: internal now bullish. Supply only gives pullbacks. Buy the strong MTF HLs.",
         "MTF i-BOS: internal now bearish. Demand only gives pullbacks. Sell the strong MTF LHs."),
        (10, 116, 78, -150, -30, "All timeframes aligned: target the weak HTF high.",
         "All timeframes aligned: target the weak HTF low."),
    ]
    for num, i, p, ox, oy, tb, ts in NOTES:
        lines = wrap(w(tb, ts), 34)
        bw, bh = 238, 22 + 15 * len(lines)
        px, py = X(i), Y(f(p))
        # buys: notes above highs / below lows as placed; sells: mirrored vertically
        oy2 = oy if bull else -oy
        bx = px + ox
        by = (py - 40 - bh + oy2) if (p > 50) == bull else (py + 40 + oy2)
        by = min(max(by, T + 4), B - bh - 4)
        bx = min(max(bx, L + 4), R - bw - 4)
        a(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{bx + bw / 2:.1f}" y2="{(by + bh) if by + bh < py else by:.1f}" stroke="#bbb" stroke-width="1"/>')
        a(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="{bh}" rx="6" fill="#ffffff" stroke="#c7c7c7"/>')
        a(f'<circle cx="{bx + 14:.1f}" cy="{by + 15:.1f}" r="10" fill="#7c3aed"/><text x="{bx + 14:.1f}" y="{by + 19:.1f}" font-size="12" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
        for k, ln in enumerate(lines):
            a(f'<text x="{bx + 30:.1f}" y="{by + 19 + 15 * k:.1f}" font-size="12" fill="#222">{ln}</text>')

    # phase strip
    sy = B + 18
    PH = [(36, 41, "D", "#ef4444", w("Shorts: phase D · wait", "Longs: phase D · wait")),
          (41, 71, "C", "#f59e0b", w("Shorts · phase C (HTF pullback)", "Longs · phase C (HTF pullback)")),
          (71, 94, "B", "#f59e0b", w("Longs · phase B", "Shorts · phase B")),
          (94, 127, "A", "#16a34a", w("Longs · phase A → weak high", "Shorts · phase A → weak low"))]
    for i0, i1, ph, col, txt in PH:
        a(f'<rect x="{X(i0):.1f}" y="{sy}" width="{X(i1) - X(i0) - 2:.1f}" height="30" rx="5" fill="{col}" opacity="0.18"/>')
        a(f'<text x="{(X(i0) + X(i1)) / 2:.1f}" y="{sy + 20}" font-size="12.5" font-weight="600" fill="#222" text-anchor="middle">{txt if X(i1) - X(i0) > 120 else ph}</text>')
    a(f'<text x="{L}" y="{sy + 20}" font-size="12.5" font-weight="700" fill="#444">MTF phase →</text>')

    # legend line
    ly = sy + 62
    a(f'<line x1="{L}" y1="{ly}" x2="{L + 40}" y2="{ly}" stroke="#111" stroke-width="3"/><text x="{L + 48}" y="{ly + 5}" font-size="13">HTF swing high / low</text>')
    a(f'<line x1="{L + 240}" y1="{ly}" x2="{L + 280}" y2="{ly}" stroke="#666" stroke-width="1.4" stroke-dasharray="2 3"/><text x="{L + 288}" y="{ly + 5}" font-size="13">MTF i-BOS / CH</text>')
    a(f'<rect x="{L + 440}" y="{ly - 8}" width="30" height="16" fill="#16a34a" opacity="0.3"/><text x="{L + 478}" y="{ly + 5}" font-size="13">demand POI</text>')
    a(f'<rect x="{L + 590}" y="{ly - 8}" width="30" height="16" fill="#dc2626" opacity="0.3"/><text x="{L + 628}" y="{ly + 5}" font-size="13">supply POI</text>')
    a(f'<circle cx="{L + 760}" cy="{ly}" r="8" fill="none" stroke="#666"/><text x="{L + 776}" y="{ly + 5}" font-size="13">MTF POI mitigated → look at the LTF</text>')

    # watchlist panel
    a(f'<rect x="{PL}" y="{T - 20}" width="{PR - PL}" height="{H - T - 20}" rx="10" fill="#f8f7fc" stroke="#e4e0f3"/>')
    yy = T + 12
    a(f'<text x="{PL + 20}" y="{yy}" font-size="20" font-weight="800" fill="#4c1d95">WATCHLIST · {w("BUYS", "SELLS")}</text>')
    yy += 26
    a(f'<text x="{PL + 20}" y="{yy}" font-size="13" fill="#555">Always ask: what is the HTF objective? What has been mitigated?</text>')
    CHECK = [
        w("HTF swing is bullish (body close BOS above the old high). Strong low below, weak high above = the target.",
          "HTF swing is bearish (body close BOS below the old low). Strong high above, weak low below = the target."),
        w("Mark the HTF swing EQ. Buys only in discount (below EQ), sells only in premium.",
          "Mark the HTF swing EQ. Sells only in premium (above EQ), buys only in discount."),
        w("HTF pullback started? MTF bearish CH then i-BOS. Shorts from MTF supply are phase C: quick targets.",
          "HTF pullback started? MTF bullish CH then i-BOS. Longs from MTF demand are phase C: quick targets."),
        w("Don't buy weak lows. Wait for price to reach HTF discount demand.",
          "Don't sell weak highs. Wait for price to reach HTF premium supply."),
        w("Extreme HTF + stacked MTF demand mitigated = phase B: longs allowed if there is enough RR to internal supply. Optional: wait for the MTF CH.",
          "Extreme HTF + stacked MTF supply mitigated = phase B: shorts allowed if there is enough RR to internal demand. Optional: wait for the MTF CH."),
        w("MTF bullish i-BOS = phase A: buy the MTF demand at the strong HL. No MTF CH needed at the POI; go to the LTF entry.",
          "MTF bearish i-BOS = phase A: sell the MTF supply at the strong LH. No MTF CH needed at the POI; go to the LTF entry."),
        w("Keep buying strong MTF HLs; supply only gives pullbacks. Target: the weak HTF high.",
          "Keep selling strong MTF LHs; demand only gives pullbacks. Target: the weak HTF low."),
        "Phase D (counter swing + counter internal): avoid, or at least wait for an M15 CH.",
        "Range with no clear intent: stay out of the middle. Longs bottom 33%, shorts top 33%, or wait for the breakout.",
    ]
    yy += 18
    for k, txt in enumerate(CHECK):
        lines = wrap(txt, 60)
        yy += 10
        a(f'<rect x="{PL + 20}" y="{yy - 1}" width="14" height="14" rx="3" fill="#fff" stroke="#7c3aed" stroke-width="1.5"/>')
        for j, ln in enumerate(lines):
            a(f'<text x="{PL + 44}" y="{yy + 11 + 16 * j}" font-size="13" fill="#222">{ln}</text>')
        yy += 16 * len(lines) + 4

    # LTF inset: entry model inside the MTF POI
    iy0 = yy + 22
    a(f'<text x="{PL + 20}" y="{iy0}" font-size="15" font-weight="700" fill="#4c1d95">LTF execution inside the MTF POI</text>')
    ix0, ix1, it, ib = PL + 30, PR - 30, iy0 + 14, H - 40
    IW = [(0, 70), (4, 52), (6, 60), (10, 42), (12, 50), (16, 30), (18, 40), (20, 33), (25, 62), (27, 54), (31, 78)]
    ic = [tuple(f(v) for v in c) for c in candles(IW, 5, 0.8)]
    ic = [(op, max(h, lo), min(h, lo), c) for op, h, lo, c in ic]
    ni = len(ic)
    idx = (ix1 - ix0) / (ni + 2)
    IX = lambda i: ix0 + idx * (i + 0.5)
    IY = lambda p: ib - (p - 20) / (85 - 20) * (ib - it)
    zy1, zy2 = sorted((IY(f(27)), IY(f(36))))
    a(f'<rect x="{IX(13):.1f}" y="{zy1:.1f}" width="{IX(ni + 1) - IX(13):.1f}" height="{zy2 - zy1:.1f}" fill="{DEM}" opacity="0.2"/>')
    a(f'<text x="{IX(ni + 1) - 2:.1f}" y="{zy2 + 14 if bull else zy1 - 5:.1f}" font-size="11" fill="{DEM}" text-anchor="end">{w("MTF demand POI", "MTF supply POI")}</text>')
    for i, (op, h, lo, c) in enumerate(ic):
        x = IX(i)
        up = c >= op
        a(f'<line x1="{x:.1f}" y1="{IY(h):.1f}" x2="{x:.1f}" y2="{IY(lo):.1f}" stroke="#1e3a8a"/>')
        t, b = max(op, c), min(op, c)
        a(f'<rect x="{x - idx * 0.33:.1f}" y="{IY(t):.1f}" width="{idx * 0.66:.1f}" height="{max(IY(b) - IY(t), 1):.1f}" fill="{"#fff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')
    a(f'<line x1="{IX(18):.1f}" y1="{IY(f(41)):.1f}" x2="{IX(23):.1f}" y2="{IY(f(41)):.1f}" stroke="{BULLC}" stroke-dasharray="3 3" stroke-width="1.4"/>')
    a(f'<text x="{IX(19):.1f}" y="{IY(f(41)) - 5 if bull else IY(f(41)) + 14:.1f}" font-size="11" fill="{BULLC}" font-weight="600">LTF CH</text>')
    a(f'<text x="{IX(23):.1f}" y="{IY(f(31)) + 24 if bull else IY(f(41)) + 34:.1f}" font-size="12" fill="#222" font-weight="600">{w("entry ▲ after the LTF CH", "entry ▼ after the LTF CH")}</text>')
    a('</svg>')
    name = 'TradePlan_Buys' if bull else 'TradePlan_Sells'
    open(f'C:/Users/u/Documents/{name}.svg', 'w', encoding='utf-8').write('\n'.join(o))
    print(name, n, 'candles')


build(True)
build(False)
