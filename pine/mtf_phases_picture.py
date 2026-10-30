"""Candlestick version of the MTF phases trade plan slide (bullish), plus the sell mirror.
The path follows the slide's line point by point; CHoCH and i-BOS are marked where the
pullback starts and ends. Output: Documents/MTF_Phases_Buys.svg / MTF_Phases_Sells.svg."""
import html
import random
import re
import textwrap

W, H = 2240, 1250
# slide coordinates (x 230..1300, y 260..960) -> canvas
CX0, CY0, S = 50, 215, 1.3


def cx(x):
    return CX0 + (x - 230) * S


def cyb(y):
    return CY0 + (y - 260) * S


# the slide's path, point by point (x, y in slide pixels)
PTS = [(240, 950), (262, 870), (276, 892), (300, 760), (309, 778), (320, 697), (345, 765), (356, 745), (420, 833),
       (440, 760), (450, 782), (470, 650), (486, 672), (515, 480), (535, 510), (565, 425),
       (592, 500), (622, 440), (665, 605),
       (693, 465), (703, 500), (717, 478), (735, 590), (745, 545), (772, 650),
       (790, 565), (805, 615), (812, 600), (833, 712),
       (862, 640), (875, 690), (888, 672), (913, 795), (930, 740), (943, 775),
       (965, 665), (1000, 725), (1037, 580),
       (1075, 705), (1100, 625), (1112, 650), (1138, 500), (1160, 580), (1180, 545), (1193, 615),
       (1218, 530), (1235, 575), (1243, 548), (1250, 580), (1272, 455), (1284, 405)]
STEP = 6.0     # slide pixels per candle

SWAP = {"bullish": "bearish", "long": "short", "longs": "shorts", "demand": "supply", "high": "low", "highs": "lows",
        "discount": "premium", "buy": "sell", "HL": "LH", "HH": "LL", "up": "down", "higher": "lower", "below": "above", "top": "bottom"}
SWAP.update({v: k for k, v in list(SWAP.items())})


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


def candles(seed=4):
    random.seed(seed)
    out = []
    prev = PTS[0][1] + 6
    for (x0, y0), (x1, y1) in zip(PTS, PTS[1:]):
        n = max(1, round((x1 - x0) / STEP))
        for k in range(1, n + 1):
            x = x0 + (x1 - x0) * k / n
            y = y0 + (y1 - y0) * k / n + random.uniform(-4, 4)
            o, c = prev, y
            hi = min(o, c) - random.uniform(2, 9)       # slide y grows downward: the high is the smaller y
            lo = max(o, c) + random.uniform(2, 9)
            out.append((x, o, hi, lo, c))
            prev = c
    # the turning points get their exact wick
    return out


def build(bull):
    my = (lambda y: y) if bull else (lambda y: 1220 - y)
    Y = lambda y: cyb(my(y))
    X = cx
    t = (lambda s: s) if bull else swap
    G, RD = "#16a34a", "#dc2626"
    DEM, SUP = (G, RD) if bull else (RD, G)
    o = []
    a = o.append
    esc = html.escape
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

    # ── header ──
    a(f'<text x="820" y="46" font-size="30" font-weight="800" fill="#111" text-anchor="middle">TRADE PLAN · {"BUYS" if bull else "SELLS"}</text>')
    a('<text x="820" y="76" font-size="20" fill="#222" text-anchor="middle">MEDIUM TIMEFRAME PHASES</text>')
    a('<text x="820" y="100" font-size="14" font-style="italic" fill="#444" text-anchor="middle">HTF objective → MTF POIs → LTF execution</text>')
    rows = [("", "SWING", "DAY", ""), ("HTF", "1D", "4H", "Narrative · signals an MTF trend change"),
            ("MTF", "4H / 1H", "M15", "Bias + POIs · fulfils the HTF objective"), ("LTF", "M15", "M5 / M1", "Execution at the MTF POIs")]
    for k, (r0, r1, r2, r3) in enumerate(rows):
        yy = 34 + k * 20
        w_ = 3 if r0 == "HTF" else 1.6 if r0 == "MTF" else 1
        if r0:
            a(f'<line x1="50" y1="{yy - 4}" x2="90" y2="{yy - 4}" stroke="#111" stroke-width="{w_}"/>')
        a(f'<text x="98" y="{yy}" font-size="12" font-weight="700" fill="#111">{r0}</text><text x="140" y="{yy}" font-size="12" fill="#333">{r1}</text>'
          f'<text x="200" y="{yy}" font-size="12" fill="#333">{r2}</text><text x="262" y="{yy}" font-size="11.5" fill="#333">{esc(r3)}</text>')
    left = ["Always start on the HTF for the bias and narrative; work down for timing and refinement.",
            "Look for the exchange in supply and demand: who is in control? Where is the liquidity (who is being induced)?"]
    for k, ln in enumerate(left):
        a(f'<text x="50" y="{128 + k * 18}" font-size="12" fill="#333">{esc(ln)}</text>')
    a('<text x="1100" y="30" font-size="13" font-weight="700" fill="#111">Always ask:</text>')
    a('<text x="1100" y="50" font-size="13" fill="#111">→ What is the current objective?</text>')
    a('<text x="1100" y="70" font-size="13" fill="#111">→ What has been mitigated?</text>')
    a('<text x="1100" y="100" font-size="13" fill="#7c3aed" font-weight="700">Trade from STRONG structure · target WEAK structure</text>')

    # ── zones (slide boxes) ──
    def box(x0, y0, x1, y1, col, op, txt='', tside='right', tcol=None):
        ya, yb = sorted((Y(y0), Y(y1)))
        a(f'<rect x="{X(x0):.1f}" y="{ya:.1f}" width="{X(x1) - X(x0):.1f}" height="{yb - ya:.1f}" fill="{col}" opacity="{op}" stroke="{col}" stroke-opacity="0.5"/>')
        if txt:
            if tside in ('right', 'left'):
                tx = X(x1) + 4 if tside == 'right' else X(x0) - 4
                anc = 'start' if tside == 'right' else 'end'
                a(f'<text x="{tx:.1f}" y="{(ya + yb) / 2 + 4:.1f}" font-size="11.5" font-weight="600" fill="{tcol or col}" text-anchor="{anc}">{esc(txt)}</text>')
            else:   # outer side of the box, away from price: 'out' = above in buys for supply etc.
                top_ = (tside == 'top') == bull
                ty = ya - 6 if top_ else yb + 15
                a(f'<text x="{(X(x0) + X(x1)) / 2:.1f}" y="{ty:.1f}" font-size="11.5" font-weight="600" fill="{tcol or col}" text-anchor="middle">{esc(txt)}</text>')

    # swing EQ: strong low 833 / weak high 425 → 629; discount below (buys)
    eqy = (833 + 425) / 2
    a(f'<rect x="{X(565):.1f}" y="{min(Y(eqy), Y(833)):.1f}" width="{X(1290) - X(565):.1f}" height="{abs(Y(833) - Y(eqy)):.1f}" fill="{DEM}" opacity="0.045"/>')
    a(f'<line x1="{X(565):.1f}" y1="{Y(eqy):.1f}" x2="{X(1290):.1f}" y2="{Y(eqy):.1f}" stroke="#888" stroke-dasharray="8 6"/>')
    a(f'<text x="{X(1290):.1f}" y="{Y(eqy) + (16 if bull else -8):.1f}" font-size="12" fill="#666" text-anchor="end">MTF swing EQ 50% · {t("discount below")}</text>')

    box(432, 593, 515, 673, DEM, 0.13, t("MTF demand"), 'left')
    box(532, 393, 597, 450, SUP, 0.18, t("HTF / MTF supply"), 'top')
    box(670, 445, 750, 535, SUP, 0.16, t("MTF supply"), 'right')
    box(752, 560, 1060, 585, SUP, 0.08)
    box(860, 628, 1060, 650, SUP, 0.08)
    box(888, 710, 980, 810, "#7c3aed", 0.13, t("7 · extreme HTF + stacked MTF demand"), 'bottom', "#6d28d9")
    box(1028, 643, 1135, 745, DEM, 0.12, t("MTF demand"), 'right')
    box(1140, 522, 1290, 645, DEM, 0.10, t("MTF demand"), 'right')

    # ── candles ──
    cs = candles()
    bw = STEP * S * 0.62
    for x, op, hi, lo, c in cs:
        up = (c < op) if bull else (c > op)          # slide y down = price up
        a(f'<line x1="{X(x):.1f}" y1="{Y(hi):.1f}" x2="{X(x):.1f}" y2="{Y(lo):.1f}" stroke="#1e3a8a" stroke-width="1"/>')
        ya, yb = sorted((Y(op), Y(c)))
        a(f'<rect x="{X(x) - bw / 2:.1f}" y="{ya:.1f}" width="{bw:.1f}" height="{max(yb - ya, 1.2):.1f}" fill="{"#ffffff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')

    # ── structure lines ──
    def hl(x0, x1, y, txt, col='#111', w=2.6, dash='', pos='end', above=True, size=12, bold=True):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<line x1="{X(x0):.1f}" y1="{Y(y):.1f}" x2="{X(x1):.1f}" y2="{Y(y):.1f}" stroke="{col}" stroke-width="{w}"{d}/>')
        if txt:
            up_ = above if bull else not above
            ty = Y(y) - 6 if up_ else Y(y) + 15
            tx = X(x1) if pos == 'end' else X(760) if pos == 'start' else (X(x0) + X(x1)) / 2
            anc = 'end' if pos == 'end' else 'start' if pos == 'start' else 'middle'
            a(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="{size}" font-weight="{700 if bold else 500}" fill="{col}" text-anchor="{anc}">{esc(txt)}</text>')

    hl(320, 410, 697, "BOS", '#111', 1.6, '', 'mid')
    hl(565, 1290, 425, t("MTF SWING HIGH (WEAK) · the target"), '#111', 2.4, '', 'start')
    hl(420, 1290, 833, t("MTF SWING LOW (STRONG) · protected"), '#111', 2.4, '', 'end', False)
    BEAR, BULL = (RD, G) if bull else (G, RD)
    # pullback start: CH (wick) then i-BOS (body close)
    hl(592, 640, 500, "CHoCH", BEAR, 1.3, '3 3', 'mid', False, 11.5)
    hl(535, 652, 510, "i-BOS", BEAR, 1.5, '1.5 3', 'end', False, 11.5)
    # internal lower lows during the pullback
    hl(665, 768, 605, "i-BOS", BEAR, 1.2, '1.5 3', 'mid', False, 10.5, False)
    hl(772, 828, 650, "i-BOS", BEAR, 1.2, '1.5 3', 'mid', False, 10.5, False)
    hl(833, 905, 712, "i-BOS", BEAR, 1.2, '1.5 3', 'mid', False, 10.5, False)
    # pullback end: CH (wick) then i-BOS (body close)
    hl(930, 962, 740, "CHoCH", BULL, 1.3, '3 3', 'mid', True, 11.5)
    hl(862, 1033, 640, "i-BOS", BULL, 1.5, '1.5 3', 'end', True, 11.5)
    hl(1138, 1268, 500, "", BULL, 1.2, '1.5 3')
    hl(565, 1278, 425, "", '#111', 2.4)
    a(f'<text x="{X(1262):.1f}" y="{Y(425) + (-24 if bull else 32):.1f}" font-size="12" font-weight="700" fill="{BULL}" text-anchor="end">BOS</text>')

    # mitigation circles
    for x, y in [(565, 425), (693, 465), (717, 478), (790, 565), (862, 640), (913, 795), (943, 775), (1075, 705), (1193, 615), (1250, 580)]:
        a(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="10" fill="none" stroke="#777" stroke-width="1.2"/>')

    # ── CH / i-BOS call-outs (the pullback) ──
    def badge(x, y, ch, col, dy):
        bx_, by_ = X(x), Y(y) + (dy if bull else -dy)
        a(f'<circle cx="{bx_:.1f}" cy="{by_:.1f}" r="10" fill="{col}"/><text x="{bx_:.1f}" y="{by_ + 4:.1f}" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">{ch}</text>')
    badge(604, 500, "a", BEAR, 22)
    badge(652, 510, "b", BEAR, 40)
    badge(946, 740, "c", BULL, -22)
    badge(1037, 640, "d", BULL, 28)
    PB = [("a", BEAR, t("Bearish CHoCH (wick through the last fractal low): the internal pullback is starting. Early sign only.")),
          ("b", BEAR, t("Bearish i-BOS (body close through the strong internal low): the swing pullback is confirmed; the swing high is now fixed = WEAK, the target.")),
          ("c", BULL, t("Bullish CHoCH (wick through the last fractal high): the internal pullback is ending. Early sign: the swing HL may be forming.")),
          ("d", BULL, t("Bullish i-BOS (body close through the strong internal high): internal back in line with the swing = phase A."))]
    pbx, pby = 150, (975 if bull else 1340 - 975 - 164)
    a(f'<rect x="{pbx}" y="{pby}" width="588" height="164" rx="8" fill="#fff" stroke="#cfcfcf"/>')
    a(f'<text x="{pbx + 12}" y="{pby + 20}" font-size="13" font-weight="800" fill="#111">How the pullback is marked</text>')
    yy0 = pby + 40
    for ch, col, txt in PB:
        lines = textwrap.wrap(txt, 88)
        a(f'<circle cx="{pbx + 22}" cy="{yy0 - 4}" r="9" fill="{col}"/><text x="{pbx + 22}" y="{yy0}" font-size="11" font-weight="800" fill="#fff" text-anchor="middle">{ch}</text>')
        for k, ln in enumerate(lines):
            a(f'<text x="{pbx + 38}" y="{yy0 + 14 * k}" font-size="11.5" fill="#222">{esc(ln)}</text>')
        yy0 += 14 * len(lines) + 6

    # ── numbered notes (the slide's descriptions) ──
    NOTES = [
        (1, (330, 545), (432, 633), "Consider long continuations after a BOS from MTF POIs following MTF order flow, but be aware a swing pullback can start. Quick targets. Ideally only do this at the start of a new trend (momentum is strong) and with no nearby key opposing levels (S&D / structure)."),
        (2, (575, 300), (565, 425), "After the MTF BOS, expect an MTF swing pullback: mitigation of HTF / MTF supply, MTF CHoCH / i-BOS. Target MTF demand in discount. If the HTF is bearish, could the HTF swing pullback be complete? Then the MTF swing trend may be about to switch bearish."),
        (3, (400, 425), (560, 425), "You MUST wait for an MTF POI mitigation before looking for an LTF entry model, otherwise wait for an MTF CHoCH / i-BOS to form a fresh MTF POI. The latter is recommended when trading counter-trend / counter order flow."),
        (4, (890, 345), (720, 470), "Trade pro MTF order flow into discount demand. Objective: play the MTF swing pullback, or anticipate an MTF swing reversal if the HTF suggests it."),
        (5, (640, 680), (665, 605), "Don't buy weak lows."),
        (6, (680, 760), (772, 650), "Cautious with shorts in swing discount."),
        (7, (880, 885), (913, 795), "Extreme HTF + stacked MTF demand mitigated: the last area that needs to hold price if the bullish MTF swing trend is to continue, so you may want to be more aggressive looking for longs. Is it pro HTF trend? Well priced on the HTF? Or is the HTF swing pullback likely complete and the MTF could switch bearish?"),
        (8, (950, 590), (943, 775), "Poor-odds shorts: against the swing POI mitigation. The swing pullback is likely complete."),
        (9, (1040, 520), (1037, 580), "MTF internal now bullish. Supply just provides pullbacks."),
        (10, (1165, 785), (1193, 615), "Full MTF alignment to target the weak swing high."),
    ]
    for num, (bx_, by_), (px, py), txt in NOTES:
        lines = textwrap.wrap(t(txt), 44)
        bwid, bht = min(300, max(len(ln) for ln in lines) * 6.4 + 46), 26 + 15 * len(lines)
        bx = X(bx_) - bwid / 2
        bcy = Y(by_)
        by = bcy - bht / 2
        bx = min(max(bx, 50), X(1290) - bwid)
        by = min(max(by, 200), 1120 - bht)
        tx, ty = X(px), Y(py)
        ex = min(max(tx, bx), bx + bwid)
        ey = by if ty < by else by + bht if ty > by + bht else ty
        a(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#bbb"/>')
        a(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bwid}" height="{bht}" rx="6" fill="#fff" stroke="#cfcfcf"/>')
        a(f'<circle cx="{bx + 15:.1f}" cy="{by + 16:.1f}" r="10" fill="#7c3aed"/><text x="{bx + 15:.1f}" y="{by + 20:.1f}" font-size="12" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
        for k, ln in enumerate(lines):
            a(f'<text x="{bx + 32:.1f}" y="{by + 20 + 15 * k:.1f}" font-size="12" fill="#222">{esc(ln)}</text>')

    # ── phase strip ──
    sy = 1150
    PH = [(565, 652, "#ef4444", t("D · shorts: no POI mitigated, no strong liquidity taken: wait for the i-BOS")),
          (652, 905, "#f59e0b", t("C · shorts: i-BOS → internal now bearish: play the MTF swing pullback, decent R:R to swing discount")),
          (905, 1037, "#f59e0b", t("B · longs: extreme demand mitigated in discount: likely end of the pullback")),
          (1037, 1290, "#16a34a", t("A · longs: swing + internal aligned: target the weak swing high"))]
    for x0, x1, col, txt in PH:
        a(f'<rect x="{X(x0):.1f}" y="{sy}" width="{X(x1) - X(x0) - 3:.1f}" height="54" rx="6" fill="{col}" opacity="0.16"/>')
        for k, ln in enumerate(textwrap.wrap(txt, int((X(x1) - X(x0)) / 6.6))[:3]):
            a(f'<text x="{X(x0) + 8:.1f}" y="{sy + 17 + 15 * k}" font-size="11.5" fill="#222">{esc(ln)}</text>')
    a(f'<text x="{X(560):.1f}" y="{sy + 30}" font-size="13" font-weight="700" fill="#444" text-anchor="end">MTF phase →</text>')
    ly = sy + 78
    a(f'<line x1="60" y1="{ly}" x2="100" y2="{ly}" stroke="#111" stroke-width="2.4"/><text x="108" y="{ly + 5}" font-size="13">MTF swing (BOS: body close)</text>')
    a(f'<line x1="330" y1="{ly}" x2="370" y2="{ly}" stroke="#666" stroke-width="1.5" stroke-dasharray="1.5 3"/><text x="378" y="{ly + 5}" font-size="13">i-BOS (internal, body close)</text>')
    a(f'<line x1="600" y1="{ly}" x2="640" y2="{ly}" stroke="#666" stroke-dasharray="3 3"/><text x="648" y="{ly + 5}" font-size="13">CHoCH (fractal, wick)</text>')
    a(f'<circle cx="860" cy="{ly}" r="9" fill="none" stroke="#777"/><text x="876" y="{ly + 5}" font-size="13">POI mitigated</text>')

    # ── MTF phases panel ──
    PX0, PX1 = 1560, 2210
    a(f'<rect x="{PX0}" y="16" width="{PX1 - PX0}" height="{H - 32}" rx="10" fill="#f8f7fc" stroke="#e4e0f3"/>')
    a(f'<text x="{(PX0 + PX1) / 2}" y="50" font-size="20" font-weight="800" fill="#111" text-anchor="middle">MTF PHASES</text>')
    a(f'<text x="{(PX0 + PX1) / 2}" y="70" font-size="12.5" fill="#555" text-anchor="middle">Use the HTF to set how aggressive you are</text>')
    PANEL = [
        ("A → PRO SWING + PRO INTERNAL", "#16a34a", [
            "Objective: target the weak MTF swing high / low; play the pro MTF swing trend run.",
            "Full MTF alignment: the MTF swing pullback is finished; follow the MTF internal structure.",
            "No MTF CHoCH needed at the MTF POI mitigation: go straight to the LTF entry model."]),
        ("B → PRO SWING + COUNTER INTERNAL", "#d97706", [
            "Objective: anticipate the end of the swing pullback (+ internal reversal).",
            "Best used: the MTF swing pullback is likely finishing · pulled back past the MTF swing EQ · premium / discount (extreme) MTF / HTF POI mitigated.",
            "Enough R:R to internal S&D / the strong high / low?",
            "Optional: wait for the MTF CHoCH (consider it if an unmitigated MTF / HTF POI is behind).",
            "If the HTF suggests the MTF could reverse, wait for the MTF i-BOS (phase A)."]),
        ("C → COUNTER SWING + PRO INTERNAL", "#d97706", [
            "Objective: play the MTF swing pullback, or anticipate an MTF swing reversal if the HTF suggests it.",
            "Best used: after an HTF POI mitigation · after the MTF swing BOS · at the start of the MTF swing pullback (before the swing EQ).",
            "Optional: wait for the MTF CHoCH."]),
        ("D → COUNTER SWING + COUNTER INTERNAL", "#dc2626", [
            "Very aggressive: avoid until you are already consistently profitable!",
            "Objective: play the internal pullback, or anticipate an MTF internal reversal for the MTF swing pullback.",
            "Best used: after the MTF swing BOS (expecting the swing pullback; avoid it when the swing pullback has just ended, #9) · after an HTF POI mitigation (a refined MTF POI is even better) · after an MTF CHoCH from the HTF / MTF POI mitigation · after a strong MTF liquidation · pro HTF trend (HTF swing pullback complete) · enough R:R into the strong internal high / low.",
            "Summary: either don't trade this phase, or at minimum wait for an M15 CHoCH."]),
        ("RANGE", "#555", [
            "No clear MTF / HTF intention: stay out of the middle. Longs: bottom 33%. Shorts: top 33%. Or wait for the breakout."]),
    ]
    yy = 104
    for head, col, items in PANEL:
        a(f'<rect x="{PX0 + 18}" y="{yy - 15}" width="{len(head) * 8.2 + 16:.0f}" height="22" rx="4" fill="{col}" opacity="0.14"/>')
        a(f'<text x="{PX0 + 26}" y="{yy}" font-size="13.5" font-weight="800" fill="{col}">{esc(head)}</text>')
        yy += 22
        for it in items:
            for k, ln in enumerate(textwrap.wrap(it, 80)):
                a(f'<text x="{PX0 + (26 if k == 0 else 38)}" y="{yy}" font-size="12.2" fill="#222">{"• " if k == 0 else ""}{esc(ln)}</text>')
                yy += 16
            yy += 3
        yy += 18
    a('</svg>')
    name = 'MTF_Phases_Buys' if bull else 'MTF_Phases_Sells'
    open(f'C:/Users/u/Documents/{name}.svg', 'w', encoding='utf-8').write('\n'.join(o))
    print(name, len(cs), 'candles')


build(True)
build(False)
