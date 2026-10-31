"""Picture of the planned merge (user, 2026-10-31): the Bias Pointer exactly as it is (KEEP)
plus what Aligned Story adds (NEW). Buys and the mirrored sells. H4 candles, Daily levels on top.
Output: Documents/Merged_Plan_Buys.svg / Merged_Plan_Sells.svg (+ PNG)."""
import html
import random
import re

W, H = 2200, 1300
L, R, T, B = 60, 1360, 120, 860
esc = html.escape

WAY = [(0, 86), (4, 92), (6, 90), (10, 97.5), (13, 96), (16, 101.6), (19, 100.4), (22, 104), (25, 102.4),
       (27, 105.5), (30, 104.2), (34, 108), (36, 106.4), (38, 113), (41, 108), (42, 104.6), (46, 108.5),
       (50, 101.5), (52, 103.5), (55, 96.7), (57, 99), (58, 98), (61, 104.6), (64, 103.0), (67, 106),
       (72, 113.6), (76, 116.5)]

SWAP = {"bullish": "bearish", "demand": "supply", "high": "low", "highs": "lows", "discount": "premium",
        "buy": "sell", "buys": "sells", "BUYS": "SELLS", "up": "down", "below": "above", "lower": "higher",
        "support": "resistance"}
SWAP.update({v: k for k, v in list(SWAP.items()) if v not in SWAP})


def swap(t):
    def rep(m):
        w = m.group(0)
        r = SWAP.get(w) or SWAP.get(w.lower())
        if r is None:
            return w
        if w.isupper() and len(w) > 2:
            return r.upper()
        return r.capitalize() if w[0].isupper() else r
    t = t.replace("V-shape", "\x01").replace("A-shape", "\x02")
    t = re.sub(r"[A-Za-z]+", rep, t)
    return t.replace("\x01", "A-shape").replace("\x02", "V-shape")


def candles(way, seed, noise=0.4, wick=0.9):
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


def build(bull):
    t = (lambda s: s) if bull else swap
    G, RD, PU, BL, GR = "#16a34a", "#dc2626", "#7c3aed", "#2563eb", "#6b7280"
    WITH, AGAINST = (G, RD) if bull else (RD, G)
    cs = candles(WAY, 7)
    n = len(cs)
    lo, hi = 83, 119
    dx = (R - L) / (n + 3)
    X = lambda i: L + dx * (i + 0.5)
    Y = (lambda p: B - (p - lo) / (hi - lo) * (B - T)) if bull else (lambda p: T + (p - lo) / (hi - lo) * (B - T))
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    a(f'<text x="{L}" y="46" font-size="28" font-weight="800" fill="#111">BIAS POINTER + ALIGNED STORY · THE MERGE (TEST) · {"BUYS" if bull else "SELLS"}</text>')
    a(f'<text x="{L}" y="76" font-size="16" fill="#444">Everything the Bias Pointer does stays exactly as it is </text>')
    a(f'<rect x="{L + 440}" y="61" width="52" height="20" rx="4" fill="{BL}"/><text x="{L + 466}" y="76" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">KEEP</text>')
    a(f'<text x="{L + 500}" y="76" font-size="16" fill="#444">· what Aligned Story adds </text>')
    a(f'<rect x="{L + 700}" y="61" width="46" height="20" rx="4" fill="{PU}"/><text x="{L + 723}" y="76" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">NEW</text>')
    a(f'<text x="{L + 754}" y="76" font-size="16" fill="#444">· every NEW part has its own on / off setting. H4 candles; Daily levels on top.</text>')

    def chip(x, y, new):
        c, w_, s_ = (PU, 34, "NEW") if new else (BL, 40, "KEEP")
        a(f'<rect x="{x:.1f}" y="{y - 11:.1f}" width="{w_}" height="15" rx="3" fill="{c}"/>')
        a(f'<text x="{x + w_ / 2:.1f}" y="{y:.1f}" font-size="10" font-weight="800" fill="#fff" text-anchor="middle">{s_}</text>')
        return w_ + 4

    def label(x, y, txt, col, new=None, anchor="start", size=11.5):
        txt = t(txt)
        if new is not None and anchor == "start":
            x += chip(x, y, new)
        a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="700" fill="{col}" text-anchor="{anchor}">{esc(txt)}</text>')

    def box(i0, i1, p1, p2, col, op=0.16):
        ya, yb = sorted((Y(p1), Y(p2)))
        a(f'<rect x="{X(i0) - dx / 2:.1f}" y="{ya:.1f}" width="{X(i1) - X(i0) + dx:.1f}" height="{yb - ya:.1f}" fill="{col}" opacity="{op}" stroke="{col}" stroke-opacity="0.6"/>')
        return ya, yb

    def hline(i0, i1, p, col, dash="", w=1.6, op=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{w}" opacity="{op}"{d}/>')

    def tag(i, p, txt, col, new, below=False):
        txt = t(txt)
        w_ = 9 + len(txt) * 7.2
        x, y = X(i) - w_ / 2, Y(p) + (14 if below else -34)
        a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="22" rx="5" fill="{col}"/>')
        a(f'<text x="{X(i):.1f}" y="{y + 15.5:.1f}" font-size="12.5" font-weight="800" fill="#fff" text-anchor="middle">{esc(txt)}</text>')
        chip(x + w_ + 4, y + 15, new)

    def step(i, p, k):
        a(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="12" fill="#111"/><text x="{X(i):.1f}" y="{Y(p) + 4.5:.1f}" font-size="13" font-weight="800" fill="#fff" text-anchor="middle">{k}</text>')

    # Daily range + 0.5 after the pullback (NEW)
    ya, yb = sorted((Y(86), Y(99.5)))
    a(f'<rect x="{X(42):.1f}" y="{ya:.1f}" width="{X(n + 1) - X(42):.1f}" height="{yb - ya:.1f}" fill="{WITH}" opacity="0.05"/>')
    hline(42, n + 1, 99.5, "#888", "6 6", 1.3)
    label(X(n + 1) + 6, Y(99.5) + 4, "Daily range 0.5", "#666", True)
    hline(0, n + 1, 86, "#111", "", 2)
    label(X(n + 1) + 6, Y(86) + 4, "Daily range low", "#111", True)
    hline(38, n + 1, 113, "#111", "", 2)
    label(X(n + 1) + 6, Y(113) + 4, "Daily range high (target)", "#111", True)

    # Daily levels after the breakout: the Bias Pointer's (KEEP) + demand and merged names (NEW)
    box(44, n, 91.8, 93.8, WITH, 0.13)
    label(X(n + 1) + 6, Y(92.8) + 4, "Daily bullish FVG (box)", WITH, False)
    hline(44, n, 94.8, WITH, "6 3", 1.6)
    label(X(n + 1) + 6, Y(94.8) + 4, "Daily OC (line)", WITH, False)
    box(44, n, 96.0, 98.2, WITH, 0.22)
    hline(44, n, 97.3, WITH, "", 1.6)
    label(X(n + 1) + 6, Y(97.1) + 4, "Daily demand + V-shape (one name)", WITH, True)
    hline(2, 16, 100, "#111", "", 2.2)
    label(X(2), Y(100) + (-8 if bull else 18), "Daily external high (Bias Pointer)", "#111", False)
    hline(16, n, 100, "#111", "8 5", 1.5)
    label(X(n + 1) + 6, Y(100.4) + 4, "Daily Breaker (line)", "#111", False)

    # candles
    for i, (op, h, l, c) in enumerate(cs):
        up = (c >= op) if bull else (c < op)
        a(f'<line x1="{X(i):.1f}" y1="{Y(h):.1f}" x2="{X(i):.1f}" y2="{Y(l):.1f}" stroke="#1e3a8a" stroke-width="1.1"/>')
        y1, y2 = sorted((Y(op), Y(c)))
        a(f'<rect x="{X(i) - dx * 0.32:.1f}" y="{y1:.1f}" width="{dx * 0.64:.1f}" height="{max(y2 - y1, 1.3):.1f}" fill="{"#ffffff" if up else "#1e3a8a"}" stroke="#1e3a8a"/>')

    # 1 Daily breakout (KEEP)
    step(16, 98.3, 1)
    tag(16, 102.8, "Daily breakout", BL, False)

    # 2 H4 continuations + the pullback line + the continuation Breaker (NEW)
    hline(22, 27, 104, PU, "2 3", 1.6)
    label(X(22) - 4, Y(104) + (-6 if bull else 16), "H4 bullish continuation", PU, True, size=11)
    hline(25, 42, 102.4, "#0284c7", "", 2.4, 0.35)
    hline(36, 42, 106.4, "#0284c7", "", 2.6)
    label(X(28), Y(106.4) + (-8 if bull else 16), "pullback line (only the last H4 low)", "#0284c7", True, size=11)
    hline(27, 34, 104, "#f97316", "", 1.8)
    label(X(27) + 2, Y(104) + (16 if bull else -8), "H4 continuation Breaker", "#f97316", True, size=10.5)
    step(24, 106.2, 2)
    tag(30, 102.0, "M15 entry confirmed", PU, True, below=True)
    hline(34, 38, 108, PU, "2 3", 1.6)
    label(X(34) - 4, Y(108) + (-6 if bull else 16), "H4 bullish continuation", PU, True, size=11)

    # 3 Daily pullback confirmed (NEW)
    a(f'<line x1="{X(42):.1f}" y1="{Y(106.4):.1f}" x2="{X(42):.1f}" y2="{Y(104.2):.1f}" stroke="{AGAINST}" stroke-width="2"/>')
    label(X(43), Y(111.6) + 4, "H4 close below the pullback line = Daily pullback confirmed", AGAINST, True, size=11)
    step(41, 110.2, 3)

    # 4 the Bias Pointer watches its Daily levels (KEEP); merged names / demand (NEW)
    step(47, 95.0, 4)
    # 5 reaction + H4 External breakout (KEEP alert) + aligned tag (NEW, newest only)
    hline(52, 61, 103.5, AGAINST, "2 3", 1.6)
    label(X(52), Y(103.5) + (-6 if bull else 16), "H4 External breakout", AGAINST, False, size=11)
    step(55, 94.4, 5)
    tag(61, 107.2, "CONFIRMED · Daily reaction + H4 breakout", BL, False)
    tag(61, 110.2, "Daily + H4 aligned (newest only)", G if bull else RD, True)
    # 6 H4 key levels: H4 reaction alerts (KEEP) + M15 sweep and break (NEW)
    hline(61, n, 103.5, "#f97316", "", 1.6)
    label(X(n + 1) + 6, Y(103.5) + 4, "H4 Breaker / H4 levels", "#f97316", False)
    step(64, 100.6, 6)
    tag(64, 101.6, "H4 Breaker retest (alert)", BL, False, below=True)
    tag(66, 99.4, "M15 entry confirmed (newest only)", PU, True, below=True)
    step(74, 118.0, 7)

    # the story (right panel)
    PX = 1700
    a(f'<rect x="{PX - 20}" y="96" width="{W - PX}" height="820" rx="12" fill="#f8f7ff" stroke="#ddd6fe"/>')
    a(f'<text x="{PX}" y="128" font-size="19" font-weight="800" fill="#4c1d95">{esc(t("THE STORY (BUYS)"))}</text>')
    notes = [
        (False, "Daily external breakout, exactly as the Bias Pointer (Daily close, its alerts)."),
        (True, "Until the Daily pulls back, each H4 External break up is an H4 bullish continuation. The pullback line is the last H4 low (one line). An M15 sweep and break at the H4 continuation Breaker (or another H4 level of the leg) = M15 entry confirmed."),
        (True, "An H4 close below the pullback line = Daily pullback confirmed: Daily range high (target), low and 0.5 drawn."),
        (False, "The Bias Pointer keeps watching its post-breakout Daily levels (V-shape, OC, FVG, Breaker, inside range) with its rules: first touch, a Daily close kills a level. NEW: Daily demand / supply as a reaction level; levels on the same price show as one (Daily demand + V-shape)."),
        (False, "Reaction + H4 External breakout = the Bias Pointer's CONFIRMED alert, as now. NEW: the Daily + H4 aligned tag, only the newest one on the chart."),
        (False, "The Bias Pointer's H4 key-level reactions (Breaker retest, OC, engulfing, H4 FVG) stay. NEW: an M15 sweep and break at those H4 levels = M15 entry confirmed (newest tag only)."),
        (False, "Target: the Daily range high and beyond."),
    ]
    yy = 164
    for k, (new, txt) in enumerate(notes, 1):
        a(f'<circle cx="{PX + 10}" cy="{yy - 5}" r="11" fill="#111"/><text x="{PX + 10}" y="{yy - 0.5}" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">{k}</text>')
        words, line_, lines = t(txt).split(), "", []
        for w_ in words:
            if len(line_) + len(w_) > 50:
                lines.append(line_)
                line_ = w_
            else:
                line_ = (line_ + " " + w_).strip()
        lines.append(line_)
        for j, ln in enumerate(lines):
            a(f'<text x="{PX + 30}" y="{yy + j * 17}" font-size="13" fill="#222">{esc(ln)}</text>')
        yy += len(lines) * 17 + 16

    # the dashboard / settings (bottom)
    DY = 900
    a(f'<rect x="{L}" y="{DY}" width="{W - L - 40}" height="370" rx="12" fill="#fafafa" stroke="#e5e7eb"/>')
    a(f'<text x="{L + 20}" y="{DY + 32}" font-size="18" font-weight="800" fill="#111">SETTINGS: switch each reaction / feature on or off (as the Bias Pointer does now)</text>')
    keep = ["Origin", "Back in line", "H4 breakout in line", "Breaker Origin", "Breaker retest", "OC reaction",
            "Engulfing", "Daily reaction + H4 breakout", "H4 FVG after breakout", "Daily engulfing",
            "External / Internal H4 breakouts", "Weekly storyline"]
    new = ["H4 continuations + pullback line (one line)", "Daily pullback confirmed + range high / low / 0.5",
           "Daily demand / supply as reaction levels", "Merge levels on the same price (one name)",
           "M15 sweep and break entries at H4 continuation levels", "M15 sweep and break entries at H4 key levels",
           "Daily + H4 aligned tag (newest only)", "M15 entry tag (newest only)",
           "Tag colours: the background opacity works", "Story notes / story table", "Line style and colour for every line"]
    for col_i, (items, isnew, hdr) in enumerate(((keep, False, "Bias Pointer reactions (KEEP, unchanged)"), (new, True, "Added from Aligned Story (NEW, each on / off)"))):
        x0 = L + 20 + col_i * 1040
        a(f'<text x="{x0}" y="{DY + 66}" font-size="15" font-weight="800" fill="{PU if isnew else BL}">{esc(hdr)}</text>')
        for j, it in enumerate(items):
            cx, cy = x0 + (j // 6) * 500, DY + 96 + (j % 6) * 40
            a(f'<rect x="{cx}" y="{cy - 14}" width="18" height="18" rx="3" fill="{PU if isnew else BL}"/><text x="{cx + 9}" y="{cy}" font-size="13" font-weight="800" fill="#fff" text-anchor="middle">✓</text>')
            a(f'<text x="{cx + 26}" y="{cy}" font-size="14" fill="#222">{esc(t(it))}</text>')
    a('</svg>')
    return '\n'.join(o)


for bull, name in ((True, "Buys"), (False, "Sells")):
    open(f"C:/Users/u/Documents/Merged_Plan_{name}.svg", "w", encoding="utf-8").write(build(bull))
print("ok")
