"""MTF Storyline (user, 2026-11-02): the flow from the user's EURUSD Dec 2019 - Feb 2020 replay
screenshots, drawn before the script is rebuilt. Buys and the mirrored sells, H4 candles.
Output: Documents/MTF_Storyline_Buys.svg / MTF_Storyline_Sells.svg (+ PNG)."""
import html
import random
import re

W, H = 2240, 1180
L, R, T, B = 60, 1420, 110, 900
esc = html.escape

# H4 path: Daily breakout -> H4 bullish conts -> top -> pullback break -> H4 bearish cont ->
# H4 pullback (range) -> inner high -> H4 bearish cont (range high = the high that took out the low)
# -> H4 pullback back in line -> Daily range high taken
WAY = [(0, 88), (3, 95.5), (6, 91.5), (9, 97.5), (11, 96.2), (13, 101), (15, 103.8), (17, 101.8),
       (20, 105.8), (22, 104.2), (25, 108.2), (27, 107.2), (30, 112), (32, 108.6), (34, 110),
       (37, 103.4), (39, 105.4), (42, 101.2), (45, 106.8), (47, 104.2), (48, 105.6), (51, 100.4),
       (54, 98.6), (56, 102.2), (57, 101.2), (60, 107.4), (62, 106.4), (65, 113.2), (69, 116)]

SWAP = {"bullish": "bearish", "high": "low", "highs": "lows", "discount": "premium", "buy": "sell",
        "buys": "sells", "BUYS": "SELLS", "up": "down", "below": "above", "lower": "higher",
        "higher": "lower", "above": "below", "Bullish": "Bearish"}
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
    return re.sub(r"[A-Za-z]+", rep, t)


def candles(way, seed, noise=0.35, wick=0.8):
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
    G, RD, PU, BL, OR = "#16a34a", "#dc2626", "#7c3aed", "#0284c7", "#ea580c"
    WITH, AGAINST = (G, RD) if bull else (RD, G)
    cs = candles(WAY, 11, 0.12, 0.5)
    n = len(cs)
    lo, hi = 84, 118
    dx = (R - L) / (n + 3)
    X = lambda i: L + dx * (i + 0.5)
    Y = (lambda p: B - (p - lo) / (hi - lo) * (B - T)) if bull else (lambda p: T + (p - lo) / (hi - lo) * (B - T))
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    a(f'<text x="{L}" y="46" font-size="28" font-weight="800" fill="#111">MTF STORYLINE · DAILY → H4 · {"BUYS" if bull else "SELLS"}</text>')
    a(f'<text x="{L}" y="76" font-size="16" fill="#444">{esc(t("H4 candles. Breaks are body closes (H4 close beyond an H4 level, Daily close beyond the Daily wick level). Only External breaks of the current leg count."))}</text>')

    def txt(x, y, s_, col, size=12, anchor="start", bold=True):
        a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col}" text-anchor="{anchor}">{esc(t(s_))}</text>')

    def hline(i0, i1, p, col, dash="", w=1.6, op=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        a(f'<line x1="{X(i0):.1f}" y1="{Y(p):.1f}" x2="{X(i1):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{w}" opacity="{op}"{d}/>')

    def brk(i0, i1, p, s_, col, above=True):
        # a break line from the level to the candle that broke it, with its name
        hline(i0, i1, p, col, "3 3", 1.5)
        up_ = above == bull
        txt((X(i0) + X(i1)) / 2, Y(p) + (-6 if up_ else 15), s_, col, 11.5, "middle")

    def tag(i, p, s_, col, below=False):
        s_ = t(s_)
        w_ = 10 + len(s_) * 7.3
        x, y = X(i) - w_ / 2, Y(p) + (14 if below == bull else -34)
        a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="22" rx="5" fill="{col}"/>')
        a(f'<text x="{X(i):.1f}" y="{y + 15.5:.1f}" font-size="12.5" font-weight="800" fill="#fff" text-anchor="middle">{esc(s_)}</text>')

    def step(i, p, k):
        a(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="12" fill="#111"/><text x="{X(i):.1f}" y="{Y(p) + 4.5:.1f}" font-size="13" font-weight="800" fill="#fff" text-anchor="middle">{k}</text>')

    HI_ = lambda i0, i1: max(range(i0, i1 + 1), key=lambda i: cs[i][1])
    LO_ = lambda i0, i1: min(range(i0, i1 + 1), key=lambda i: cs[i][2])
    hh = lambda i: cs[i][1]
    ll = lambda i: cs[i][2]
    first = lambda i0, f: next(i for i in range(i0, n) if f(cs[i][3]))
    iDH = HI_(1, 5); DH = hh(iDH)
    iBO = first(iDH + 2, lambda c: c > DH)
    iA1 = HI_(14, 16); iL1 = LO_(16, 18); iC1 = first(iL1 + 1, lambda c: c > hh(iA1))
    iA2 = HI_(19, 21); iL2 = LO_(21, 23); iC2 = first(iL2 + 1, lambda c: c > hh(iA2))
    iTOP = HI_(28, 31); TOP = hh(iTOP)
    iL0 = LO_(26, 28)                      # the last low that made a new high (the dip before the top)
    iPB = first(iTOP + 1, lambda c: c < ll(iL0))
    iL3 = LO_(36, 38); iH3 = HI_(38, 40); iC3 = first(iH3 + 1, lambda c: c < ll(iL3))
    iRL = LO_(iC3, 43); iP1 = first(iRL + 1, lambda c: c > hh(iH3))
    iH4 = HI_(iP1, 46); iIN = HI_(47, 49); iC4 = first(iIN + 1, lambda c: c < ll(iRL))
    iRL2 = LO_(iC4, 56); iP2 = first(iRL2 + 1, lambda c: c > hh(iH4))
    iDT = first(iP2 + 1, lambda c: c > TOP)
    RLOW = ll(LO_(0, 2)); MID = (TOP + RLOW) / 2

    # Daily range after the pullback break
    ya, yb = sorted((Y(RLOW), Y(MID)))
    a(f'<rect x="{X(iPB):.1f}" y="{ya:.1f}" width="{X(n + 1) - X(iPB):.1f}" height="{yb - ya:.1f}" fill="{WITH}" opacity="0.05"/>')
    ya, yb = sorted((Y(MID), Y(TOP)))
    a(f'<rect x="{X(iPB):.1f}" y="{ya:.1f}" width="{X(n + 1) - X(iPB):.1f}" height="{yb - ya:.1f}" fill="{AGAINST}" opacity="0.04"/>')
    hline(0, n + 1, RLOW, "#111", "", 2)
    txt(X(n + 1) + 6, Y(RLOW) + 4, "Daily bullish external low · Daily range low", "#111")
    hline(iTOP, n + 1, TOP, "#111", "", 2)
    txt(X(n + 1) + 6, Y(TOP) + 4, "Daily + H4 range high", "#111")
    txt(X(n + 1) + 6, Y(TOP) + 20 if bull else Y(TOP) - 12, "(has to go for Daily to continue bullish)", "#555", 11, bold=False)
    hline(iPB, n + 1, MID, "#888", "6 6", 1.3)
    txt(X(n + 1) + 6, Y(MID) + 4, "Daily range 0.5 · discount below", "#666", 11.5)
    hline(iDH, iBO, DH, "#111", "", 2)
    txt(X(iDH), Y(DH) + (-8 if bull else 18), "Daily external high", "#111", 11.5)

    # candles
    for i, (op, h, l, c) in enumerate(cs):
        up_ = (c >= op) if bull else (c < op)
        a(f'<line x1="{X(i):.1f}" y1="{Y(h):.1f}" x2="{X(i):.1f}" y2="{Y(l):.1f}" stroke="#1e3a8a" stroke-width="1.1"/>')
        y1, y2 = sorted((Y(op), Y(c)))
        a(f'<rect x="{X(i) - dx * 0.32:.1f}" y="{y1:.1f}" width="{dx * 0.64:.1f}" height="{max(y2 - y1, 1.3):.1f}" fill="{"#ffffff" if up_ else "#1e3a8a"}" stroke="#1e3a8a"/>')

    # 1 Daily breakout, labelled where it happened
    tag(iBO, hh(iBO) + 0.4, "Daily breakout", "#111")
    step(iBO, ll(iBO) - 1.6, 1)
    # 2 H4 bullish conts; the pullback line = the last H4 low that made a new low
    brk(iA1, iC1, hh(iA1), "H4 bullish cont", WITH)
    brk(iA2, iC2, hh(iA2), "H4 bullish cont", WITH)
    hline(iL1, iL2, ll(iL1), BL, "", 2, 0.3)
    hline(iL2, iL0, ll(iL2), BL, "", 2, 0.3)
    hline(iL0, iPB, ll(iL0), BL, "", 2.6)
    txt(X(iL0) + 6, Y(ll(iL0)) + (16 if bull else -8), "pullback line: the last H4 low that made a new high", BL, 11.5)
    step(iC2 + 1, hh(iA2) + 4.5, 2)
    # 3 Pullback break
    brk(iL0, iPB, ll(iL0), "", AGAINST)
    tag(iPB - 7, ll(iL2) - 1.2, "Pullback break · Daily pullback confirmed", AGAINST, below=True)
    step(iPB + 1, ll(iPB + 1) - 1.6, 3)
    # 4 H4 bearish cont; the last H4 high is tracked
    brk(iL3, iC3, ll(iL3), "H4 bearish cont", AGAINST, above=False)
    hline(iH3, iP1, hh(iH3), OR, "", 2.2)
    step(iC3, ll(iC3) - 1.8, 4)
    # 5 H4 pullback -> H4 range
    brk(iH3, iP1, hh(iH3), "H4 pullback", WITH)
    hline(iRL, iC4, ll(iRL), OR, "", 2.2)
    txt(X(iRL) + 4, Y(ll(iRL)) + (-6 if bull else 16), "H4 range low", OR, 11.5)
    step(iP1 + 1, hh(iP1) + 4.0, 5)
    # 6 inner high vs the high that took out the low
    txt(X(iIN), Y(hh(iIN)) + (-10 if bull else 20), "inner high: still inside the leg", "#888", 11, "middle")
    brk(iRL, iC4, ll(iRL), "H4 bearish cont", AGAINST, above=False)
    hline(iH4, iP2, hh(iH4), OR, "", 2.2)
    txt(X(iH4), Y(hh(iH4)) + (-26 if bull else 34), "H4 range high: the high that took out the low", OR, 11)
    txt(X(iH4), Y(hh(iH4)) + (-12 if bull else 48), "(has to go for H4 not to be bearish)", OR, 10.5, bold=False)
    step(iC4 + 1, ll(iC4 + 1) - 1.8, 6)
    # 7 H4 pullback again = back in alignment
    brk(iH4, iP2, hh(iH4), "", WITH)
    tag(iP2, hh(iP2) + 2.0, "H4 pullback · back in alignment with Daily", G if bull else RD)
    hline(iRL2, n, ll(iRL2), OR, "", 1.8, 0.6)
    txt(X(n + 1) + 6, Y(ll(iRL2)) + 4, "new H4 range low", OR, 11.5)
    step(iRL2, ll(iRL2) - 1.8, 7)
    # 8 the Daily range high taken
    brk(iTOP, iDT, TOP, "", WITH)
    tag(iDT, hh(iDT) + 2.6, "Daily range high taken: Daily continues bullish", "#111")
    step(iDT + 2, TOP - 3.0, 8)

    # the story (right panel)
    PX = 1880
    a(f'<rect x="{PX - 20}" y="96" width="{W - PX}" height="1060" rx="12" fill="#f8f7ff" stroke="#ddd6fe"/>')
    txt(PX, 128, "THE STORY (BUYS)", "#4c1d95", 18)
    notes = [
        "Daily breakout: a Daily body close beyond the Daily external high. The label sits where the breakout happened.",
        "Until the Daily pulls back, every External H4 break up is labelled H4 bullish cont. In a bullish move lows take out highs: the pullback line is the last H4 low that made a new high (one line, it moves up with each new high).",
        "An H4 body close below the pullback line = Pullback break: the Daily pullback is confirmed. Daily range: high (also the H4 range high), low, 0.5.",
        "H4 is now bearish inside the bullish Daily: each External H4 break down = H4 bearish cont (the Daily pullback goes on). In a bearish move highs take out lows: the last H4 high that made a new low is tracked.",
        "An H4 close above the last H4 high = H4 pullback (Daily continuation / bullish alignment). H4 range: the H4 low up to the Daily range high.",
        "If H4 breaks the H4 range low again = H4 bearish cont. The new H4 range high is the high that took out the low, not an inner high of the leg. It has to go for H4 not to be bearish.",
        "H4 takes out that high = H4 pullback, H4 back in alignment with the Daily. New H4 range low.",
        "The Daily range high taken = Daily continues bullish. A Daily close below the Daily range low instead = Daily turns bearish and the same story runs mirrored.",
    ]
    yy = 164
    for k, s_ in enumerate(notes, 1):
        a(f'<circle cx="{PX + 10}" cy="{yy - 5}" r="11" fill="#111"/><text x="{PX + 10}" y="{yy - 0.5}" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">{k}</text>')
        words, line_, lines = t(s_).split(), "", []
        for w_ in words:
            if len(line_) + len(w_) > 40:
                lines.append(line_)
                line_ = w_
            else:
                line_ = (line_ + " " + w_).strip()
        lines.append(line_)
        for j, ln in enumerate(lines):
            a(f'<text x="{PX + 30}" y="{yy + j * 17}" font-size="13" fill="#222">{esc(ln)}</text>')
        yy += len(lines) * 17 + 18

    # legend
    LY = 960
    items = [(WITH, "3 3", "H4 bullish cont / H4 pullback (break line to the candle that broke it)"),
             (AGAINST, "3 3", "H4 bearish cont / Pullback break"),
             (BL, "", "pullback line: the last H4 low that made a new high (only the latest)"),
             (OR, "", "last H4 high that made a new low / H4 range high and low"),
             ("#111", "", "Daily external high / low, Daily range"), ("#888", "6 6", "Daily range 0.5")]
    for j, (c, d, s_) in enumerate(items):
        x0, y0 = L + (j % 2) * 820, LY + (j // 2) * 34
        dd = f' stroke-dasharray="{d}"' if d else ''
        a(f'<line x1="{x0}" y1="{y0}" x2="{x0 + 46}" y2="{y0}" stroke="{c}" stroke-width="2.4"{dd}/>')
        txt(x0 + 58, y0 + 4, s_, "#333", 13.5, bold=False)
    a('</svg>')
    return '\n'.join(o)


for bull, name in ((True, "Buys"), (False, "Sells")):
    open(f"C:/Users/u/Documents/MTF_Storyline_{name}.svg", "w", encoding="utf-8").write(build(bull))
print("ok")
