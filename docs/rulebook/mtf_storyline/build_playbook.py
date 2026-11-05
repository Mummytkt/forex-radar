"""MTF Storyline Playbook: the whole strategy on one candlestick picture + a checklist per phase.
Run: python docs/rulebook/mtf_storyline/build_playbook.py -> docs/rulebook/mtf_storyline/playbook.html
(user's strategy summary, 2026-11-03)."""
import html
import os
import random
import re

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playbook.html")
esc = html.escape

WAY = [(0, 96.0), (3, 99.6), (5, 98.6), (8, 103.0), (10, 101.6), (13, 106.0), (15, 104.4), (18, 109.5),
       (20, 107.5), (21, 108.3), (24, 103.4), (27, 107.0), (29, 105.4), (30, 105.9), (32, 102.4),
       (34, 103.7), (37, 100.2), (39, 102.0), (40, 101.5), (42, 104.6), (43, 104.0), (44, 103.5),
       (47, 107.9), (48, 107.4), (52, 110.8)]


def make(way, seed=12, noise=0.14, wick=0.45):
    random.seed(seed)
    path = []
    for (a, pa), (b, pb) in zip(way, way[1:]):
        for i in range(a, b):
            path.append(pa + (pb - pa) * (i - a) / (b - a))
    path.append(way[-1][1])
    out, prev = [], path[0] - 0.5
    for p in path:
        o, c = prev, p + random.uniform(-noise, noise)
        out.append((o, max(o, c) + random.uniform(0.1, wick), min(o, c) - random.uniform(0.1, wick), c))
        prev = c
    return out


CS = make(WAY)
N = len(CS)
bh = lambda i: max(CS[i][0], CS[i][3])
bl = lambda i: min(CS[i][0], CS[i][3])
cl = lambda i: CS[i][3]
imax = lambda a, b: max(range(a, b + 1), key=bh)
imin = lambda a, b: min(range(a, b + 1), key=bl)
first = lambda a, f: next(i for i in range(a, N) if f(cl(i)))

D_LO = bl(0)
OLD_HI = 98.8
iDB = first(1, lambda c: c > OLD_HI)
iPL = imin(14, 16); PL = bl(iPL)                    # pullback line: the last low that broke a high
iTOP = imax(16, 19); TOP = bh(iTOP)                 # the top = Daily external high (target later)
iPB = first(iTOP + 1, lambda c: c < PL)             # pullback confirmed
MID = (TOP + D_LO) / 2
iBH = imax(iTOP + 1, iPB); BH = bh(iBH)             # the high that broke the pullback line
iBL = imin(iPB, 25); BLV = bl(iBL)                  # the low of that break
iRV = imax(25, 28); RV = bh(iRV)                    # reversal into the pullback-break range (holds)
iC2 = first(iRV + 1, lambda c: c < BLV)             # another bearish break: H4 still in play
iHP = imax(33, 35); HP = bh(iHP)                    # H4 pullback line: the last high that broke a low
iLOW = imin(35, 41); LOW = bl(iLOW)                 # the bottom (in the Daily discount)
iAL = first(iLOW + 1, lambda c: c > HP)             # H4 pullback: MTF range
iLH = iRV; LH = RV                                  # the last H4 high, the one that made the external low
iGO = first(iAL + 1, lambda c: c > LH)              # last H4 high broken: aligned with the Daily
LO_P, HI_P = 94.0, 113.0
VW, VH = 1100, 700
PL_, PR_, PT_, PB_ = 20, 250, 30, 40


def X(i):
    return PL_ + (VW - PL_ - PR_) * (i + 0.5) / (N + 1)


SWAP = {"bullish": "bearish", "high": "low", "highs": "lows", "discount": "premium", "buys": "sells",
        "buy": "sell", "above": "below", "below": "above", "up": "down", "top": "bottom", "Buys": "Sells"}
SWAP.update({v: k for k, v in list(SWAP.items()) if v not in SWAP})


def swap(t):
    def rep(m):
        w = m.group(0)
        r = SWAP.get(w) or SWAP.get(w.lower())
        if r is None:
            return w
        return r.capitalize() if w[0].isupper() else r
    return re.sub(r"[A-Za-z]+", rep, t)


def chart(flip):
    t = swap if flip else (lambda s: s)
    Y = lambda p: (VH - PB_) - ((LO_P + HI_P - p if flip else p) - LO_P) / (HI_P - LO_P) * (VH - PT_ - PB_)
    o = [f'<svg class="chart" viewBox="0 0 {VW} {VH}" role="img" aria-label="The MTF Storyline on H4 candles{" (sells)" if flip else ""}" xmlns="http://www.w3.org/2000/svg">',
         f'<rect x="0" y="0" width="{VW}" height="{VH}" rx="12" fill="#0e151c"/>']

    def zone(i0, i1, p0, p1, fill, op, tx=None, tcol="#9fb0bd"):
        y0, y1 = sorted((Y(p0), Y(p1)))
        o.append(f'<rect x="{X(i0):.1f}" y="{y0:.1f}" width="{X(i1) - X(i0):.1f}" height="{y1 - y0:.1f}" fill="{fill}" opacity="{op}"/>')
        if tx:
            o.append(f'<text x="{X(i0) + 6:.1f}" y="{y0 + 15:.1f}" font-size="12" font-weight="600" fill="{tcol}">{esc(t(tx))}</text>')

    def line(i0, i1, p, col, wd=1.8, dash="", tx=None, right=True):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o.append(f'<line x1="{X(i0):.1f}" x2="{X(i1):.1f}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="{wd}"{d}/>')
        if tx:
            o.append(f'<text x="{X(i1) + 8:.1f}" y="{Y(p) + 4:.1f}" font-size="12.5" font-weight="700" fill="{col}">{esc(t(tx))}</text>')

    def tag(i, p, tx, col, below=False):
        tx = t(tx)
        b = (not below) if flip else below
        w = 14 + len(tx) * 6.5
        x0 = min(max(X(i) - w / 2, 6), X(N - 1) - w)
        y0 = Y(p) + 10 if b else Y(p) - 32
        o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="22" rx="5" fill="{col}"/>')
        o.append(f'<text x="{x0 + w / 2:.1f}" y="{y0 + 15:.1f}" font-size="12" font-weight="800" fill="#fff" text-anchor="middle">{esc(tx)}</text>')

    def num(i, p, k):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(p):.1f}" r="12" fill="#ffffff"/><text x="{X(i):.1f}" y="{Y(p) + 4.5:.1f}" font-size="13" font-weight="800" fill="#0e151c" text-anchor="middle">{k}</text>')

    # Daily range, premium / discount (from the pullback)
    zone(iPB, N, MID, TOP, "#e5636c", 0.07)
    zone(iPB, N, D_LO, MID, "#2fb57f", 0.07)
    line(0, N - 1, D_LO, "#dfe7ee", 1.4, "", "Daily external low")
    line(iTOP, N - 1, TOP, "#dfe7ee", 1.6, "", "Daily external high (target)")
    line(iPB, N - 1, MID, "#8a9aa8", 1.2, "6 5", "Daily 0.5 · discount below")
    line(0, iDB, OLD_HI, "#dfe7ee", 1.4)
    # pullback-break range and the MTF range
    zone(iBH, iC2, BLV, BH, "#f0a634", 0.10, "pullback-break range")
    zone(iAL, iGO, LOW, LH, "#4aa3e0", 0.10)
    o.append(f'<text x="{X(iAL) + 6:.1f}" y="{Y(LOW) + (-14 if flip else 18):.1f}" font-size="12" font-weight="600" fill="#9fb0bd">{esc(t("H4 (MTF) range"))}</text>')
    # candles
    dx = (VW - PL_ - PR_) / (N + 1)
    for i, (op, h, l, c) in enumerate(CS):
        up = (c >= op) != flip
        col = "#3b82f6" if up else "#7b8794"
        y1, y2 = sorted((Y(op), Y(c)))
        o.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" stroke="{col}" stroke-width="1.3"/>')
        o.append(f'<rect x="{X(i) - dx * .32:.1f}" y="{y1:.1f}" width="{dx * .64:.1f}" height="{max(y2 - y1, 1.4):.1f}" fill="{col}" rx="1"/>')
    # levels
    line(iPL, iPB, PL, "#38a7f0", 2.6)
    o.append(f'<text x="{X(iPL) - 4:.1f}" y="{Y(PL) + (-8 if flip else 18):.1f}" font-size="12" font-weight="700" fill="#7cc4f5" text-anchor="end">{esc(t("pullback line"))}</text>')
    line(iHP, iAL, HP, "#38a7f0", 2.6)
    o.append(f'<text x="{X(iHP) - 4:.1f}" y="{Y(HP) + (14 if flip else -8):.1f}" font-size="12" font-weight="700" fill="#7cc4f5" text-anchor="end">{esc(t("H4 pullback line"))}</text>')
    line(iLH, iGO, LH, "#f0a634", 2.4, "", None)
    o.append(f'<text x="{(X(iLH) + X(iGO)) / 2:.1f}" y="{Y(LH) + (16 if flip else -8):.1f}" font-size="12" font-weight="700" fill="#f6c26a" text-anchor="middle">{esc(t("last H4 high (made the external low)"))}</text>')
    # tags
    tag(iDB, CS[iDB][1] + 0.4, "Daily bullish breakout", "#2c3a46")
    tag(iPB, CS[iPB][2] - 0.4, "Pullback confirmed", "#d23f49", below=True)
    tag(iRV, CS[iRV][1] + 0.4, "range holds?", "#b7791f")
    tag(iC2, CS[iC2][2] - 0.4, "H4 bearish cont", "#d23f49", below=True)
    tag(iAL, CS[iAL][1] + 0.6, "H4 pullback · MTF range", "#0f9d62")
    tag(iGO, CS[iGO][1] + 0.6, "last H4 high broken · aligned", "#0f9d62")
    # phase numbers
    for i, p, k in ((iDB - 1, OLD_HI - 2.0, 1), (cont_i, PL + 2.6, 2), (iPB + 1, PL - 3.2, 3), (iRV + 1, RV + 2.6, 4),
                    (iC2 + 3, BLV - 4.2, 5), (iAL + 1, HP - 3.2, 6), (iGO + 2, LH - 2.6, 7)):
        num(i, p, k)
    o.append('</svg>')
    return ''.join(o)


cont_i = iPL + 1

PHASES = [
    ("1", "Daily breakout", "Alert: Daily breakout · D.BO", "w", [
        "A Daily candle body closed beyond the Daily external high (the wick level).",
        "Note the Weekly direction: with it, or against it.",
        "Mark the Daily external low (the frame). The Daily high is now forming.",
        "Go to H4 and wait for the continuation breaks.",
    ]),
    ("2", "H4 continuation", "Alert: H4 continuation after the Daily breakout · H4.C", "w", [
        "An H4 body closed above the last real high (a real pullback came first: a candle's wick took out the previous candle's low, or this same candle did it, right after a bearish candle).",
        "Pullback line = the last H4 low that broke a high. It just moved up.",
        "Range low waiting = the pullback line before it.",
        "Entry: in the leg of this break, with M15 confirmation at the leg's levels.",
    ]),
    ("3", "Pullback confirmed", "Alert: H4 pullback confirmed · PB · D.PC", "a", [
        "An H4 body closed below the pullback line, after a proper reversal.",
        "Mark the Daily range and its 0.5: premium above, discount below. The H4 range resets to the range just broken, and the new line is the closest high inside it.",
        "H4 is now against the Daily.",
        "Watch for one of two things: an H4 bearish continuation, or a reversal into the pullback-break range.",
    ]),
    ("4", "Reversal into the pullback-break range", "Decision point", "d", [
        "Price climbs back into the range of the leg that broke the pullback line.",
        "It breaks out above that range (a body close above the high that broke the pullback line): the range did not hold, the Daily is continuing. Back to phase 2.",
        "It holds and H4 breaks bearish again: H4 is still in play. Go to phase 5.",
    ]),
    ("5", "H4 bearish continuation", "Alert: H4 continuation after the pullback · H4.C pb", "a", [
        "An H4 body closed below a real low.",
        "H4 pullback line = the last high that broke a low.",
        "Key level: the last H4 high that made the external low. If there is no pullback line inside it, that high is the pullback line. Until it is taken, H4 is still bearish.",
        "Entry: sells in the leg of this break, with M15 confirmation.",
        "Care: price is heading into the Daily discount (below 0.5). Manage the trade there.",
    ]),
    ("6", "H4 pullback: the MTF range", "Alert: H4 pullback: back in alignment · H4.P · BIA", "d", [
        "An H4 body closed above the H4 pullback line.",
        "MTF range resets to the range just broken: low = the bottom of the pullback, high = the newest leg high beyond the old line. The new line is the closest low inside it.",
        "Inside the range: H4 continuation in alignment (H4.C al), pullback break inside the range (PB.in), H4 continuation against the Daily (H4.C in).",
        "That last H4 high holds: still bearish. Back to phase 5.",
        "It breaks: go to phase 7.",
    ]),
    ("7", "Aligned with the Daily", "Alert: H4 continuation · H4.RHB · D.C", "w", [
        "An H4 body closed above the last H4 high inside the Daily range.",
        "Target: the Daily external high.",
        "Entry: buys in the leg of each H4 continuation break, with M15 confirmation.",
        "One candle through the line and the range edge is one alert: H4 pullback + continuation (H4.P+C).",
        "A close below the H4 range low instead: alert H4 continuation (H4.RLB). H4 is against the Daily again, back to phase 5.",
        "A new close below the pullback line takes you back to phase 3.",
    ]),
]

CSS = """
:root{
  /* layout: one reading column; the picture on top, the phase stepper, then one card per phase */
  --bg:#f3f5f7; --sheet:#ffffff; --ink:#15202b; --ink-2:#556574; --line:#d8dfe6;
  --with:#0f8a5f; --against:#c23b45; --decide:#b7791f; --accent:#1f78c4;
  --display:"Archivo", "Segoe UI", system-ui, sans-serif;
  --body:"IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#0b1117; --sheet:#121b23; --ink:#e3eaf0; --ink-2:#9db0bf; --line:#24323e;
  --with:#33bd86; --against:#ec6a73; --decide:#e0a645; --accent:#55a9e6; color-scheme:dark; } }
:root[data-theme="dark"]{
  --bg:#0b1117; --sheet:#121b23; --ink:#e3eaf0; --ink-2:#9db0bf; --line:#24323e;
  --with:#33bd86; --against:#ec6a73; --decide:#e0a645; --accent:#55a9e6; color-scheme:dark; }
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:16px/1.55 var(--body);
  padding-left:max(16px, env(safe-area-inset-left, 0px));padding-right:max(16px, env(safe-area-inset-right, 0px))}
main{max-width:1080px;margin:0 auto;padding-block:36px 72px;display:grid;gap:26px}
h1,h2,h3{font-family:var(--display);line-height:1.15;margin:0;text-wrap:balance}
h1{font-size:clamp(30px,5.5vw,48px);font-weight:800;letter-spacing:-.02em}
h2{font-size:23px;font-weight:800}
h3{font-size:18px;font-weight:700}
p{margin:0;max-width:70ch}
.kicker{font:600 12.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
header{display:grid;gap:12px;padding-bottom:20px;border-bottom:2px solid var(--ink)}
.lede{font-size:18px;color:var(--ink-2)}
.sheet{background:var(--sheet);border:1px solid var(--line);border-radius:14px;padding:22px;display:grid;gap:14px;min-width:0}
.chartwrap{overflow-x:auto;border-radius:12px}
.chart{display:block;width:100%;min-width:760px;height:auto}
.row{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
.toggle{display:inline-flex;border:1.5px solid var(--line);border-radius:999px;padding:3px;gap:3px}
.toggle button,.reset{font:600 14px/1 var(--body);border:0;background:none;color:var(--ink-2);padding:8px 15px;border-radius:999px;cursor:pointer}
.toggle button[aria-pressed="true"]{background:var(--ink);color:var(--sheet)}
.reset{border:1.5px solid var(--line)}
button:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:14px;color:var(--ink-2)}
.legend i{display:inline-block;width:18px;height:4px;border-radius:2px;vertical-align:middle;margin-right:6px}
.steps{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}
@media (max-width:760px){.steps{grid-template-columns:repeat(2,minmax(0,1fr))}}
.step{border:1.5px solid var(--line);background:var(--sheet);border-radius:10px;padding:10px;display:grid;gap:4px;text-align:left;cursor:pointer;color:var(--ink);font:inherit;min-width:0}
.step b{font:800 20px/1 var(--display)}
.step span{font-size:13px;line-height:1.3;color:var(--ink-2)}
.step.w b{color:var(--with)} .step.a b{color:var(--against)} .step.d b{color:var(--decide)}
.step[aria-pressed="true"]{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent) inset}
.phases{display:grid;gap:14px}
.phase{border-left:5px solid var(--line)}
.phase.w{border-left-color:var(--with)} .phase.a{border-left-color:var(--against)} .phase.d{border-left-color:var(--decide)}
.phase.now{box-shadow:0 0 0 2px var(--accent)}
.ph-head{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline}
.ph-n{font:800 30px/1 var(--display);color:var(--ink-2)}
.alert{font:600 13px/1.3 var(--mono);color:var(--ink-2)}
.nowpill{font:700 12px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;background:var(--accent);color:var(--sheet);padding:5px 8px;border-radius:999px}
ul.check{list-style:none;margin:0;padding:0;display:grid;gap:8px}
ul.check label{display:grid;grid-template-columns:22px 1fr;gap:10px;align-items:start;cursor:pointer}
ul.check input{width:18px;height:18px;margin-top:3px;accent-color:var(--accent)}
ul.check input:checked + span{color:var(--ink-2);text-decoration:line-through;text-decoration-color:var(--line)}
.always{border:1.5px dashed var(--accent);background:transparent}
.rules{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.rule{border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;gap:6px;background:var(--sheet)}
.rule p{font-size:15px;color:var(--ink-2)}
footer{font:13px/1.5 var(--mono);color:var(--ink-2)}
"""

JS = r"""
const KEY='mtf-playbook-v1';
let st={phase:'1',ticks:{}};
try{const s=JSON.parse(localStorage.getItem(KEY)||'null');if(s&&s.phase)st=s;}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(st));}catch(e){}}
function render(){
  document.querySelectorAll('.step').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.p===st.phase)));
  document.querySelectorAll('.phase').forEach(c=>{const on=c.dataset.p===st.phase;c.classList.toggle('now',on);c.querySelector('.nowpill').hidden=!on;});
  document.querySelectorAll('ul.check input').forEach(i=>{i.checked=!!st.ticks[i.id];});
}
document.querySelectorAll('.step').forEach(b=>b.addEventListener('click',()=>{st.phase=b.dataset.p;save();render();
  const c=document.querySelector('.phase[data-p="'+b.dataset.p+'"]');if(c)c.scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}));
document.querySelectorAll('ul.check input').forEach(i=>i.addEventListener('change',()=>{st.ticks[i.id]=i.checked;save();}));
document.getElementById('reset').addEventListener('click',()=>{st={phase:'1',ticks:{}};save();render();});
const tg=document.querySelectorAll('.toggle button');
tg.forEach(b=>b.addEventListener('click',()=>{tg.forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
  document.querySelectorAll('.side').forEach(v=>v.hidden=v.dataset.side!==b.dataset.side);}));
render();
"""


def page():
    steps = ''.join(f'<button type="button" class="step {c}" data-p="{k}" aria-pressed="false"><b>{k}</b><span>{esc(t)}</span></button>'
                    for k, t, a, c, _ in PHASES)
    cards = []
    for k, t, a, c, items in PHASES:
        lis = ''.join(f'<li><label for="c{k}-{j}"><input type="checkbox" id="c{k}-{j}"><span>{esc(x)}</span></label></li>' for j, x in enumerate(items))
        cards.append(f'<article class="sheet phase {c}" data-p="{k}"><div class="ph-head"><span class="ph-n">{k}</span><h3>{esc(t)}</h3>'
                     f'<span class="alert">{esc(a)}</span><span class="nowpill" hidden>you are here</span></div><ul class="check">{lis}</ul></article>')
    return f"""<title>MTF Storyline Playbook</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
<main>
<header>
  <div class="kicker">MummyTKT · MTF Storyline · Daily → H4 → M15</div>
  <h1>MTF Storyline Playbook</h1>
  <p class="lede">Breakout, continuation, pullback, then either the Daily continues or H4 plays against it until it comes back in alignment. Pick the phase you are in and tick what you have checked.</p>
</header>

<section class="sheet">
  <div class="row"><h2>The whole story</h2>
    <div class="toggle" role="group" aria-label="Direction"><button type="button" data-side="buys" aria-pressed="true">Buys</button><button type="button" data-side="sells" aria-pressed="false">Sells</button></div></div>
  <div class="chartwrap"><div class="side" data-side="buys">{chart(False)}</div><div class="side" data-side="sells" hidden>{chart(True)}</div></div>
  <div class="legend"><span><i style="background:#38a7f0"></i>pullback lines</span><span><i style="background:#f0a634"></i>pullback-break range · last H4 high</span><span><i style="background:#4aa3e0;opacity:.6"></i>H4 (MTF) range</span><span><i style="background:#8a9aa8"></i>Daily 0.5</span></div>
  <p>The numbers on the chart are the phases below. H4 candles drawn for teaching, not market data.</p>
</section>

<section class="sheet">
  <div class="row"><h2>Where am I?</h2><button type="button" class="reset" id="reset">New setup</button></div>
  <div class="steps">{steps}</div>
</section>

<section class="sheet always">
  <h3>At every break</h3>
  <p>Look for the entry in the leg of the break, with M15 confirmation at that leg's levels. Every break is a body close beyond the level.</p>
</section>

<section class="phases">{''.join(cards)}</section>

<section>
  <h2>The levels</h2>
  <div class="rules" style="margin-top:12px">
    <div class="rule"><h3>Pullback line</h3><p>Buys: the last H4 low that broke a high. Sells: the last H4 high that broke a low. It only counts after a real pullback, not one candle.</p></div>
    <div class="rule"><h3>Pullback-break range</h3><p>The leg that broke the pullback line. Price often comes back into it. It holds: H4 is still against the Daily. It breaks: the Daily continues.</p></div>
    <div class="rule"><h3>Last H4 high</h3><p>The high that made the external low. Until it is taken, H4 is still bearish. Taken = back in alignment with the Daily.</p></div>
    <div class="rule"><h3>Daily range</h3><p>Set by the first pullback after the Daily breakout. Premium above the 0.5, discount below. Sells get careful in the discount.</p></div>
  </div>
</section>

<footer>Built from the MTF Storyline rules, 3 November 2026. Your ticks are kept in this browser only.</footer>
</main>
<script>{JS}</script>"""


if __name__ == "__main__":
    open(OUT, "w", encoding="utf-8").write(page())
    print(OUT, dict(iDB=iDB, iPB=iPB, iRV=iRV, iC2=iC2, iAL=iAL, iGO=iGO, N=N))
