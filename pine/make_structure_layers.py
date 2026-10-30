"""Builds MummyTKT_Structure_Layers_TEST.pine from the live script's structure engine."""
SRC = 'C:/Users/u/forex-radar/pine/MummyTKT_BiasPointer.pine'
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_Structure_Layers_TEST.pine'
N = 6   # depths shown

lines = open(SRC, encoding='utf-8').read().split('\n')
start = next(i for i, l in enumerate(lines) if l.startswith('// High / low of the daily candle'))
sec4 = next(i for i, l in enumerate(lines) if l.startswith('    // 4. The most recent structure'))
engine = '\n'.join(lines[start:sec4])
engine = engine.replace('f_structure(bool bd) =>', 'f_layers(bool bd) =>')

FIELDS = ['d', 'hi', 'lo', 'ht', 'lt', 'hf', 'lf']

ret = []
ret.append('    // 4. Every structure, outermost first (depth 0 = External). [1] + lookahead_on =')
ret.append('    //    state after the last COMPLETED candle of that timeframe (no repaint)')
for k in range(N):
    names = ', '.join(f'{f}{k}' for f in FIELDS)
    ret.append(f'    [{names}] = f_lay(stack, e_dir, e_hi, e_lo, e_hi_t, e_lo_t, e_hif, e_lof, {k})')
ret.append('    [' + ', '.join(f'{f}{k}[1]' for k in range(N) for f in FIELDS) + ']')

def outs(p):
    return ', '.join(f'{p}{f}{k}' for k in range(N) for f in FIELDS)

body = []
body.append(f'[{outs("D_")}] = request.security(syminfo.tickerid, "D", f_layers(wick_lv == false), lookahead=barmerge.lookahead_on)')
body.append(f'[{outs("H_")}] = request.security(syminfo.tickerid, "240", f_layers(wick_lv == false), lookahead=barmerge.lookahead_on)')

draw = []
for p, tf in (('D_', 'D'), ('H_', 'H4')):
    for k in range(N):
        a = ', '.join(f'{p}{f}{k}' for f in FIELDS)
        draw.append(f'    f_draw("{tf}", {k}, {p}d0, {a})')

header = f'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — Structure Layers (TEST, display only, no alerts) · 2026-10-30
//
// Every market structure, nested to any depth, drawn with its own name:
//   External › Internal › Inner Internal › Sub-Internal › Micro › Nano
// Rules (the same at every depth):
//   • Levels are WICK highs / lows (switch "Levels from" to Body to test bodies).
//     A level is broken only when a candle BODY closes beyond it.
//   • First level: a close above an A-shape (inside a range: only after a later
//     candle traded below the A's bearish candle) → the lowest point since the A
//     is the low; mirror for a V.
//   • The side in the move's direction is "still forming" (follows price) until
//     price closes beyond the A / V it pulled back from; then it is fixed.
//   • Close beyond the fixed high / low → new pair the same way; close beyond the
//     other side → it flips.
//   • A new structure forms inside the newest range without waiting for anything
//     above it to break; a break drops every structure inside the one that broke.
//   • Each layer says Bullish / Bearish, and "against External" when it points the
//     other way. Its highs / lows are the targets inside it.
// Daily layers show on the Daily chart and lower; H4 layers on the 4H chart and
// lower (H4 lines dashed).
// ─────────────────────────────────────────────────────────────────────────────

indicator("MummyTKT — Structure Layers (Test)", overlay = true, max_lines_count = 100, max_labels_count = 100, max_bars_back = 2000)

bool   wick_lv  = input.string("Wick", "Levels from", options = ["Wick", "Body"]) == "Wick"
bool   show_d   = input.bool(true, "Daily layers (Daily chart and lower)")
bool   show_h   = input.bool(true, "H4 layers (4H chart and lower)")
int    depth_d  = input.int(4, "Daily: layers to show", minval = 1, maxval = {N})
int    depth_h  = input.int(4, "H4: layers to show", minval = 1, maxval = {N})
color  c0 = input.color(#E0E0E0, "External",       group = "Colours", inline = "c1")
color  c1 = input.color(#FFA726, "Internal",       group = "Colours", inline = "c1")
color  c2 = input.color(#26C6DA, "Inner Internal", group = "Colours", inline = "c2")
color  c3 = input.color(#AB47BC, "Sub-Internal",   group = "Colours", inline = "c2")
color  c4 = input.color(#FFEE58, "Micro",          group = "Colours", inline = "c3")
color  c5 = input.color(#F06292, "Nano",           group = "Colours", inline = "c3")
int    lw = input.int(1, "Line width", minval = 1, maxval = 4)

var NAMES = array.from("External", "Internal", "Inner Internal", "Sub-Internal", "Micro", "Nano")

'''

lay = '''
// One structure's values: direction (+1 bull, -1 bear, 0 none), high, low, when
// each formed, and whether each side is fixed (1) or still forming (0)
f_lay(array<Layer> st, string edir, float ehi, float elo, int ehit, int elot, bool ehif, bool elof, int k) =>
    float d  = 0.0
    float hi = na
    float lo = na
    int   ht = na
    int   lt = na
    float hf = 0.0
    float lf = 0.0
    if k == 0
        if edir != "none"
            d  := edir == "bull" ? 1.0 : -1.0
            hi := ehi
            lo := elo
            ht := ehit
            lt := elot
            hf := ehif ? 1.0 : 0.0
            lf := elof ? 1.0 : 0.0
    else if array.size(st) >= k
        Layer L = array.get(st, k - 1)
        if L.dir != "none"
            d  := L.dir == "bull" ? 1.0 : -1.0
            hi := L.hi
            lo := L.lo
            ht := L.hi_t
            lt := L.lo_t
            hf := L.hi_fixed ? 1.0 : 0.0
            lf := L.lo_fixed ? 1.0 : 0.0
    [d, hi, lo, ht, lt, hf, lf]

'''

draw_fn = f'''
var array<line>  ln_all = array.new<line>()
var array<label> lb_all = array.new<label>()
// Labels waiting to be drawn: layers at the same price share one label
var array<float>  pv_y  = array.new<float>()
var array<string> pv_s  = array.new<string>()
var array<color>  pv_c  = array.new<color>()
var array<string> pv_tf = array.new<string>()

f_col(int k) =>
    k == 0 ? c0 : k == 1 ? c1 : k == 2 ? c2 : k == 3 ? c3 : k == 4 ? c4 : c5

f_side(string tf, int k, float d0, float d, float y, int t, bool fixed, bool is_hi) =>
    if not na(y) and not na(t)
        color  c   = f_col(k)
        string dir = d > 0 ? "Bullish " : "Bearish "
        bool   frm = not fixed and (is_hi ? d > 0 : d < 0)
        string vs  = k > 0 and d != d0 ? " · against External" : ""
        string txt = tf + " " + dir + array.get(NAMES, k) + (is_hi ? " high" : " low") + (frm ? " (still forming)" : "") + vs
        array.push(ln_all, line.new(t, y, time, y, xloc = xloc.bar_time, extend = extend.right, color = c, width = lw,
             style = tf == "H4" ? line.style_dashed : line.style_solid))
        array.push(pv_y, y)
        array.push(pv_s, txt)
        array.push(pv_c, c)
        array.push(pv_tf, tf)

f_draw(string tf, int k, float d0, float d, float hi, float lo, int ht, int lt, float hf, float lf) =>
    bool on  = tf == "D" ? show_d and k < depth_d and timeframe.in_seconds() <= 86400 : show_h and k < depth_h and timeframe.in_seconds() <= 14400
    if on and d != 0
        f_side(tf, k, d0, d, hi, ht, hf == 1.0, true)
        f_side(tf, k, d0, d, lo, lt, lf == 1.0, false)

if barstate.islast
    for l in ln_all
        line.delete(l)
    for b in lb_all
        label.delete(b)
    array.clear(ln_all)
    array.clear(lb_all)
    array.clear(pv_y)
    array.clear(pv_s)
    array.clear(pv_c)
    array.clear(pv_tf)
'''

MERGE = r'''    // One label per price: the layers sharing it are listed one per line
    int pn = array.size(pv_y)
    array<bool> pdone = array.new<bool>(pn, false)
    int i = 0
    while i < pn
        if not array.get(pdone, i)
            string ptxt = array.get(pv_s, i)
            int j = i + 1
            while j < pn
                if not array.get(pdone, j) and array.get(pv_tf, j) == array.get(pv_tf, i) and math.abs(array.get(pv_y, j) - array.get(pv_y, i)) < syminfo.mintick / 2
                    ptxt := ptxt + "\n" + array.get(pv_s, j)
                    array.set(pdone, j, true)
                j += 1
            float py = array.get(pv_y, i)
            array.push(lb_all, label.new(bar_index + (array.get(pv_tf, i) == "H4" ? 3 : 18), py, ptxt + "  " + str.tostring(py, format.mintick),
                 style = label.style_label_left, color = color.new(color.black, 100), textcolor = array.get(pv_c, i), size = size.small))
        i += 1
'''

out = header + engine.split('f_layers(bool bd) =>')[0] + lay + 'f_layers(bool bd) =>' + engine.split('f_layers(bool bd) =>')[1] + '\n' + '\n'.join(ret) + '\n\n' + '\n'.join(body) + '\n' + draw_fn + '\n'.join(draw) + '\n' + MERGE
open(OUT, 'w', encoding='utf-8', newline='\n').write(out)
print(OUT, len(out.split('\n')), 'lines')
