"""Draws structure_picture.svg: the engine's own marks on the made-up chart (seed 0)."""
from sim_path import make
from structure_sim import run

c = make(0)
ev, IN, SW = run(c)

W, H = 1800, 1070
L, R, T, B = 70, 1700, 80, 760          # chart area
lo_p, hi_p = 111.0, 123.0
n = len(c)
dx = (R - L) / n


def X(i):
    return L + dx * (i + 0.5)


def Y(p):
    return B - (p - lo_p) / (hi_p - lo_p) * (B - T)


out = []
add = out.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
add('<text x="70" y="42" font-size="26" font-weight="700" fill="#111">How the script marks Swing, Internal and Fractal structure (bullish example)</text>')
add('<text x="70" y="66" font-size="15" fill="#555">Every mark below was drawn by the script\'s own rules on this chart: CH = wick break of a fractal point · i-BOS = body close beyond an internal high/low · BOS = body close beyond a swing high/low</text>')

# grid
for p in range(112, 123):
    add(f'<line x1="{L}" y1="{Y(p):.1f}" x2="{R}" y2="{Y(p):.1f}" stroke="#f0f0f0"/>')
    add(f'<text x="{R + 8}" y="{Y(p) + 4:.1f}" font-size="11" fill="#999">{p:.2f}</text>')

# swing range of the pullback: EQ, premium / discount (swing low 41 → swing high 72)
sl, sh = 111.84, 121.32
eq = (sl + sh) / 2
add(f'<rect x="{X(72):.1f}" y="{Y(eq):.1f}" width="{X(131) - X(72):.1f}" height="{Y(sl) - Y(eq):.1f}" fill="#16a34a" opacity="0.06"/>')
add(f'<rect x="{X(72):.1f}" y="{Y(sh):.1f}" width="{X(131) - X(72):.1f}" height="{Y(eq) - Y(sh):.1f}" fill="#dc2626" opacity="0.05"/>')
add(f'<line x1="{X(72):.1f}" y1="{Y(eq):.1f}" x2="{X(131):.1f}" y2="{Y(eq):.1f}" stroke="#888" stroke-dasharray="8 5"/>')
add(f'<text x="{X(73):.1f}" y="{Y(eq) - 6:.1f}" font-size="12" fill="#666">Swing EQ 50% · premium above, discount below</text>')

# demand POI at the low that caused the last BOS (bar 102)
pt, pb = 115.55, 114.59
add(f'<rect x="{X(101.5):.1f}" y="{Y(pt):.1f}" width="{X(132) - X(101.5):.1f}" height="{Y(pb) - Y(pt):.1f}" fill="#0d9488" opacity="0.22" stroke="#0d9488"/>')
add(f'<text x="{X(108):.1f}" y="{Y(pb) + 15:.1f}" font-size="12" fill="#0d9488">Swing demand POI (last bearish candle at the strong HL)</text>')

# candles
for i, (o, h, l, cl) in enumerate(c):
    x = X(i)
    up = cl >= o
    add(f'<line x1="{x:.1f}" y1="{Y(h):.1f}" x2="{x:.1f}" y2="{Y(l):.1f}" stroke="#1e3a8a" stroke-width="1"/>')
    top, bot = max(o, cl), min(o, cl)
    hgt = max(Y(bot) - Y(top), 1.2)
    fill = "#ffffff" if up else "#1e3a8a"
    add(f'<rect x="{x - dx * 0.32:.1f}" y="{Y(top):.1f}" width="{dx * 0.64:.1f}" height="{hgt:.1f}" fill="{fill}" stroke="#1e3a8a" stroke-width="1"/>')

STY = {'CH': ('#9ca3af', '3 3', 1), 'i-BOS': ('#6b7280', '1.5 3', 1.4), 'BOS': ('#111111', '', 1.8)}
for e in ev:
    kind, d, lvl, p, b = e[:5]
    col, dash, w = STY[kind]
    y = Y(lvl)
    da = f' stroke-dasharray="{dash}"' if dash else ''
    add(f'<line x1="{X(p):.1f}" y1="{y:.1f}" x2="{X(b):.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="{w}"{da}/>')
    mid = (X(p) + X(b)) / 2 if kind != 'CH' else X(b) - 10
    ty = y - 5 if d > 0 else y + 14
    add(f'<text x="{mid:.1f}" y="{ty:.1f}" font-size="{11 if kind == "CH" else 12}" fill="{col}" text-anchor="middle" font-weight="{600 if kind == "BOS" else 400}">{kind}</text>')


def arc(i, p, high, strong, big):
    x, y = X(i), Y(p)
    r = 13 if big else 8
    y0 = y - 7 if high else y + 7
    sweep = 1 if high else 0
    dash = '' if strong else ' stroke-dasharray="2 3"'
    add(f'<path d="M {x - r:.1f} {y0:.1f} A {r} {r * 0.7:.1f} 0 0 {sweep} {x + r:.1f} {y0:.1f}" fill="none" stroke="#111" stroke-width="{1.6 if strong else 1.2}"{dash}/>')


def dot(i, p, big):
    add(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="{4.5 if big else 2.6}" fill="{"#9ca3af" if big else "#111"}"/>')


def tag(i, p, txt, high, size=13):
    y = Y(p) - 24 if high else Y(p) + 34
    add(f'<text x="{X(i):.1f}" y="{y:.1f}" font-size="{size}" font-weight="700" fill="#111" text-anchor="middle">{txt}</text>')


# swing points
dot(41, 111.84, True); arc(41, 111.84, False, True, True); tag(41, 111.84, "LL · strong swing low", False)
dot(72, 121.32, True); arc(72, 121.32, True, False, True); tag(72, 121.32, "weak swing high (target)", True)
dot(102, 114.59, True); arc(102, 114.59, False, True, True); tag(102, 114.59, "HL · new strong swing low", False)
# internal points
dot(94, 118.52, False); arc(94, 118.52, True, True, False); tag(94, 118.52, "strong internal LH", True, 11)
dot(64, 116.07, False); arc(64, 116.07, False, True, False); tag(64, 116.07, "strong internal HL", False, 11)

# numbered steps
STEPS = [
    (71, 120.16, True, "1"), (78, 118.75, False, "2"), (91, 116.07, False, "3"), (99, 115.76, False, "4"),
    (120, 118.52, True, "5"), (131, 121.32, True, "6"),
]
for i, p, high, s in STEPS:
    x, y = X(i), (Y(p) - 44 if high else Y(p) + 62)
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#7c3aed"/><text x="{x:.1f}" y="{y + 5:.1f}" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">{s}</text>')

add(f'<text x="{X(14):.1f}" y="{Y(121.6):.1f}" font-size="13" fill="#555" text-anchor="middle">Downtrend: lower highs, lower lows</text>')

# legend
ly = 800
add(f'<line x1="70" y1="{ly - 14}" x2="1730" y2="{ly - 14}" stroke="#e5e7eb"/>')
LEG = [
    ("1", "Swing BOS up = trend change. The candle body closed above the strong swing high. The lowest point that caused it (LL) is now the strong swing low. Expect a swing pullback."),
    ("2", "Bearish CH (a wick through a fractal low): the internal pullback may be starting. An early sign only. Nothing is confirmed yet."),
    ("3", "Bearish i-BOS (a body close through the strong internal low): the swing pullback is confirmed, so the swing high is fixed. It is the WEAK high, the target. Longs: phase B · shorts: phase C."),
    ("4", "Another bearish i-BOS: the internal trend is bearish and its lower high is strong. Shorting it is against the swing, so manage it tightly. Price is now in the swing discount."),
    ("5", "Bullish i-BOS: the internal trend is back in line with the swing. Phase A for longs: buy the strong internal / swing HL (the demand POI), target the weak swing high."),
    ("6", "Swing BOS: the weak high is taken. The lowest point that caused the break becomes the new strong swing HL. Expect the next swing pullback."),
]
for k, (s, txt) in enumerate(LEG):
    y = ly + 14 + k * 34
    add(f'<circle cx="86" cy="{y - 5}" r="11" fill="#7c3aed"/><text x="86" y="{y}" font-size="13" font-weight="700" fill="#fff" text-anchor="middle">{s}</text>')
    add(f'<text x="108" y="{y}" font-size="15" fill="#222">{txt}</text>')
ky = ly + 14 + 6 * 34 + 10
add(f'<line x1="86" y1="{ky}" x2="136" y2="{ky}" stroke="#111" stroke-width="1.8"/><text x="144" y="{ky + 5}" font-size="13" fill="#333">BOS (swing, body close)</text>')
add(f'<line x1="330" y1="{ky}" x2="380" y2="{ky}" stroke="#6b7280" stroke-width="1.4" stroke-dasharray="1.5 3"/><text x="388" y="{ky + 5}" font-size="13" fill="#333">i-BOS (internal, body close)</text>')
add(f'<line x1="590" y1="{ky}" x2="640" y2="{ky}" stroke="#9ca3af" stroke-dasharray="3 3"/><text x="648" y="{ky + 5}" font-size="13" fill="#333">CH (fractal, wick)</text>')
add(f'<path d="M 800 {ky + 4} A 12 8 0 0 1 824 {ky + 4}" fill="none" stroke="#111" stroke-width="1.6"/><text x="832" y="{ky + 5}" font-size="13" fill="#333">strong</text>')
add(f'<path d="M 900 {ky + 4} A 12 8 0 0 1 924 {ky + 4}" fill="none" stroke="#111" stroke-dasharray="2 3"/><text x="932" y="{ky + 5}" font-size="13" fill="#333">weak</text>')
add(f'<circle cx="1010" cy="{ky}" r="4.5" fill="#9ca3af"/><text x="1022" y="{ky + 5}" font-size="13" fill="#333">swing point</text>')
add(f'<circle cx="1120" cy="{ky}" r="2.6" fill="#111"/><text x="1130" y="{ky + 5}" font-size="13" fill="#333">internal point</text>')
add('</svg>')

open('C:/Users/u/Documents/Structure_3Types_picture.svg', 'w', encoding='utf-8').write('\n'.join(out))
print('ok')
