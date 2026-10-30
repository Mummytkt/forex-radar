"""Builds MummyTKT_Structure_3Types_TEST.pine (display only, no alerts).

The engine is written once (f_ms); this script only generates the long, repetitive
parts: the tuple lists for request.security and the drawing code per timeframe.
Python copy of the engine for testing: structure_sim.py.
"""
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_Structure_3Types_TEST.pine'

FIELDS = ['fdir', 'fh', 'fht', 'flo', 'flt', 'ch', 'chl', 'chp', 'chn', 'bt',
          'idir', 'ihi', 'iht', 'ihf', 'ilo', 'ilt', 'ilf', 'iev', 'ifl', 'ibl', 'ibp', 'inp', 'inpt', 'ipt', 'ipo', 'ipq', 'in_',
          'sdir', 'shi', 'sht', 'shf', 'slo', 'slt', 'slf', 'sev', 'sfl', 'sbl', 'sbp', 'snp', 'snpt', 'spt', 'spo', 'spq', 'sn']

HEAD = r'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — Swing · Internal · Fractal structure (TEST, display only, no alerts)
//
// Three structures, each inside the one above it:
//   Swing    → BOS   = a candle BODY closes beyond the swing high / low
//   Internal → i-BOS = a candle BODY closes beyond the internal high / low
//   Fractal  → CH    = a WICK goes beyond the latest fractal high / low and turns the
//                      fractal trend (CHoCH)
// Highs and lows are wick levels. A fractal high / low is a candle whose wick is
// beyond the N candles on each side (setting "Fractal: candles each side").
//
// How the points are set (bullish; bearish is the mirror):
//   • The high of a leg keeps following price ("still forming") until the pullback
//     is confirmed: an internal high by a bearish CH, a swing high by a bearish
//     i-BOS. From then on it is fixed: the WEAK high, the target.
//   • A body close above the fixed high is a break (i-BOS / BOS). The lowest point
//     between that high and the break (the low that caused it) is the new STRONG low.
//   • A body close below the strong low flips the trend: the high that took out the
//     strong low becomes the strong high.
//   • Strong = protected, trade from it; weak = the target.
// POIs: at each break, the last opposite candle at the new strong point (demand
// below for buys, supply above for sells). Faded once price returns into it
// (mitigated), removed once a candle closes through it.
// Phases (table): Longs A = swing + internal bullish, B = swing bullish, internal
// pulling back, C = swing bearish, internal bullish, D = both bearish (avoid).
// Shorts the mirror.
// Mode: one timeframe (all three from the chart) or HTF + MTF (both timeframes'
// structure drawn on this chart; the chart is your LTF for entries).
// ─────────────────────────────────────────────────────────────────────────────

indicator("MummyTKT — Swing · Internal · Fractal (Test)", overlay = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 200, max_bars_back = 5000)

const string G_MODE = "1 · Mode"
const string G_SHOW = "2 · What to show"
const string G_POI  = "3 · POIs"
const string G_TBL  = "4 · Table"
const string G_COL  = "5 · Colours"

string mode = input.string("One timeframe (chart)", "Structure from", options = ["One timeframe (chart)", "HTF + MTF"], group = G_MODE,
     tooltip = "One timeframe: swing, internal and fractal all from this chart's candles. HTF + MTF: the structure of both timeframes below is drawn on this chart (use a lower chart, e.g. M15, as your LTF).")
string htf  = input.timeframe("D",   "HTF (narrative)", group = G_MODE)
string mtf  = input.timeframe("240", "MTF (bias and POIs)", group = G_MODE)
int    flen = input.int(2, "Fractal: candles each side", minval = 1, maxval = 10, group = G_MODE,
     tooltip = "A fractal high is a candle whose high is above this many candles on each side (low: below). 2 = the classic 5-candle fractal.")

bool one_s = input.bool(true,  "One TF: Swing",    group = G_SHOW, inline = "one")
bool one_i = input.bool(true,  "Internal",         group = G_SHOW, inline = "one")
bool one_f = input.bool(true,  "Fractal CH",       group = G_SHOW, inline = "one")
bool htf_s = input.bool(true,  "HTF: Swing",       group = G_SHOW, inline = "htf")
bool htf_i = input.bool(true,  "Internal",         group = G_SHOW, inline = "htf")
bool htf_f = input.bool(false, "Fractal CH",       group = G_SHOW, inline = "htf")
bool mtf_s = input.bool(true,  "MTF: Swing",       group = G_SHOW, inline = "mtf")
bool mtf_i = input.bool(true,  "Internal",         group = G_SHOW, inline = "mtf")
bool mtf_f = input.bool(true,  "Fractal CH",       group = G_SHOW, inline = "mtf")
bool show_pts = input.bool(true, "HH / HL / LH / LL labels at the points", group = G_SHOW)
bool show_cur = input.bool(true, "Current strong / weak highs and lows", group = G_SHOW)
bool show_eq  = input.bool(true, "Swing EQ 50% (premium / discount)", group = G_SHOW)
int  keep_n   = input.int(15, "Past breaks kept (each type)", minval = 1, maxval = 100, group = G_SHOW)

bool poi_s   = input.bool(true, "Swing POIs", group = G_POI, inline = "p")
bool poi_i   = input.bool(true, "Internal POIs", group = G_POI, inline = "p")
int  poi_max = input.int(10, "POIs kept", minval = 1, maxval = 50, group = G_POI)
bool poi_mit = input.bool(true, "Keep mitigated POIs (faded)", group = G_POI,
     tooltip = "A POI is mitigated once price comes back into it. On: it stays, faded. Off: it is removed. A candle closing through it always removes it.")

bool   tbl_on  = input.bool(true, "Show the structure table", group = G_TBL)
string tbl_pos = input.string("Top right", "Position", options = ["Top right", "Bottom right", "Top left", "Bottom left"], group = G_TBL)

color c_bull = input.color(#26A69A, "Bullish break", group = G_COL, inline = "c1")
color c_bear = input.color(#EF5350, "Bearish break", group = G_COL, inline = "c1")
color c_sw   = input.color(#E0E0E0, "Swing levels", group = G_COL, inline = "c2")
color c_in   = input.color(#FFB74D, "Internal levels", group = G_COL, inline = "c2")
color c_pt   = input.color(#B0BEC5, "Point labels", group = G_COL, inline = "c3")
color c_eq   = input.color(#9E9E9E, "EQ", group = G_COL, inline = "c3")
color c_dem  = input.color(#26A69A, "Demand POI", group = G_COL, inline = "c4")
color c_sup  = input.color(#EF5350, "Supply POI", group = G_COL, inline = "c4")
color c_mit  = input.color(#787B86, "Mitigated", group = G_COL, inline = "c4")

// ── Engine ────────────────────────────────────────────────────────────────────
type Lvl
    int   dir = 0
    float hi  = na
    int   hb  = na
    bool  hf  = false
    float lo  = na
    int   lb  = na
    bool  lf  = false

// Open time of bar b (na if unknown)
f_tb(int b) =>
    na(b) ? na : time[math.min(bar_index - b, 4990)]

// Highest high / lowest low from bar from_bar up to this bar, and its bar
f_hi_since(int from_bar) =>
    float m  = high
    int   mb = bar_index
    int   n  = math.min(bar_index - nz(from_bar, bar_index), 1500)
    for i = 0 to n
        if high[i] > m
            m  := high[i]
            mb := bar_index - i
    [m, mb]
f_lo_since(int from_bar) =>
    float m  = low
    int   mb = bar_index
    int   n  = math.min(bar_index - nz(from_bar, bar_index), 1500)
    for i = 0 to n
        if low[i] < m
            m  := low[i]
            mb := bar_index - i
    [m, mb]

// POI: the last opposite candle at the new strong point (it, or up to 3 candles
// before it): bearish for demand, bullish for supply. [top, bottom, open time]
f_poi(bool bull, int pb) =>
    int k0 = math.min(bar_index - pb, 4985)
    int kk = k0
    for j = 0 to 3
        int k = k0 + j
        if bull ? close[k] < open[k] : close[k] > open[k]
            kk := k
            break
    [high[kk], low[kk], time[kk]]

// One candle of one structure (internal or swing). fixH / fixL: the structure
// below confirmed a pullback (a bearish / bullish CH for internal, i-BOS for swing).
// Returns [break (+1 / -1 / 0), trend flipped, broken level, its bar, new strong point, its bar]
method step(Lvl s, bool fixH, bool fixL) =>
    int   ev   = 0
    bool  flip = false
    float bl   = na
    int   bp   = na
    float np   = na
    int   npb  = na
    if s.dir == 0
        // start: the first confirmed pullback sets the direction
        if fixL
            [m, mb] = f_lo_since(bar_index - 20)
            s.dir := 1
            s.lo := m
            s.lb := mb
            s.lf := true
            s.hi := high
            s.hb := bar_index
            s.hf := false
        else if fixH
            [m, mb] = f_hi_since(bar_index - 20)
            s.dir := -1
            s.hi := m
            s.hb := mb
            s.hf := true
            s.lo := low
            s.lb := bar_index
            s.lf := false
    else if s.dir == 1
        if not s.hf and high >= s.hi
            s.hi := high
            s.hb := bar_index
        if fixH
            s.hf := true
        if close < s.lo
            // the strong low broke: the high that took it out is the strong high
            ev   := -1
            flip := true
            bl   := s.lo
            bp   := s.lb
            [m, mb] = f_hi_since(s.lb)
            s.dir := -1
            s.hi := m
            s.hb := mb
            s.hf := true
            s.lo := low
            s.lb := bar_index
            s.lf := false
            np  := m
            npb := mb
        else if s.hf and close > s.hi
            // break of the fixed high: the low that caused it is the new strong low
            ev := 1
            bl := s.hi
            bp := s.hb
            [m, mb] = f_lo_since(s.hb)
            s.lo := m
            s.lb := mb
            s.lf := true
            s.hi := high
            s.hb := bar_index
            s.hf := false
            np  := m
            npb := mb
    else
        if not s.lf and low <= s.lo
            s.lo := low
            s.lb := bar_index
        if fixL
            s.lf := true
        if close > s.hi
            ev   := 1
            flip := true
            bl   := s.hi
            bp   := s.hb
            [m, mb] = f_lo_since(s.hb)
            s.dir := 1
            s.lo := m
            s.lb := mb
            s.lf := true
            s.hi := high
            s.hb := bar_index
            s.hf := false
            np  := m
            npb := mb
        else if s.lf and close < s.lo
            ev := -1
            bl := s.lo
            bp := s.lb
            [m, mb] = f_hi_since(s.lb)
            s.hi := m
            s.hb := mb
            s.hf := true
            s.lo := low
            s.lb := bar_index
            s.lf := false
            np  := m
            npb := mb
    [ev, flip, bl, bp, np, npb]

// The whole engine on this timeframe's candles
f_ms(simple int fln) =>
    var Lvl IN = Lvl.new()
    var Lvl SW = Lvl.new()
    var float fh   = na
    var int   fhb  = na
    var bool  fhx  = true
    var float fl   = na
    var int   flb  = na
    var bool  flx  = true
    var int   fdir = 0
    var int   chn  = 0
    var int   inn  = 0
    var int   swn  = 0
    float ph = ta.pivothigh(high, fln, fln)
    float pl = ta.pivotlow(low, fln, fln)
    if not na(ph)
        fh  := ph
        fhb := bar_index - fln
        fhx := false
    if not na(pl)
        fl  := pl
        flb := bar_index - fln
        flx := false
    // Fractal CH: a wick beyond the latest fractal high / low that turns the fractal trend
    int   ch  = 0
    float chl = na
    int   chp = na
    if not fhx and high > fh
        fhx := true
        if fdir != 1
            fdir := 1
            ch   := 1
            chl  := fh
            chp  := fhb
    if not flx and low < fl
        flx := true
        if fdir != -1
            fdir := -1
            ch   := -1
            chl  := fl
            chp  := flb
    if ch != 0
        chn += 1
    [iev, ifl, ibl, ibp, inp, inpb] = IN.step(ch == -1, ch == 1)
    if iev != 0
        inn += 1
    [sev, sfl, sbl, sbp, snp, snpb] = SW.step(iev == -1, iev == 1)
    if sev != 0
        swn += 1
    float ipt = na
    float ipo = na
    int   ipq = na
    if iev != 0 and not na(inpb)
        [a1, a2, a3] = f_poi(iev == 1, inpb)
        ipt := a1
        ipo := a2
        ipq := a3
    float spt = na
    float spo = na
    int   spq = na
    if sev != 0 and not na(snpb)
        [b1, b2, b3] = f_poi(sev == 1, snpb)
        spt := b1
        spo := b2
        spq := b3
    [fdir, fh, f_tb(fhb), fl, f_tb(flb), ch, chl, f_tb(chp), chn, time,
     IN.dir, IN.hi, f_tb(IN.hb), IN.hf, IN.lo, f_tb(IN.lb), IN.lf, iev, ifl, ibl, f_tb(ibp), inp, f_tb(inpb), ipt, ipo, ipq, inn,
     SW.dir, SW.hi, f_tb(SW.hb), SW.hf, SW.lo, f_tb(SW.lb), SW.lf, sev, sfl, sbl, f_tb(sbp), snp, f_tb(snpb), spt, spo, spq, swn]

'''

WRAP = '''// Another timeframe: [1] + lookahead_on = its last COMPLETED candle (no repaint)
f_ms1(simple int fln) =>
    [{v}] = f_ms(fln)
    [{v1}]

'''

DRAW_HELPERS = r'''
bool one     = mode == "One timeframe (chart)"
int  tf_sec  = timeframe.in_seconds()
bool C_on    = one
bool H_on    = not one and timeframe.in_seconds(htf) >= tf_sec
bool M_on    = not one and timeframe.in_seconds(mtf) >= tf_sec

f_tfname(string tf) =>
    tf == "D" or tf == "1D" ? "D" : tf == "W" or tf == "1W" ? "W" : tf == "M" or tf == "1M" ? "M" : tf == "240" ? "H4" : tf == "60" ? "H1" : tf == "120" ? "H2" : tf == "30" ? "M30" : tf == "15" ? "M15" : tf == "5" ? "M5" : tf
string C_tf = ""
string H_tf = f_tfname(htf) + " "
string M_tf = f_tfname(mtf) + " "

// ── Drawing ───────────────────────────────────────────────────────────────────
var array<line>  l_sw  = array.new<line>()
var array<label> lb_sw = array.new<label>()
var array<line>  l_in  = array.new<line>()
var array<label> lb_in = array.new<label>()
var array<line>  l_ch  = array.new<line>()
var array<label> lb_ch = array.new<label>()
var array<label> lb_pt = array.new<label>()

f_cap_l(array<line> a, int cap) =>
    while array.size(a) > cap
        line.delete(array.shift(a))
f_cap_lb(array<label> a, int cap) =>
    while array.size(a) > cap
        label.delete(array.shift(a))

// A break: a line from the broken point to the breaking candle, its name in the middle
f_brk(array<line> la, array<label> lba, int pt, int bt, float y, int d, string txt, string st, color c, int w, int cap) =>
    array.push(la, line.new(pt, y, bt, y, xloc = xloc.bar_time, style = st, color = c, width = w))
    array.push(lba, label.new(pt + int((bt - pt) / 2), y, txt, xloc = xloc.bar_time, style = d > 0 ? label.style_label_down : label.style_label_up,
         color = color.new(color.black, 100), textcolor = c, size = size.tiny))
    f_cap_l(la, cap)
    f_cap_lb(lba, cap)

f_ptl(int t, float y, bool is_hi, string txt, color c) =>
    if not na(t) and not na(y)
        array.push(lb_pt, label.new(t, y, txt, xloc = xloc.bar_time, style = is_hi ? label.style_label_down : label.style_label_up,
             color = color.new(color.black, 100), textcolor = c, size = size.tiny))
        f_cap_lb(lb_pt, keep_n * 6)

// The broken point and the new strong point of a break
f_brkname(int ev, bool flip) =>
    ev > 0 ? (flip ? "LH" : "HH") : (flip ? "HL" : "LL")
f_newname(int ev, bool flip) =>
    ev > 0 ? (flip ? "LL" : "HL") : (flip ? "HH" : "LH")

// POIs
var array<box>   pz   = array.new<box>()
var array<float> pz_t = array.new<float>()
var array<float> pz_b = array.new<float>()
var array<bool>  pz_d = array.new<bool>()
var array<bool>  pz_m = array.new<bool>()
f_pz_drop(int k) =>
    box.delete(array.get(pz, k))
    array.remove(pz, k)
    array.remove(pz_t, k)
    array.remove(pz_b, k)
    array.remove(pz_d, k)
    array.remove(pz_m, k)
f_poi_add(float top, float bot, int t, bool demand, string txt) =>
    if not na(top) and not na(bot) and not na(t)
        color c = demand ? c_dem : c_sup
        array.push(pz, box.new(t, top, time, bot, xloc = xloc.bar_time, border_color = c, bgcolor = color.new(c, 82),
             text = txt, text_size = size.tiny, text_color = c, text_halign = text.align_right, text_valign = text.align_center))
        array.push(pz_t, top)
        array.push(pz_b, bot)
        array.push(pz_d, demand)
        array.push(pz_m, false)
        while array.size(pz) > poi_max
            f_pz_drop(0)

'''

EVENTS = r'''
// ── @NAME@: breaks as they happen ──
var int @P@k1 = 0
var int @P@k2 = 0
var int @P@k3 = 0
if @P@on and not na(@P@chn)
    if @P@chn != @P@k1
        @P@k1 := @P@chn
        if @P@sf and @P@ch != 0 and not na(@P@chp)
            f_brk(l_ch, lb_ch, @P@chp, @P@bt, @P@chl, @P@ch, @P@tf + "CH", line.style_dashed, @P@ch > 0 ? c_bull : c_bear, 1, keep_n * 2)
    if @P@in_ != @P@k2
        @P@k2 := @P@in_
        if @P@iev != 0 and not na(@P@ibp)
            if @P@si
                f_brk(l_in, lb_in, @P@ibp, @P@bt, @P@ibl, @P@iev, @P@tf + "i-BOS", line.style_dotted, @P@iev > 0 ? c_bull : c_bear, 1, keep_n * 2)
                if show_pts
                    f_ptl(@P@ibp, @P@ibl, @P@iev > 0, @P@tf + "i" + f_brkname(@P@iev, @P@ifl), c_pt)
                    f_ptl(@P@inpt, @P@inp, @P@iev < 0, @P@tf + "i" + f_newname(@P@iev, @P@ifl), c_pt)
            if poi_i and @P@si
                f_poi_add(@P@ipt, @P@ipo, @P@ipq, @P@iev > 0, @P@tf + "internal " + (@P@iev > 0 ? "demand" : "supply"))
    if @P@sn != @P@k3
        @P@k3 := @P@sn
        if @P@sev != 0 and not na(@P@sbp)
            if @P@ss
                f_brk(l_sw, lb_sw, @P@sbp, @P@bt, @P@sbl, @P@sev, @P@tf + "BOS", line.style_solid, @P@sev > 0 ? c_bull : c_bear, 2, keep_n * 2)
                if show_pts
                    f_ptl(@P@sbp, @P@sbl, @P@sev > 0, @P@tf + f_brkname(@P@sev, @P@sfl), c_sw)
                    f_ptl(@P@snpt, @P@snp, @P@sev < 0, @P@tf + f_newname(@P@sev, @P@sfl) + " (strong)", c_sw)
            if poi_s and @P@ss
                f_poi_add(@P@spt, @P@spo, @P@spq, @P@sev > 0, @P@tf + "swing " + (@P@sev > 0 ? "demand" : "supply"))
'''

TAIL = r'''
// ── POIs: extend, fade when mitigated, remove when closed through ──
if array.size(pz) > 0
    int k = array.size(pz) - 1
    while k >= 0
        box   bx = array.get(pz, k)
        bool  dm = array.get(pz_d, k)
        float tp = array.get(pz_t, k)
        float bb = array.get(pz_b, k)
        if dm ? close < bb : close > tp
            f_pz_drop(k)
        else if not array.get(pz_m, k)
            box.set_right(bx, time)
            if dm ? low <= tp : high >= bb
                if poi_mit
                    array.set(pz_m, k, true)
                    box.set_bgcolor(bx, color.new(c_mit, 85))
                    box.set_border_color(bx, c_mit)
                    box.set_text_color(bx, c_mit)
                else
                    f_pz_drop(k)
        k -= 1

// ── Current highs and lows (strong / weak), EQ, merged labels ──
var array<line>   cur_l = array.new<line>()
var array<label>  cur_b = array.new<label>()
var array<float>  pv_y  = array.new<float>()
var array<string> pv_s  = array.new<string>()
var array<color>  pv_c  = array.new<color>()

f_pend(float y, string txt, color c) =>
    array.push(pv_y, y)
    array.push(pv_s, txt)
    array.push(pv_c, c)

f_cur(string tf, string nm, int dir, float hi, int ht, bool hf, float lo, int lt, bool lf, string st, color c, bool eq) =>
    if dir != 0 and not na(hi) and not na(lo) and not na(ht) and not na(lt)
        string d  = dir > 0 ? "Bullish " : "Bearish "
        string hs = dir < 0 ? "strong" : hf ? "weak (target)" : "weak, still forming"
        string ls = dir > 0 ? "strong" : lf ? "weak (target)" : "weak, still forming"
        array.push(cur_l, line.new(ht, hi, time, hi, xloc = xloc.bar_time, extend = extend.right, style = st, color = c))
        array.push(cur_l, line.new(lt, lo, time, lo, xloc = xloc.bar_time, extend = extend.right, style = st, color = c))
        f_pend(hi, tf + d + nm + " high · " + hs, c)
        f_pend(lo, tf + d + nm + " low · " + ls, c)
        if eq
            float e = (hi + lo) / 2
            array.push(cur_l, line.new(math.max(ht, lt), e, time, e, xloc = xloc.bar_time, extend = extend.right, style = line.style_dotted, color = c_eq))
            f_pend(e, tf + "swing EQ 50% · " + (close > e ? "price in premium" : "price in discount"), c_eq)

f_dirtxt(int d) =>
    d > 0 ? "Bullish" : d < 0 ? "Bearish" : "—"
// Phase for a trade direction: A pro swing + pro internal, B pro swing + counter
// internal, C counter swing + pro internal, D counter both
f_phase(int s, int i, bool long) =>
    int ws = long ? s : -s
    int wi = long ? i : -i
    s == 0 or i == 0 ? "—" : ws > 0 ? (wi > 0 ? "A" : "B") : (wi > 0 ? "C" : "D")
f_phtxt(string p) =>
    p == "A" ? "A · full alignment" : p == "B" ? "B · internal pulling back" : p == "C" ? "C · counter swing" : p == "D" ? "D · avoid" : "—"
f_phcol(string p) =>
    p == "A" ? color.new(#26A69A, 40) : p == "B" or p == "C" ? color.new(#FFB74D, 50) : p == "D" ? color.new(#EF5350, 50) : color.new(color.gray, 70)

f_tpos(string p) =>
    p == "Top right" ? position.top_right : p == "Bottom right" ? position.bottom_right : p == "Top left" ? position.top_left : position.bottom_left
var table tb = table.new(f_tpos(tbl_pos), 7, 3, bgcolor = color.new(#0F1120, 10), border_width = 1, border_color = color.new(color.gray, 70))

f_row(int r, string tf, int s, int i, int f, float shi, float slo) =>
    string pl = f_phase(s, i, true)
    string ps = f_phase(s, i, false)
    float  e  = (shi + slo) / 2
    table.cell(tb, 0, r, tf, text_color = color.white, text_size = size.small)
    table.cell(tb, 1, r, f_dirtxt(s), text_color = s > 0 ? c_bull : s < 0 ? c_bear : color.gray, text_size = size.small)
    table.cell(tb, 2, r, f_dirtxt(i), text_color = i > 0 ? c_bull : i < 0 ? c_bear : color.gray, text_size = size.small)
    table.cell(tb, 3, r, f_dirtxt(f), text_color = f > 0 ? c_bull : f < 0 ? c_bear : color.gray, text_size = size.small)
    table.cell(tb, 4, r, f_phtxt(pl), text_color = color.white, bgcolor = f_phcol(pl), text_size = size.small)
    table.cell(tb, 5, r, f_phtxt(ps), text_color = color.white, bgcolor = f_phcol(ps), text_size = size.small)
    table.cell(tb, 6, r, na(e) ? "—" : close > e ? "Premium" : "Discount", text_color = color.white, text_size = size.small)

if barstate.islast
    for l in cur_l
        line.delete(l)
    for b in cur_b
        label.delete(b)
    array.clear(cur_l)
    array.clear(cur_b)
    array.clear(pv_y)
    array.clear(pv_s)
    array.clear(pv_c)
    if show_cur
@CUR@
    // one label per price: the levels sharing it are listed one per line
    int pn = array.size(pv_y)
    array<bool> pdone = array.new<bool>(pn, false)
    int i = 0
    while i < pn
        if not array.get(pdone, i)
            string ptxt = array.get(pv_s, i)
            int j = i + 1
            while j < pn
                if not array.get(pdone, j) and math.abs(array.get(pv_y, j) - array.get(pv_y, i)) < syminfo.mintick / 2
                    ptxt := ptxt + "\n" + array.get(pv_s, j)
                    array.set(pdone, j, true)
                j += 1
            float py = array.get(pv_y, i)
            array.push(cur_b, label.new(bar_index + 3, py, ptxt + "  " + str.tostring(py, format.mintick),
                 style = label.style_label_left, color = color.new(color.black, 100), textcolor = array.get(pv_c, i), size = size.small))
        i += 1
    if tbl_on
        table.clear(tb, 0, 0, 6, 2)
        table.cell(tb, 0, 0, "TF", text_color = color.gray, text_size = size.small)
        table.cell(tb, 1, 0, "Swing", text_color = color.gray, text_size = size.small)
        table.cell(tb, 2, 0, "Internal", text_color = color.gray, text_size = size.small)
        table.cell(tb, 3, 0, "Fractal", text_color = color.gray, text_size = size.small)
        table.cell(tb, 4, 0, "Longs", text_color = color.gray, text_size = size.small)
        table.cell(tb, 5, 0, "Shorts", text_color = color.gray, text_size = size.small)
        table.cell(tb, 6, 0, "vs swing EQ", text_color = color.gray, text_size = size.small)
        if one
            f_row(1, "Chart", C_sdir, C_idir, C_fdir, C_shi, C_slo)
        else
            if H_on
                f_row(1, "HTF " + f_tfname(htf), H_sdir, H_idir, H_fdir, H_shi, H_slo)
            else
                table.cell(tb, 0, 1, "HTF " + f_tfname(htf) + " is below the chart timeframe: switch the chart lower", text_color = c_bear, text_size = size.small)
            if M_on
                f_row(2, "MTF " + f_tfname(mtf), M_sdir, M_idir, M_fdir, M_shi, M_slo)
            else
                table.cell(tb, 0, 2, "MTF " + f_tfname(mtf) + " is below the chart timeframe: switch the chart lower", text_color = c_bear, text_size = size.small)
'''

CUR = r'''        if @P@on and @P@ss
            f_cur(@P@tf, "swing", @P@sdir, @P@shi, @P@sht, @P@shf, @P@slo, @P@slt, @P@slf, line.style_solid, c_sw, show_eq)
        if @P@on and @P@si
            f_cur(@P@tf, "internal", @P@idir, @P@ihi, @P@iht, @P@ihf, @P@ilo, @P@ilt, @P@ilf, line.style_dotted, c_in, false)
'''

ENGINES = [('C_', 'one timeframe', 'one_s', 'one_i', 'one_f'),
           ('H_', 'HTF', 'htf_s', 'htf_i', 'htf_f'),
           ('M_', 'MTF', 'mtf_s', 'mtf_i', 'mtf_f')]


def names(p):
    return ', '.join(p + f for f in FIELDS)


body = HEAD
body += WRAP.format(v=', '.join('v_' + f for f in FIELDS), v1=', '.join('v_' + f + '[1]' for f in FIELDS))
body += f'[{names("C_")}] = f_ms(flen)\n'
body += f'[{names("H_")}] = request.security(syminfo.tickerid, htf, f_ms1(flen), lookahead = barmerge.lookahead_on)\n'
body += f'[{names("M_")}] = request.security(syminfo.tickerid, mtf, f_ms1(flen), lookahead = barmerge.lookahead_on)\n'
body += DRAW_HELPERS
for p, nm, s, i, f in ENGINES:
    body += f'bool {p}ss = {s}\nbool {p}si = {i}\nbool {p}sf = {f}\n'
for p, nm, s, i, f in ENGINES:
    body += EVENTS.replace('@P@', p).replace('@NAME@', nm)
cur = ''.join(CUR.replace('@P@', p) for p, *_ in ENGINES)
body += TAIL.replace('@CUR@\n', cur)
open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
print(OUT, body.count('\n'), 'lines')
