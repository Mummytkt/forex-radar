"""MTF Storyline Rulebook: one HTML page with candlestick diagrams (inline SVG, theme-aware).
Run: python docs/rulebook/mtf_storyline/build_mtf_rulebook.py  ->  docs/rulebook/mtf_storyline/index.html
The rules mirror pine/MummyTKT_MTF_Storyline.pine (generator pine/make_mtf_storyline.py)."""
import html
import os
import random
import re

VERSION = "Version 2 · 3 November 2026"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
esc = html.escape

# ── One H4 story (buys), reused by every figure ─────────────────────────────────────────────
WAY = [(0, 96), (3, 99.2), (5, 97.6), (8, 104.6), (10, 103.2), (13, 108.2), (15, 106.4), (18, 111.2),
       (20, 109.5), (23, 114.2), (25, 112.5), (29, 118.6), (31, 116.9), (32, 117.5), (35, 110.4),
       (37, 112.6), (40, 107.1), (42, 109.2), (45, 104.1), (47, 106.3), (50, 101.4), (52, 102.6),
       (55, 108.4), (57, 107.0), (60, 112.2), (62, 110.6), (65, 115.6), (67, 114.1), (71, 121.4)]


def make_candles(way, seed=7, noise=0.22, wick=0.55):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for i in range(a, b):
            path.append(pa + (pb - pa) * (i - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 0.5
    for p in path:
        o, c = prev, p + random.uniform(-noise, noise)
        out.append((o, max(o, c) + random.uniform(0.12, wick), min(o, c) - random.uniform(0.12, wick), c))
        prev = c
    return out


CS = make_candles(WAY)
N = len(CS)
o_ = lambda i: CS[i][0]
c_ = lambda i: CS[i][3]
bh = lambda i: max(o_(i), c_(i))          # body high (story-timeframe levels sit on bodies)
bl = lambda i: min(o_(i), c_(i))
hh = lambda i: CS[i][1]
ll = lambda i: CS[i][2]
imax = lambda a, b, f: max(range(a, b + 1), key=f)
imin = lambda a, b, f: min(range(a, b + 1), key=f)
first = lambda a, f: next(i for i in range(a, N) if f(c_(i)))

# key points of the story, computed from the candles
D_EXT_LO = ll(imin(0, 2, ll))                    # Daily external low (frame)
OLD_HI = 102.6                                   # the Daily external high that breaks
iDB = first(3, lambda c: c > OLD_HI)            # Daily breakout
cont_up = []                                     # H4 bullish cont: (high idx, break idx, dip idx)
for a, b, d0, d1 in ((10, 14, 14, 16), (16, 19, 19, 21), (21, 24, 24, 26)):
    ih = imax(a, b, bh)
    idp = imin(d0, d1, bl)
    ib = first(idp, lambda c, v=bh(ih): c > v)
    cont_up.append((ih, ib, idp))
iTOP = imax(26, 31, hh)
TOP = hh(iTOP)
iPL = cont_up[-1][2]                              # pullback line = the last low that made a new high
PL = bl(iPL)
iPB = first(iTOP + 1, lambda c: c < PL)           # Pullback break
RANGE_MID = (TOP + D_EXT_LO) / 2
cont_dn = []                                      # H4 bearish cont inside the pullback
for a, b, d0, d1 in ((iPB, iPB + 2, 36, 38), (39, 41, 41, 43), (44, 46, 46, 48)):
    il = imin(a, b, bl)
    ih = imax(d0, d1, bh)
    ib = first(ih, lambda c, v=bl(il): c < v)
    cont_dn.append((il, ib, ih))
iHPL = cont_dn[-1][2]                             # H4 pullback line = the last high that made a new low
HPL = bh(iHPL)
iRL = imin(48, 53, bl)                            # the leg's low = H4 range low
RL = bl(iRL)
iHP = first(iRL + 1, lambda c: c > HPL)           # H4 pullback · back in alignment
cont_in = []                                      # H4 bullish cont inside the H4 range
for a, b, d0, d1 in ((iHP, iHP + 2, 56, 58), (59, 61, 61, 63), (64, 66, 66, 68)):
    ih = imax(a, b, bh)
    idp = imin(d0, d1, bl)
    ib = first(idp, lambda c, v=bh(ih): c > v)
    cont_in.append((ih, ib, idp))
iP3 = cont_in[-1][2]
P3 = bl(iP3)
iDC = first(iP3 + 1, lambda c: c > TOP)          # the H4 range high taken: the Daily continues
LO_P, HI_P = 93.0, 124.0

# ── SVG drawing ───────────────────────────────────────────────────────────────────────────────
VW, VH = 1000, 430
PADL, PADR, PADT, PADB = 18, 210, 26, 34


def X(i):
    return PADL + (VW - PADL - PADR) * (i + 0.5) / (N + 1)


def Y(p, flip=False):
    if flip:
        p = LO_P + HI_P - p
    return PADT + (HI_P - p) / (HI_P - LO_P) * (VH - PADT - PADB)


SWAP = {"bullish": "bearish", "high": "low", "highs": "lows", "discount": "premium", "buy": "sell",
        "buys": "sells", "up": "down", "below": "above", "above": "below", "lower": "higher",
        "higher": "lower", "top": "bottom", "Buys": "Sells"}
SWAP.update({v: k for k, v in list(SWAP.items()) if v not in SWAP})


def swap(t):
    def rep(m):
        w = m.group(0)
        r = SWAP.get(w) or SWAP.get(w.lower())
        if r is None:
            return w
        return r.capitalize() if w[0].isupper() else r
    return re.sub(r"[A-Za-z]+", rep, t)


def svg(items, focus=None, flip=False, label="", h=VH):
    """items: ('line', i0, i1, p, cls, text) · ('tag', i, p, text, cls, below) · ('zone', i0, i1, p0, p1, cls, text)
    · ('num', i, p, k) · ('brk', i0, i1, p, cls, text). focus = (a, b): candles outside are faded."""
    t = swap if flip else (lambda s: s)
    yy = lambda p: Y(p, flip)
    o = [f'<svg class="fig" viewBox="0 0 {VW} {h}" role="img" aria-label="{esc(label)}" xmlns="http://www.w3.org/2000/svg">']
    o.append(f'<rect class="plot" x="0" y="0" width="{VW}" height="{h}" rx="10"/>')
    for k in range(5):
        p = LO_P + (HI_P - LO_P) * k / 4
        o.append(f'<line class="grid" x1="{PADL}" x2="{VW - PADR + 6}" y1="{yy(p):.1f}" y2="{yy(p):.1f}"/>')
    for it in items:
        if it[0] == 'zone':
            _, i0, i1, p0, p1, cls, tx = it
            y0, y1 = sorted((yy(p0), yy(p1)))
            o.append(f'<rect class="{cls}" x="{X(i0):.1f}" y="{y0:.1f}" width="{X(i1) - X(i0):.1f}" height="{y1 - y0:.1f}"/>')
            if tx:
                o.append(f'<text class="zt" x="{X(i0) + 6:.1f}" y="{y0 + 14:.1f}">{esc(t(tx))}</text>')
    dx = (VW - PADL - PADR) / (N + 1)
    for i, (op, hi, lo, cl) in enumerate(CS):
        up = cl >= op
        if flip:
            up = not up
        fade = focus is not None and not (focus[0] <= i <= focus[1])
        cls = ("up" if up else "dn") + (" fade" if fade else "")
        y1, y2 = sorted((yy(op), yy(cl)))
        o.append(f'<g class="{cls}"><line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{yy(hi):.1f}" y2="{yy(lo):.1f}"/>'
                 f'<rect x="{X(i) - dx * 0.33:.1f}" y="{y1:.1f}" width="{dx * 0.66:.1f}" height="{max(y2 - y1, 1.2):.1f}" rx="1"/></g>')
    for it in items:
        kind = it[0]
        if kind == 'line':
            _, i0, i1, p, cls, tx = it
            o.append(f'<line class="{cls}" x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{yy(p):.1f}" y2="{yy(p):.1f}"/>')
            if tx:
                o.append(f'<text class="lt {cls}-t" x="{X(i1) + 8:.1f}" y="{yy(p) + 4:.1f}">{esc(t(tx))}</text>')
        elif kind == 'brk':
            _, i0, i1, p, cls, tx = it
            o.append(f'<line class="brk {cls}" x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{yy(p):.1f}" y2="{yy(p):.1f}"/>')
            if tx:
                o.append(f'<text class="bt" x="{(X(i0) + X(i1)) / 2:.1f}" y="{yy(p) - 5:.1f}" text-anchor="middle">{esc(t(tx))}</text>')
        elif kind == 'tag':
            _, i, p, tx, cls, below = it
            tx = t(tx)
            if flip:
                below = not below
            w = 14 + len(tx) * 6.4
            x0 = min(max(X(i) - w / 2, 4), VW - w - 4)
            y0 = yy(p) + 10 if below else yy(p) - 32
            o.append(f'<g class="tag {cls}"><rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="22" rx="5"/>'
                     f'<text x="{x0 + w / 2:.1f}" y="{y0 + 15:.1f}" text-anchor="middle">{esc(tx)}</text></g>')
        elif kind == 'num':
            _, i, p, k = it
            o.append(f'<g class="num"><circle cx="{X(i):.1f}" cy="{yy(p):.1f}" r="11"/>'
                     f'<text x="{X(i):.1f}" y="{yy(p) + 4.5:.1f}" text-anchor="middle">{k}</text></g>')
    o.append('</svg>')
    return ''.join(o)


# ── The annotations of each part of the story ──────────────────────────────────────────────────
def frame(end=N - 1):
    return [('line', 0, end, D_EXT_LO, 'ext', 'Daily external low')]


def f_breakout():
    return frame() + [
        ('line', 0, iDB, OLD_HI, 'ext', ''),
        ('tag', iDB, hh(iDB), 'Daily bullish breakout', 'tg-ink', False),
        ('num', iDB - 3, OLD_HI + 2.4, 1)]


def f_cont():
    it = []
    for ih, ib, idp in cont_up:
        it.append(('brk', ih, ib, bh(ih), 'with', 'H4 bullish cont'))
    it += [('line', iPL, iTOP + 2, PL, 'pl', 'pullback line'), ('num', cont_up[0][1], bh(cont_up[0][0]) + 3, 2)]
    return frame() + it


def f_pullback_break():
    return frame() + [
        ('line', iPL, iPB, PL, 'pl', ''),
        ('brk', iPL, iPB, PL, 'agst', 'Pullback break'),
        ('tag', iPB, ll(iPB) - 0.4, 'Pullback break · Daily pullback confirmed', 'tg-bear', True),
        ('line', iTOP, N - 1, TOP, 'ext', 'Daily range high'),
        ('line', iTOP, N - 1, RANGE_MID, 'mid', 'Daily range 0.5'),
        ('num', iPB + 2, PL + 2.2, 3)]


def f_against():
    it = [('line', iTOP, N - 1, TOP, 'rg', 'H4 range high (fixed)'),
          ('line', iTOP, N - 1, RANGE_MID, 'mid', 'Daily 0.5 · discount below'),
          ('zone', iTOP, N - 1, RANGE_MID, D_EXT_LO, 'disc', 'Daily discount')]
    for il, ib, ih in cont_dn:
        it.append(('brk', il, ib, bl(il), 'agst', 'H4 bearish cont'))
    it += [('line', iHPL, iHP, HPL, 'pl', 'H4 pullback line'), ('num', cont_dn[1][1], bl(cont_dn[1][0]) - 3, 4)]
    return frame() + it


def f_hold():
    return frame() + [
        ('line', iTOP, N - 1, TOP, 'rg', 'H4 range high'),
        ('line', iHPL, iHP, HPL, 'pl', 'last high before the pullback'),
        ('zone', iHPL, iHP, HPL + 0.2, HPL - 0.2, 'hold', ''),
        ('line', iTOP, N - 1, RANGE_MID, 'mid', 'Daily 0.5'),
        ('num', iHPL + 1, HPL + 2.4, 5)]


def f_aligned():
    it = [('brk', iHPL, iHP, HPL, 'with', 'H4 pullback'),
          ('tag', iHP, hh(iHP) + 0.3, 'H4 pullback · back in alignment with Daily', 'tg-bull', False),
          ('zone', iRL, N - 1, RL, TOP, 'rng', 'H4 range'),
          ('line', iTOP, N - 1, TOP, 'rg', 'H4 range high'),
          ('line', iRL, N - 1, RL, 'rg', 'H4 range low'),
          ('num', iHP + 1, HPL - 2.6, 6)]
    for ih, ib, idp in cont_in[:2]:
        it.append(('brk', ih, ib, bh(ih), 'with', 'H4 bullish cont'))
    return frame() + it


def f_trail():
    it = [('zone', iRL, N - 1, RL, TOP, 'rng', ''),
          ('line', iTOP, N - 1, TOP, 'rg', 'H4 range high'),
          ('line', iRL, N - 1, RL, 'rg', 'H4 range low'),
          ('line', iP3, iDC, P3, 'pl', 'pullback line (inside the range)')]
    for ih, ib, idp in cont_in:
        it.append(('brk', ih, ib, bh(ih), 'with', 'cont'))
    it.append(('num', iP3, P3 - 2.6, 7))
    return frame() + it


def f_continues():
    return frame() + [
        ('zone', iRL, iDC, RL, TOP, 'rng', ''),
        ('brk', iTOP, iDC, TOP, 'with', 'H4 range high broken · Daily continues'),
        ('tag', iDC, hh(iDC) + 0.3, 'Daily continues', 'tg-bull', False),
        ('num', iDC - 2, TOP + 2.6, 8)]


def f_all():
    it = f_breakout() + [x for x in f_cont() if x[0] in ('brk',)]
    it += [('line', iPL, iPB, PL, 'pl', ''), ('tag', iPB, ll(iPB) - 0.4, 'Pullback break', 'tg-bear', True)]
    it += [('brk', x[1], x[2], x[3], x[4], '') for x in f_against() if x[0] == 'brk']
    it += [('line', iHPL, iHP, HPL, 'pl', ''), ('tag', iHP, hh(iHP) + 0.3, 'H4 pullback · back in alignment', 'tg-bull', False),
           ('zone', iRL, iDC, RL, TOP, 'rng', 'H4 range'), ('line', iTOP, N - 1, TOP, 'rg', 'H4 range high'),
           ('line', iRL, N - 1, RL, 'rg', 'H4 range low'), ('line', iTOP, N - 1, RANGE_MID, 'mid', 'Daily 0.5'),
           ('tag', iDC, hh(iDC) + 0.3, 'Daily continues', 'tg-bull', False)]
    return it


def f_bias_pointer():
    zlo, zhi = bl(iDB - 1) - 0.4, bh(iDB) - 0.8
    return frame() + [
        ('zone', iDB - 1, N - 1, zlo, zhi, 'poi', 'Daily FVG / OC / V-shape in the leg'),
        ('line', iTOP, N - 1, TOP, 'ext', 'Daily range high'),
        ('line', iTOP, N - 1, RANGE_MID, 'mid', 'Daily 0.5'),
        ('tag', iRL, ll(iRL) - 0.3, 'reaction at the Daily level', 'tg-ink', True),
        ('brk', iHPL, iHP, HPL, 'with', 'H4 External break up'),
        ('tag', iHP, hh(iHP) + 0.3, 'Bias Pointer: CONFIRMED · MTF: back in alignment', 'tg-bull', False)]


# ── The page ──────────────────────────────────────────────────────────────────────────────────
def fig(items, focus, cap, alt, both=False):
    buys = svg(items, focus, False, alt)
    body = buys
    if both:
        body = (f'<div class="sideview" data-side="buys">{buys}</div>'
                f'<div class="sideview" data-side="sells" hidden>{svg(items, focus, True, alt + " (sells)")}</div>')
    return f'<figure><div class="figwrap">{body}</div><figcaption>{cap}</figcaption></figure>'


RULES = [
    ("1", "The Daily breakout sets the frame", "f_breakout", (0, iDB + 3),
     "A Daily candle body closes beyond the Daily external high (the wick level). The Daily external high and low are the Bias Pointer's, always. Every new Daily breakout starts the story again in its direction.",
     "D.BO · D.Bull XH / XL · alert: Daily breakout"),
    ("2", "Continuation: trade the breakout direction", "f_cont", (iDB, iTOP + 1),
     "In a bullish move lows break highs. The pullback line is the low that broke the last high. Until that high breaks, the low stands and everything inside it is ignored. A high counts once price really pulled back from it (a candle's wick took out the previous candle's low; one candle can do this and close above the high, and its wick is then the new line). When an H4 body closes above it, the line moves to the last low inside the breaking move that broke a high; else the new dip low if it is above the current line; else the broken high itself. The line is drawn on the wick.",
     "H4.C · PL · alert: H4 continuation after the Daily breakout"),
    ("3", "Pullback break: the Daily pulls back", "f_pullback_break", (iTOP - 2, iPB + 2),
     "An H4 body closes below the pullback line. The Daily pullback is confirmed, the Daily range prints its premium and discount, and H4 is now against the Daily. The new pullback line is the high that broke that low: the top of the leg, which is also the H4 range high.",
     "PB · D.PC · D.EQ · alert: H4 pullback confirmed"),
    ("4", "Trade the pullback's continuation, mind the discount", "f_against", (iPB, iRL + 1),
     "While H4 is against the Daily, each close below a real low is an H4 bearish cont, and the H4 pullback line moves to the highest point of the leg that broke that low. Selling deep in the Daily discount (below 0.5) is where the Daily may take over again.",
     "H4.C pb · H4.PL · alert: H4 continuation after the pullback"),
    ("5", "The level that must hold", "f_hold", (iHPL - 2, iHP),
     "After a pullback, the last high created before it is expected to hold. It holds: H4 is still in play against the Daily. It breaks on an H4 body close: the H4 pullback is over.",
     "(the decision point, no label of its own)"),
    ("6", "H4 pullback: back in alignment, the H4 range", "f_aligned", (iRL - 1, iHP + 6),
     "An H4 body close above the H4 pullback line is the H4 pullback. H4 is back in alignment with the Daily. The new pullback line is the low that broke that high, which is also the H4 range low. The H4 range runs from it up to the top of the leg, always inside the Daily range.",
     "H4.P · BIA · H4.RH / H4.RL · alert: H4 pullback: back in alignment"),
    ("7", "Inside the H4 range the pullback line keeps trailing", "f_trail", (iHP, iDC - 1),
     "Inside the range the same rule goes on: each real high broken moves the pullback line up to the low that broke it. Everything else inside is ignored.",
     "PL · H4.C al · PB.in · H4.C in · alerts: H4 continuation in alignment, Inside the H4 range"),
    ("8", "The range breaks: the Daily continues (or H4 keeps going against)", "f_continues", (iP3, N - 1),
     "A close above the H4 range high is the last H4 high inside the Daily range taken: now you can be convinced you are with the Daily. A close below the H4 range low instead means H4 is against the Daily again: the pullback line and the new H4 range high are the high that broke that low.",
     "H4.RHB · D.C / H4.RLB · alerts: H4 range high broken, H4 range low broken"),
]

PHOTON = [
    ("1. 4H is bullish", "Daily bullish breakout, H4 bullish cont", "Rules 1–2"),
    ("2. After the 4H BOS, expect a 4H pullback", "the pullback line is tracked, waiting for the Pullback break", "Rule 2"),
    ("3. M15 switches bearish to facilitate the 4H pullback", "Pullback break · Daily pullback confirmed, H4 bearish cont", "Rules 3–4"),
    ("4. Price pulled back to 4H discount; wait for M15 to switch bullish", "Daily 0.5 and discount shading; the H4 pullback line is the switch level", "Rules 4–5"),
    ("5. M15 switches bullish, now aligned with 4H", "H4 pullback · back in alignment with Daily, the H4 range", "Rule 6"),
    ("6. M1 switches bullish, all timeframes aligned, target the weak 4H high", "entry timeframe confirmation (not built yet); the target is the H4 range high → Daily continues", "Rules 7–8"),
]

CSS = """
:root{
  --paper:#f4f6f8; --sheet:#ffffff; --ink:#14202b; --ink-2:#4a5a68; --line:#d9e0e6;
  --bull:#11845b; --bear:#c8414b; --pl:#1d7fc4; --rg:#d98a12; --accent:#1d7fc4;
  --plot:#0f1820; --plot-grid:#1e2a35; --plot-ink:#dfe7ee; --plot-muted:#8a9aa8;
  --c-up:#3b82f6; --c-dn:#cfd6dc;
  --display:"Archivo", "Segoe UI", system-ui, sans-serif;
  --body:"IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, Consolas, monospace;
  /* layout: one reading column; every rule = statement + the same chart, zoomed on its part */
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#0b1117; --sheet:#111a22; --ink:#e3eaf0; --ink-2:#9db0bf; --line:#22313d;
  --bull:#2fb57f; --bear:#e5636c; --pl:#4aa3e0; --rg:#f0a634; --accent:#4aa3e0;
  --plot:#0a1016; --plot-grid:#17222c; color-scheme:dark; } }
:root[data-theme="dark"]{
  --paper:#0b1117; --sheet:#111a22; --ink:#e3eaf0; --ink-2:#9db0bf; --line:#22313d;
  --bull:#2fb57f; --bear:#e5636c; --pl:#4aa3e0; --rg:#f0a634; --accent:#4aa3e0;
  --plot:#0a1016; --plot-grid:#17222c; color-scheme:dark; }
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 var(--body)}
main{max-width:1040px;margin:0 auto;padding:40px 20px 80px;display:grid;gap:28px}
h1,h2,h3{font-family:var(--display);line-height:1.15;text-wrap:balance;margin:0}
h1{font-size:clamp(34px,6vw,54px);font-weight:800;letter-spacing:-.02em}
h2{font-size:26px;font-weight:800}
h3{font-size:20px;font-weight:700}
p{margin:0;max-width:68ch}
.lede{font-size:19px;color:var(--ink-2)}
.meta{font:13px/1.4 var(--mono);color:var(--ink-2);display:flex;gap:16px;flex-wrap:wrap}
header{display:grid;gap:14px;padding-bottom:22px;border-bottom:2px solid var(--ink)}
.kicker{font:600 13px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
section{display:grid;gap:16px}
.sheet{background:var(--sheet);border:1px solid var(--line);border-radius:14px;padding:24px;display:grid;gap:16px}
.flow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;list-style:none;margin:0;padding:0}
.flow li{font:600 14px/1 var(--body);padding:9px 12px;border-radius:999px;border:1.5px solid var(--line);background:var(--paper)}
.flow li.w{border-color:var(--bull);color:var(--bull)} .flow li.a{border-color:var(--bear);color:var(--bear)}
.flow .arr{border:0;background:none;padding:0;color:var(--ink-2)}
figure{margin:0;display:grid;gap:8px}
.figwrap{overflow-x:auto;border-radius:10px}
.fig{display:block;width:100%;min-width:720px;height:auto}
figcaption{font:13px/1.45 var(--mono);color:var(--ink-2)}
.toggle{display:inline-flex;border:1.5px solid var(--line);border-radius:999px;padding:3px;gap:3px;justify-self:start}
.toggle button{font:600 14px/1 var(--body);border:0;background:none;color:var(--ink-2);padding:8px 16px;border-radius:999px;cursor:pointer}
.toggle button[aria-pressed="true"]{background:var(--ink);color:var(--sheet)}
.toggle button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.rule{display:grid;grid-template-columns:64px 1fr;gap:6px 18px;align-items:start}
.rule .n{font:800 44px/1 var(--display);color:var(--accent);font-variant-numeric:tabular-nums}
.rule .txt{display:grid;gap:8px}
.rule figure{grid-column:1/-1}
.onchart{font:13px/1.4 var(--mono);color:var(--ink-2)}
.onchart b{color:var(--ink);font-weight:600}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:14px 16px;background:var(--sheet);display:grid;gap:6px}
.card h3{font-size:16px}
.card p{font-size:15px;color:var(--ink-2)}
table{border-collapse:collapse;width:100%;font-size:15px}
.tw{overflow-x:auto}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{font:600 12px/1.3 var(--mono);text-transform:uppercase;letter-spacing:.08em;color:var(--ink-2)}
td.k{font-family:var(--mono);font-size:14px;white-space:nowrap}
.branch{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.branch .card.h{border-left-color:var(--bear)} .branch .card.b{border-left-color:var(--bull)}
ul.todo{margin:0;padding-left:20px;display:grid;gap:6px;max-width:70ch}
footer{font:13px/1.5 var(--mono);color:var(--ink-2);border-top:1px solid var(--line);padding-top:16px}
/* chart */
.plot{fill:var(--plot)} .grid{stroke:var(--plot-grid);stroke-width:1}
.up rect{fill:var(--c-up)} .up line{stroke:var(--c-up)} .dn rect{fill:#5e6b76} .dn line{stroke:#5e6b76}
.fade{opacity:.22}
.ext{stroke:#e8edf1;stroke-width:1.6} .pl{stroke:#38a7f0;stroke-width:2.4} .rg{stroke:#f0a634;stroke-width:2.2}
.mid{stroke:#8a9aa8;stroke-width:1.2;stroke-dasharray:6 5}
.lt{font:600 12.5px var(--body);fill:var(--plot-ink)} .pl-t{fill:#7cc4f5} .rg-t{fill:#f6c26a} .mid-t{fill:#9fb0bd}
.brk{stroke-width:1.3;stroke-dasharray:3 3} .brk.with{stroke:#7cc4f5} .brk.agst{stroke:#f08a91}
.bt{font:500 11.5px var(--body);fill:var(--plot-ink)}
.tag rect{fill:#2a3540} .tag text{font:700 12px var(--body);fill:#fff}
.tg-bull rect{fill:#0f9d62} .tg-bear rect{fill:#d23f49} .tg-ink rect{fill:#2c3a46}
.num circle{fill:#fff} .num text{font:800 12.5px var(--body);fill:#0f1820}
.disc{fill:#38a7f0;opacity:.07} .rng{fill:#f0a634;opacity:.08} .hold{fill:#38a7f0;opacity:.35}
.poi{fill:#0f9d62;opacity:.16} .zt{font:600 11.5px var(--body);fill:var(--plot-muted)}
@media (prefers-reduced-motion:no-preference){.toggle button{transition:background .15s}}
"""

JS = """
const btns=document.querySelectorAll('.toggle button');
btns.forEach(b=>b.addEventListener('click',()=>{
  btns.forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
  document.querySelectorAll('.sideview').forEach(v=>{v.hidden=v.dataset.side!==b.dataset.side;});
}));
"""


def page():
    F = globals()
    rules_html = []
    for k, title, fn, focus, text, onchart in RULES:
        rules_html.append(
            f'<article class="sheet rule"><div class="n">{k}</div><div class="txt"><h3>{esc(title)}</h3>'
            f'<p>{esc(text)}</p><p class="onchart">On the chart: <b>{esc(onchart)}</b></p></div>'
            + fig(F[fn](), focus, f'Rule {k} · H4 candles, buys (sells are the mirror)', title) + '</article>')
    photon_rows = ''.join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td class="k">{esc(c)}</td></tr>' for a, b, c in PHOTON)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MTF Storyline Rulebook</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><main>
<header>
  <div class="kicker">MummyTKT · MTF Storyline · owner only</div>
  <h1>MTF Storyline Rulebook</h1>
  <p class="lede">A run on a higher timeframe is a trend on a lower timeframe. This book tells the story the script follows: breakout, continuation, pullback, back in alignment.</p>
  <div class="meta"><span>{VERSION}</span><span>Plan shown: Daily → H4 → M15</span><span>Script: MummyTKT_MTF_Storyline.pine</span></div>
</header>

<section class="sheet">
  <h2>The story in one line</h2>
  <ol class="flow">
    <li class="w">Breakout</li><li class="arr">→</li><li class="w">Continuation</li><li class="arr">→</li>
    <li class="a">Pullback · against the Daily</li><li class="arr">→</li><li class="a">Continuation of the pullback</li><li class="arr">→</li>
    <li class="w">Pullback · back in alignment</li><li class="arr">→</li><li class="w">Daily continues</li>
  </ol>
  <div class="toggle" role="group" aria-label="Direction"><button type="button" data-side="buys" aria-pressed="true">Buys</button><button type="button" data-side="sells" aria-pressed="false">Sells</button></div>
  {fig(f_all(), None, 'The whole story on H4 candles. The white line is the Daily external low, orange lines are the H4 range, blue lines are pullback lines.', 'The whole MTF story', both=True)}
</section>

<section>
  <h2>Three timeframes, three jobs</h2>
  <div class="sheet tw"><table>
    <tr><th>Plan</th><th>Frame (higher)</th><th>Story (medium)</th><th>Entry (lower)</th></tr>
    <tr><td class="k">Weekly story</td><td>Weekly</td><td>Daily</td><td>H4</td></tr>
    <tr><td class="k">Daily story (default)</td><td>Daily</td><td>H4</td><td>M15</td></tr>
    <tr><td class="k">H4 story</td><td>H4</td><td>M15</td><td>M5</td></tr>
  </table>
  <p>The frame timeframe gives the external high and low and the breakout. The story timeframe tells the pullback. The entry timeframe confirms the trade. The rules below use the Daily story; the other plans work the same way one step up or down.</p></div>
</section>

<section>
  <h2>How a break counts</h2>
  <div class="cards">
    <div class="card"><h3>Daily</h3><p>A Daily body close beyond the level's wick.</p></div>
    <div class="card"><h3>H4</h3><p>An H4 body close beyond the level's body.</p></div>
    <div class="card"><h3>Only External breaks</h3><p>A level counts only when an External break made it, as in the Bias Pointer. A tiny candle with no pullback is not a high or a low.</p></div>
    <div class="card"><h3>Inside the Daily range</h3><p>The H4 range high and low always sit inside the Daily range.</p></div>
  </div>
</section>

<section>
  <h2>The rules</h2>
  {''.join(rules_html)}
</section>

<section class="sheet">
  <h2>Reading the pullback: hold or break</h2>
  <p>Every decision in the story is the same question at a different level: does the last high or low before the pullback hold?</p>
  <div class="branch">
    <div class="card h"><h3>It holds</h3><p>H4 is still in play against the Daily. Keep trading the H4 continuation, and be careful in the Daily discount (buys) or premium (sells).</p></div>
    <div class="card b"><h3>It breaks</h3><p>The H4 pullback is over. H4 may be back in alignment with the Daily: this is the H4 pullback tag.</p></div>
    <div class="card"><h3>At the last H4 high inside the Daily range</h3><p>It holds: you may still be against the Daily. It breaks: now you can be convinced you are with the Daily (Daily continues).</p></div>
  </div>
</section>

<section class="sheet">
  <h2>Does it match the Photon picture?</h2>
  <p>Yes, one timeframe higher. Photon's 4H / M15 / M1 is the same story as Daily / H4 / M15 here.</p>
  <div class="tw"><table><tr><th>Photon picture</th><th>In the MTF Storyline</th><th>Rule</th></tr>{photon_rows}</table></div>
</section>

<section class="sheet">
  <h2>Where it meets the Bias Pointer</h2>
  <p>Both scripts use the same Daily external high and low and the same H4 External break. The Bias Pointer asks where the Daily pullback should stop: a reaction at a Daily OC, A or V-shape, FVG or Breaker inside the Daily range (or a post-breakout level), then an H4 External breakout with the Daily confirms it. The MTF Storyline tells the structure around it: when the pullback started, how far H4 went against the Daily, and when it came back in alignment.</p>
  {fig(f_bias_pointer(), (iPB, iHP + 3), 'When a Bias Pointer CONFIRMED lands on the same candle as the MTF "back in alignment", both stories agree: the strongest case.', 'Bias Pointer and MTF Storyline together')}
  <div class="tw"><table>
    <tr><th>Bias Pointer</th><th>MTF Storyline</th></tr>
    <tr><td>Daily breakout (External)</td><td>Rule 1, same engine</td></tr>
    <tr><td>Price returns into the Daily range, to a Daily level</td><td>Rules 3–4: Pullback break, H4 against the Daily, discount</td></tr>
    <tr><td>Reaction at the level + H4 External breakout with the Daily = CONFIRMED</td><td>Rules 5–6: the last high breaks, H4 pullback · back in alignment</td></tr>
    <tr><td>H4 continuation after the confirmation</td><td>Rules 7–8: cont inside the H4 range, then Daily continues</td></tr>
  </table></div>
</section>

<section class="sheet">
  <h2>Not built yet</h2>
  <ul class="todo">
    <li>The Daily levels (OC, A / V-shapes, FVG, Breaker) inside the Daily range. Next build.</li>
    <li>Entry-timeframe confirmation (M15 sweep and break on the H4 levels). After the levels.</li>
    <li>Discount and premium are drawn (0.5 line and shading) but do not block anything.</li>
    <li>Inside the H4 range, a close below a pullback line that has moved up (above the range low) flips H4 against the Daily as a Pullback break inside the range; the range high stays. Check this in replay.</li>
  </ul>
</section>

<footer>{VERSION}. Built from pine/make_mtf_storyline.py rules. Diagrams are drawn candles for teaching, not market data.</footer>
</main><script>{JS}</script></body></html>"""


if __name__ == "__main__":
    open(OUT, "w", encoding="utf-8").write(page())
    print(OUT, "candles", N, "breakout", iDB, "top", iTOP, "PB", iPB, "HP", iHP, "DC", iDC)
