"""Builds MummyTKT_PullbackStory.pine — the user's nested story (2026-10-30):

  T1 (top) external breakout starts the story; its external range is the frame.
  T2 (story) tells the pullback inside it: a reaction at the opposite T1 levels + a T2
     breakout against T1 = the T1 pullback; a T2 CHoCH back = the T2 pullback, in line
     with T1; the main T2 high / low taken out = aligned.
  T3 (entry) confirms at the T2 POIs (sweep / sweep and break).
  Plans: W → D → H4 · D → H4 → M15 · H4 → M15 → M5.

The external structure engine is copied from MummyTKT_BiasPointer.pine (most recent
external high / low); its breaks go through f_cu / f_cd so a break can be a wick
(default) or a body close.
"""
import re

SRC = 'C:/Users/u/forex-radar/pine/MummyTKT_BiasPointer.pine'
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_PullbackStory.pine'

src = open(SRC, encoding='utf-8').read().split('\n')
a = next(i for i, l in enumerate(src) if l.startswith('// High / low of the daily candle'))
b = next(i for i, l in enumerate(src) if l.startswith('[s_cdir, s_chi'))
ENGINE = '\n'.join(src[a:b])
n_before = len(re.findall(r'close ([<>]) (?!open)', ENGINE))
ENGINE = re.sub(r'close > (?!open)', 'f_cu() > ', ENGINE)
ENGINE = re.sub(r'close < (?!open)', 'f_cd() < ', ENGINE)
assert n_before >= 20, n_before

HEAD = r'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — Pullback Story (display only, no alerts) · 2026-10-30
//
// One story, nested three timeframes deep (pick the plan in the settings):
//   W → D → H4    the Weekly breakout starts it, the Daily tells it, H4 gives entries
//   D → H4 → M15  the Daily breakout starts it, H4 tells it, M15 gives entries
//   H4 → M15 → M5 the same for day trading
// (Buys; sells are the mirror.)
//   1. Top timeframe external breakout (the Bias Pointer's external high / low; a break
//      is a WICK beyond the level by default, or a body close). A pullback is expected.
//   2. The reaction levels where that pullback may start: the opposite top-timeframe
//      levels above it: V-shape / resistance (A-shape), OC, FVG.
//   3. A story-timeframe breakout DOWN after the reaction = the top timeframe's pullback.
//      Its high is the main story-timeframe high.
//   4. A story-timeframe CHoCH UP = the story-timeframe pullback starts, in line with the
//      top timeframe. Careful: it stays bearish until the main high is taken out.
//   5. The main high is taken out (a breakout up) = aligned. The low that caused it is the
//      demand POI.
//   6. Entries: the entry timeframe's sweep or sweep-and-break at a reached POI.
// All of it happens inside the top timeframe's external range; a breakout the other way
// starts a new story. Until a reaction level gives the pullback, each story-timeframe
// breakout with the top timeframe is printed as a continuation of the breakout.
// ─────────────────────────────────────────────────────────────────────────────

indicator("MummyTKT — Pullback Story", overlay = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 200, max_bars_back = 5000)

const string G_PL = "1 · Plan and breaks"
const string G_ST = "2 · Story notes"
const string G_LV = "3 · Levels and lines"
const string G_ZN = "4 · Zones"
const string G_EN = "5 · Entries"
const string G_TB = "6 · Status table"

string plan     = input.string("D → H4 → M15", "Plan (top → story → entry)", options = ["W → D → H4", "D → H4 → M15", "H4 → M15 → M5"], group = G_PL,
     tooltip = "The top timeframe's breakout starts the story, the story timeframe tells the pullback, the entry timeframe confirms. Put the chart on the story or the entry timeframe.")
bool   brk_wick = input.string("Wick", "Break confirmed by", options = ["Wick", "Body close"], group = G_PL,
     tooltip = "Wick (default): a wick beyond the level breaks it. Body close: the candle must close beyond it.") == "Wick"
bool   d_body   = input.string("Body", "Levels from", options = ["Body", "Wick"], group = G_PL,
     tooltip = "Highs, lows, A-shapes and V-shapes from candle bodies (as the Bias Pointer) or wicks.") == "Body"
int    fr_n     = input.int(2, "CHoCH: fractal candles each side", minval = 1, maxval = 5, group = G_PL)

string st_mode  = input.string("Latest note + dots (hover)", "Story on the chart", options = ["Latest note + dots (hover)", "Latest note only", "Last N notes", "Off"], group = G_ST,
     tooltip = "Latest note + dots: only the newest note is written out; older ones become small dots, hover to read them.")
int    st_n     = input.int(6, "N (notes or dots kept)", minval = 1, maxval = 40, group = G_ST)
color  st_bg    = input.color(#0E3B43, "Note background", group = G_ST, inline = "sb")
int    st_op    = input.int(5, "transparency %", minval = 0, maxval = 100, group = G_ST, inline = "sb")
color  st_tx    = input.color(color.white, "Note text", group = G_ST, inline = "st")
string st_sz    = input.string("Small", "size", options = ["Tiny", "Small", "Normal"], group = G_ST, inline = "st")
color  st_dot   = input.color(#26C6DA, "Older note dots", group = G_ST)
bool   sl_on    = input.bool(true, "Story lines (CHoCH / BOS from the level to the candle that broke it)", group = G_ST)
color  sl_col   = input.color(color.new(color.white, 20), "Story line colour", group = G_ST, inline = "sl")
color  sl_tx    = input.color(color.white, "text", group = G_ST, inline = "sl")

bool   t1_on    = input.bool(true, "Top timeframe external high / low", group = G_LV, inline = "t1")
color  t1_col   = input.color(#E0E0E0, "", group = G_LV, inline = "t1")
string t1_sty   = input.string("Solid", "", options = ["Solid", "Dashed", "Dotted"], group = G_LV, inline = "t1")
int    t1_w     = input.int(2, "width", minval = 1, maxval = 4, group = G_LV, inline = "t1")
bool   rg_on    = input.bool(true, "Shade the top timeframe external range", group = G_LV, inline = "rg")
color  rg_col   = input.color(#7C4DFF, "", group = G_LV, inline = "rg")
int    rg_op    = input.int(94, "transparency %", minval = 0, maxval = 100, group = G_LV, inline = "rg")
bool   mn_on    = input.bool(true, "Main story-timeframe high / low (while the pullback runs)", group = G_LV, inline = "mn")
color  mn_col   = input.color(#FFB74D, "", group = G_LV, inline = "mn")
color  lv_tx    = input.color(#E0E0E0, "Level label text", group = G_LV, inline = "lt")
string lv_sz    = input.string("Small", "size", options = ["Tiny", "Small", "Normal"], group = G_LV, inline = "lt")

bool   rx_on    = input.bool(true, "Reaction levels (opposite top-timeframe A / V-shapes and OCs)", group = G_ZN, inline = "rx")
color  rx_col   = input.color(#EF5350, "", group = G_ZN, inline = "rx")
bool   fv_on    = input.bool(true, "Reaction FVGs (top timeframe)", group = G_ZN, inline = "fv")
color  fv_col   = input.color(#EF5350, "", group = G_ZN, inline = "fv")
int    fv_op    = input.int(85, "transparency %", minval = 0, maxval = 100, group = G_ZN, inline = "fv")
bool   pz_on    = input.bool(true, "POIs (story timeframe, after it lines up)", group = G_ZN, inline = "pz")
color  pz_dem   = input.color(#26A69A, "demand", group = G_ZN, inline = "pc")
color  pz_sup   = input.color(#EF5350, "supply", group = G_ZN, inline = "pc")
int    pz_op    = input.int(80, "transparency %", minval = 0, maxval = 100, group = G_ZN, inline = "pc")
color  pz_mit   = input.color(#787B86, "Reached (mitigated)", group = G_ZN, inline = "pm")
int    pz_max   = input.int(6, "POIs kept", minval = 1, maxval = 30, group = G_ZN, inline = "pm")

string en_conf  = input.string("Both", "Entry confirmation", options = ["Sweep", "Sweep and break", "Both"], group = G_EN,
     tooltip = "Sweep: a bullish candle wicks below the bearish candle before it and closes back above that low (sells: mirror). Sweep and break: a low at the POI, its sweep, then a close above the last lower high.")
int    en_win   = input.int(20, "Sweep and break: candles from the sweep to the break", minval = 1, maxval = 100, group = G_EN)
color  en_col   = input.color(#7C4DFF, "Entry mark", group = G_EN)

bool   tb_on    = input.bool(true, "Status table", group = G_TB, inline = "tb")
string tb_pos   = input.string("Top right", "", options = ["Top right", "Bottom right", "Top left", "Bottom left"], group = G_TB, inline = "tb")
color  tb_bg    = input.color(color.new(#0F1120, 10), "Background", group = G_TB, inline = "tc")
color  tb_tx    = input.color(color.white, "Text", group = G_TB, inline = "tc")

// The plan's three timeframes and their names
string T1 = plan == "W → D → H4" ? "W" : plan == "D → H4 → M15" ? "D" : "240"
string T2 = plan == "W → D → H4" ? "D" : plan == "D → H4 → M15" ? "240" : "15"
string T3 = plan == "W → D → H4" ? "240" : plan == "D → H4 → M15" ? "15" : "5"
string N1 = plan == "W → D → H4" ? "Weekly" : plan == "D → H4 → M15" ? "Daily" : "H4"
string N2 = plan == "W → D → H4" ? "Daily" : plan == "D → H4 → M15" ? "H4" : "M15"
string N3 = plan == "W → D → H4" ? "H4" : plan == "D → H4 → M15" ? "M15" : "M5"

f_sz(string s) =>
    s == "Tiny" ? size.tiny : s == "Normal" ? size.normal : size.small
f_sty(string s) =>
    s == "Dashed" ? line.style_dashed : s == "Dotted" ? line.style_dotted : line.style_solid

// A break: a wick beyond the level (default) or a body close
f_cu() =>
    brk_wick ? high : close
f_cd() =>
    brk_wick ? low : close

'''

EXTRA = r'''

// ── Top timeframe: the reaction levels (where a pullback may start) ──────────
// Sell side (resistance, for a pullback after a breakout UP): A-shapes and bearish OCs,
// bearish FVGs. Buy side: V-shapes, bullish OCs, bullish FVGs. Each dies when broken.
// Returns the two nearest above and below the close, and the nearest FVG on each side.
f_rlv(bool bd) =>
    var array<float> sl  = array.new<float>()
    var array<int>   sk  = array.new<int>()     // 1 = A-shape, 2 = OC
    var array<float> bl  = array.new<float>()
    var array<int>   bk  = array.new<int>()
    var array<float> sfh = array.new<float>()
    var array<float> sfl = array.new<float>()
    var array<float> bfh = array.new<float>()
    var array<float> bfl = array.new<float>()
    int k = array.size(sl) - 1
    while k >= 0
        if f_cu() > array.get(sl, k)
            array.remove(sl, k)
            array.remove(sk, k)
        k -= 1
    k := array.size(bl) - 1
    while k >= 0
        if f_cd() < array.get(bl, k)
            array.remove(bl, k)
            array.remove(bk, k)
        k -= 1
    k := array.size(sfh) - 1
    while k >= 0
        if f_cu() > array.get(sfh, k)
            array.remove(sfh, k)
            array.remove(sfl, k)
        k -= 1
    k := array.size(bfl) - 1
    while k >= 0
        if f_cd() < array.get(bfl, k)
            array.remove(bfh, k)
            array.remove(bfl, k)
        k -= 1
    if close[1] > open[1] and close < open
        array.push(sl, math.max(f_bh(0, bd), f_bh(1, bd)))
        array.push(sk, 1)
    if close[1] < open[1] and close > open
        array.push(bl, math.min(f_bl(0, bd), f_bl(1, bd)))
        array.push(bk, 1)
    if close[1] < open[1] and close < open
        array.push(sl, close[1])
        array.push(sk, 2)
    if close[1] > open[1] and close > open
        array.push(bl, close[1])
        array.push(bk, 2)
    if not na(low[2]) and low[2] > high
        array.push(sfh, low[2])
        array.push(sfl, high)
    if not na(high[2]) and high[2] < low
        array.push(bfh, low)
        array.push(bfl, high[2])
    while array.size(sl) > 60
        array.shift(sl)
        array.shift(sk)
    while array.size(bl) > 60
        array.shift(bl)
        array.shift(bk)
    while array.size(sfh) > 40
        array.shift(sfh)
        array.shift(sfl)
    while array.size(bfh) > 40
        array.shift(bfh)
        array.shift(bfl)
    float s1 = na
    int   s1k = 0
    float s2 = na
    int   s2k = 0
    for i = 0 to array.size(sl) - 1
        if array.size(sl) > 0
            float v = array.get(sl, i)
            if v > close
                if na(s1) or v < s1
                    s2 := s1
                    s2k := s1k
                    s1 := v
                    s1k := array.get(sk, i)
                else if na(s2) or v < s2
                    s2 := v
                    s2k := array.get(sk, i)
    float b1 = na
    int   b1k = 0
    float b2 = na
    int   b2k = 0
    for i = 0 to array.size(bl) - 1
        if array.size(bl) > 0
            float v = array.get(bl, i)
            if v < close
                if na(b1) or v > b1
                    b2 := b1
                    b2k := b1k
                    b1 := v
                    b1k := array.get(bk, i)
                else if na(b2) or v > b2
                    b2 := v
                    b2k := array.get(bk, i)
    float fsh = na
    float fsl = na
    for i = 0 to array.size(sfh) - 1
        if array.size(sfh) > 0
            if array.get(sfl, i) > close and (na(fsl) or array.get(sfl, i) < fsl)
                fsh := array.get(sfh, i)
                fsl := array.get(sfl, i)
    float fbh = na
    float fbl = na
    for i = 0 to array.size(bfh) - 1
        if array.size(bfh) > 0
            if array.get(bfh, i) < close and (na(fbh) or array.get(bfh, i) > fbh)
                fbh := array.get(bfh, i)
                fbl := array.get(bfl, i)
    [s1[1], s1k[1], s2[1], s2k[1], b1[1], b1k[1], b2[1], b2k[1], fsh[1], fsl[1], fbh[1], fbl[1]]

// ── Story timeframe: the fractal CHoCH and its candle ────────────────────────
// CHoCH = a wick beyond the latest fractal high / low that turns the fractal trend.
f_t2(simple int n) =>
    var float fh  = na
    var int   fht = na
    var bool  fhx = true
    var float fl  = na
    var int   flt = na
    var bool  flx = true
    var int   fdir = 0
    var int   chn = 0
    float ph = ta.pivothigh(high, n, n)
    float pl = ta.pivotlow(low, n, n)
    if not na(ph)
        fh  := ph
        fht := time[n]
        fhx := false
    if not na(pl)
        fl  := pl
        flt := time[n]
        flx := false
    int   ch  = 0
    float chl = na
    int   chp = na
    if not fhx and high > fh
        fhx := true
        if fdir != 1
            fdir := 1
            ch := 1
            chl := fh
            chp := fht
    if not flx and low < fl
        flx := true
        if fdir != -1
            fdir := -1
            ch := -1
            chl := fl
            chp := flt
    if ch != 0
        chn += 1
    [ch[1], chl[1], chp[1], chn[1], open[1], high[1], low[1], close[1], time[1]]

// ── Entry timeframe: sweep, sweep and break ──────────────────────────────────
f_forms(simple int n, simple int win) =>
    bool b_sw = close[1] < open[1] and close > open and low < low[1] and close > low[1]
    bool s_sw = close[1] > open[1] and close < open and high > high[1] and close < high[1]
    var float fl  = na
    var float fh  = na
    var float lfh = na
    var float lfl = na
    float ph = ta.pivothigh(high, n, n)
    float pl = ta.pivotlow(low, n, n)
    if not na(ph)
        fh  := ph
        lfh := ph
    if not na(pl)
        fl  := pl
        lfl := pl
    var bool  bs_on = false
    var float bs_lo = na
    var float bs_br = na
    var int   bs_b  = na
    var bool  ss_on = false
    var float ss_hi = na
    var float ss_br = na
    var int   ss_b  = na
    if not na(fl) and low < fl and close > fl
        bs_on := not na(lfh) and lfh > close
        bs_lo := low
        bs_br := lfh
        bs_b  := bar_index
        fl := na
    if not na(fh) and high > fh and close < fh
        ss_on := not na(lfl) and lfl < close
        ss_hi := high
        ss_br := lfl
        ss_b  := bar_index
        fh := na
    bool  b_sb = false
    bool  s_sb = false
    float b_tp = na
    float s_tp = na
    if bs_on
        if close < bs_lo or bar_index - bs_b > win
            bs_on := false
        else if close > bs_br
            b_sb := true
            b_tp := bs_lo
            bs_on := false
    if ss_on
        if close > ss_hi or bar_index - ss_b > win
            ss_on := false
        else if close < ss_br
            s_sb := true
            s_tp := ss_hi
            ss_on := false
    [b_sw, s_sw, b_sb, s_sb, low, high, b_tp, s_tp, time]

f_forms1(simple int n, simple int win) =>
    [a1, a2, a3, a4, a5, a6, a7, a8, a9] = f_forms(n, win)
    [a1[1], a2[1], a3[1], a4[1], a5[1], a6[1], a7[1], a8[1], a9[1]]

// ── The three timeframes ─────────────────────────────────────────────────────
[a_cdir, a_chi, a_clo, a_chif, a_clof, a_chit, a_clot, a_bcnt, a_bdir, a_blvl, a_bopp, a_da, a_dat, a_dv, a_dvt, a_bt] = request.security(syminfo.tickerid, T1, f_structure(d_body), lookahead = barmerge.lookahead_on)
[r_s1, r_s1k, r_s2, r_s2k, r_b1, r_b1k, r_b2, r_b2k, r_fsh, r_fsl, r_fbh, r_fbl] = request.security(syminfo.tickerid, T1, f_rlv(d_body), lookahead = barmerge.lookahead_on)
[b_cdir, b_chi, b_clo, b_chif, b_clof, b_chit, b_clot, b_bcnt, b_bdir, b_blvl, b_bopp, b_da, b_dat, b_dv, b_dvt, b_bt] = request.security(syminfo.tickerid, T2, f_structure(d_body), lookahead = barmerge.lookahead_on)
[b_ch, b_chl, b_chp, b_chn, b_o, b_h, b_l, b_c, b_t] = request.security(syminfo.tickerid, T2, f_t2(fr_n), lookahead = barmerge.lookahead_on)
[q_bsw, q_ssw, q_bsb, q_ssb, q_l, q_h, q_btp, q_stp, q_t] = request.security(syminfo.tickerid, T3, f_forms1(fr_n, en_win), lookahead = barmerge.lookahead_on)
[d_bsw, d_ssw, d_bsb, d_ssb, d_l, d_h, d_btp, d_stp, d_t] = f_forms(fr_n, en_win)
// on the entry timeframe itself, its own candles (no one-candle delay)
bool e_own = timeframe.in_seconds() == timeframe.in_seconds(T3)
bool  e_bsw = e_own ? d_bsw : q_bsw
bool  e_ssw = e_own ? d_ssw : q_ssw
bool  e_bsb = e_own ? d_bsb : q_bsb
bool  e_ssb = e_own ? d_ssb : q_ssb
float e_l   = e_own ? d_l : q_l
float e_h   = e_own ? d_h : q_h
float e_btp = e_own ? d_btp : q_btp
float e_stp = e_own ? d_stp : q_stp
int   e_t   = e_own ? d_t : q_t
bool  e_new = not na(e_t) and e_t != nz(e_t[1]) and (not e_own or barstate.isconfirmed)
bool  chart_ok = timeframe.in_seconds() <= timeframe.in_seconds(T2)

int D1 = a_bdir == "bullish" ? 1 : a_bdir == "bearish" ? -1 : 0
int D2 = b_bdir == "bullish" ? 1 : b_bdir == "bearish" ? -1 : 0

// ── Drawing helpers ──────────────────────────────────────────────────────────
var array<label> st_l = array.new<label>()
var st_last = array.from("")
f_story(int t, float y, bool above, string txt) =>
    if not na(t) and not na(y)
        array.set(st_last, 0, txt)
        if st_mode != "Off"
            if array.size(st_l) > 0
                label prev = array.last(st_l)
                if st_mode == "Latest note only"
                    label.delete(array.pop(st_l))
                else if st_mode == "Latest note + dots (hover)"
                    label.set_tooltip(prev, label.get_text(prev))
                    label.set_text(prev, "●")
                    label.set_style(prev, label.style_none)
                    label.set_textcolor(prev, st_dot)
                    label.set_size(prev, size.tiny)
            array.push(st_l, label.new(t, y, txt, xloc = xloc.bar_time, style = above ? label.style_label_down : label.style_label_up,
                 color = color.new(st_bg, st_op), textcolor = st_tx, size = f_sz(st_sz), textalign = text.align_left))
            while array.size(st_l) > (st_mode == "Latest note only" ? 1 : st_mode == "Latest note + dots (hover)" ? st_n + 1 : st_n)
                label.delete(array.shift(st_l))

var array<line>  sl_l = array.new<line>()
var array<label> sl_b = array.new<label>()
f_sline(int t1, int t2, float y, string txt, bool above) =>
    if sl_on and not na(t1) and not na(t2) and not na(y)
        array.push(sl_l, line.new(t1, y, t2, y, xloc = xloc.bar_time, color = sl_col, width = 1))
        array.push(sl_b, label.new(t1 + int((t2 - t1) / 2), y, txt, xloc = xloc.bar_time, style = above ? label.style_label_down : label.style_label_up,
             color = color.new(color.black, 100), textcolor = sl_tx, size = f_sz(lv_sz)))
        while array.size(sl_l) > st_n * 2
            line.delete(array.shift(sl_l))
        while array.size(sl_b) > st_n * 2
            label.delete(array.shift(sl_b))

// POIs: demand (buys) / supply (sells) on the story timeframe, after it lines up
var array<box>   pz   = array.new<box>()
var array<float> pz_t = array.new<float>()
var array<float> pz_b = array.new<float>()
var array<bool>  pz_d = array.new<bool>()
var array<bool>  pz_m = array.new<bool>()
var array<bool>  pz_e = array.new<bool>()
f_pz_drop(int k) =>
    box.delete(array.get(pz, k))
    array.remove(pz, k)
    array.remove(pz_t, k)
    array.remove(pz_b, k)
    array.remove(pz_d, k)
    array.remove(pz_m, k)
    array.remove(pz_e, k)
f_pz_add(float top, float bot, int t, bool dem) =>
    if not na(top) and not na(bot) and not na(t) and top > bot
        color c = dem ? pz_dem : pz_sup
        array.push(pz, box.new(t, top, time, bot, xloc = xloc.bar_time, border_color = pz_on ? c : color.new(c, 100), bgcolor = pz_on ? color.new(c, pz_op) : color.new(c, 100),
             text = pz_on ? N2 + (dem ? " demand POI" : " supply POI") : "", text_size = f_sz(lv_sz), text_color = c, text_halign = text.align_right, text_valign = text.align_center))
        array.push(pz_t, top)
        array.push(pz_b, bot)
        array.push(pz_d, dem)
        array.push(pz_m, false)
        array.push(pz_e, false)
        while array.size(pz) > pz_max
            f_pz_drop(0)

f_kind(int k, bool sell) =>
    k == 1 ? (sell ? "A-shape (resistance)" : "V-shape (support)") : k == 2 ? (sell ? "bearish OC" : "bullish OC") : "level"

// ── The story ────────────────────────────────────────────────────────────────
// phase: 0 none · 1 pullback expected · 2 reaction level reached · 3 T2 broke against
// (T1 pullback confirmed) · 4 T2 CHoCH back (T2 pullback, in line) · 5 aligned
var int   ph      = 0
var int   k1      = 0
var int   k2      = 0
var int   kc      = 0
var float mn_lvl  = na      // the main story-timeframe high (buys) / low (sells)
var int   mn_t    = na
var float rx_lvl  = na      // the reaction level reached
var float pc_lo   = na      // the story-timeframe candle with the lowest low since its last breakout (demand POI)
var float pc_lot  = na
var int   pc_lt   = na
var float pc_hi   = na      // ... highest high (supply POI)
var float pc_hib  = na
var int   pc_ht   = na
bool t2_new = not na(b_t) and b_t != nz(b_t[1])

if chart_ok
    string up = D1 > 0 ? "up" : "down"
    string dn = D1 > 0 ? "down" : "up"
    string HI = D1 > 0 ? "high" : "low"
    // the story-timeframe candle that will be the next POI
    if t2_new
        if na(pc_lo) or b_l < pc_lo
            pc_lo  := b_l
            pc_lot := math.max(b_o, b_c)
            pc_lt  := b_t
        if na(pc_hi) or b_h > pc_hi
            pc_hi  := b_h
            pc_hib := math.min(b_o, b_c)
            pc_ht  := b_t
    // 1. a top-timeframe breakout starts a new story
    if not na(a_bcnt) and a_bcnt != k1
        k1 := a_bcnt
        if D1 != 0 and not na(k1[1]) and k1[1] != 0
            ph := 1
            mn_lvl := na
            rx_lvl := na
            f_story(time, D1 > 0 ? high : low, D1 > 0, N1 + " external breakout " + up + " (" + (brk_wick ? "wick" : "body close") + " beyond " + str.tostring(a_blvl, format.mintick) + ").\nA pullback is expected. Watch the reaction levels " + (D1 > 0 ? "above" : "below") + ":\n" + (D1 > 0 ? "A-shapes / resistance, bearish OCs, bearish FVGs." : "V-shapes / support, bullish OCs, bullish FVGs."))
    // 2. price reaches a reaction level on the far side
    if ph == 1 and D1 != 0
        float lv = D1 > 0 ? r_s1 : r_b1
        float fz = D1 > 0 ? r_fsl : r_fbh
        bool hit_l = not na(lv) and (D1 > 0 ? high >= lv : low <= lv)
        bool hit_f = not na(fz) and (D1 > 0 ? high >= fz : low <= fz)
        if hit_l or hit_f
            ph := 2
            rx_lvl := hit_l ? lv : fz
            string kd = hit_l ? f_kind(D1 > 0 ? r_s1k : r_b1k, D1 > 0) : (D1 > 0 ? "bearish FVG" : "bullish FVG")
            f_story(time, D1 > 0 ? high : low, D1 > 0, "Price reached the " + N1 + " " + kd + " " + str.tostring(rx_lvl, format.mintick) + ".\nWatch for an " + N2 + " breakout " + dn + ": the " + N1 + " pullback.")
    // 3 / 5. a story-timeframe breakout
    if not na(b_bcnt) and b_bcnt != k2
        k2 := b_bcnt
        if D1 != 0 and D2 == D1 and ph >= 1 and ph <= 2
            // still the breakout's move: each story-timeframe breakout with it is a continuation
            f_sline(b_bt, time, b_blvl, N2 + " BOS " + up, D1 > 0)
            f_story(time, D1 > 0 ? high : low, D1 > 0, N2 + " breakout " + up + ": a continuation of the " + N1 + " breakout.\nNo pullback yet: waiting for price to reach a reaction level\n(" + (D1 > 0 ? "A-shape / resistance, OC, FVG, supply above" : "V-shape / support, OC, FVG, demand below") + ") and an " + N2 + " breakout " + dn + ".")
        else if D1 != 0 and D2 == -D1 and ph >= 1 and ph <= 2
            ph := 3
            mn_lvl := D1 > 0 ? b_chi : b_clo
            mn_t   := D1 > 0 ? b_chit : b_clot
            f_sline(b_bt, time, b_blvl, N2 + " BOS " + dn, D1 < 0)
            f_story(time, D1 > 0 ? low : high, D1 < 0, N2 + " breakout " + dn + ": the " + N1 + " pullback is confirmed.\nAfter every breakout a pullback is expected:\nwatch for an " + N2 + " CHoCH " + up + ". " + N2 + " stays " + (D1 > 0 ? "bearish" : "bullish") + "\nuntil its main " + HI + " " + str.tostring(mn_lvl, format.mintick) + " is taken out.")
        else if D1 != 0 and D2 == D1 and ph >= 3 and ph <= 4
            ph := 5
            f_sline(mn_t, time, mn_lvl, N2 + " BOS " + up, D1 > 0)
            if D1 > 0
                f_pz_add(pc_lot, pc_lo, pc_lt, true)
            else
                f_pz_add(pc_hi, pc_hib, pc_ht, false)
            f_story(time, D1 > 0 ? high : low, D1 > 0, "The main " + N2 + " " + HI + " is taken out: " + N2 + " is aligned with the " + N1 + ".\nEntries: the " + N2 + (D1 > 0 ? " demand" : " supply") + " POI with an " + N3 + " confirmation.\nTarget: the " + N1 + " external " + HI + ".")
            mn_lvl := na
        else if D1 != 0 and D2 == D1 and ph == 5
            if D1 > 0
                f_pz_add(pc_lot, pc_lo, pc_lt, true)
            else
                f_pz_add(pc_hi, pc_hib, pc_ht, false)
            f_sline(b_bt, time, b_blvl, N2 + " BOS " + up, D1 > 0)
        pc_lo := na
        pc_hi := na
    // 4. a story-timeframe CHoCH back in the top timeframe's direction
    if not na(b_chn) and b_chn != kc
        kc := b_chn
        if ph == 3 and b_ch == D1
            ph := 4
            f_sline(b_chp, time, b_chl, N2 + " CHoCH " + up, D1 > 0)
            f_story(time, D1 > 0 ? high : low, D1 > 0, N2 + " CHoCH " + up + ": the " + N2 + " pullback starts, in line with the " + N1 + ".\nCareful: " + N2 + " is still " + (D1 > 0 ? "bearish" : "bullish") + " until the main " + HI + "\n" + str.tostring(mn_lvl, format.mintick) + " is taken out; it can still push price " + dn + ".")

// POIs: extend, fade once reached, remove once closed through; entries at a reached POI
if array.size(pz) > 0
    int k = array.size(pz) - 1
    while k >= 0
        box   bx = array.get(pz, k)
        bool  dm = array.get(pz_d, k)
        float tp = array.get(pz_t, k)
        float bb = array.get(pz_b, k)
        if dm ? close < bb : close > tp
            f_pz_drop(k)
        else
            if not array.get(pz_m, k)
                box.set_right(bx, time)
                if dm ? low <= tp : high >= bb
                    array.set(pz_m, k, true)
                    if pz_on
                        box.set_bgcolor(bx, color.new(pz_mit, pz_op))
                        box.set_border_color(bx, pz_mit)
                        box.set_text_color(bx, pz_mit)
            if array.get(pz_m, k) and not array.get(pz_e, k) and e_new
                bool sw = dm ? e_bsw : e_ssw
                bool sb = dm ? e_bsb : e_ssb
                float tch = dm ? (sb ? e_btp : e_l) : (sb ? e_stp : e_h)
                bool ok = (en_conf != "Sweep and break" and sw) or (en_conf != "Sweep" and sb)
                if ok and not na(tch) and tch <= tp and tch >= bb
                    array.set(pz_e, k, true)
                    string nm = sb ? "sweep and break" : "sweep"
                    label.new(bar_index, dm ? low : high, dm ? "▲" : "▼", yloc = dm ? yloc.belowbar : yloc.abovebar, style = label.style_none,
                         textcolor = en_col, size = size.normal, tooltip = N3 + " " + nm + " at the " + N2 + (dm ? " demand" : " supply") + " POI")
                    f_story(time, dm ? low : high, not dm, N3 + " " + nm + " at the " + N2 + (dm ? " demand" : " supply") + " POI: entry.\nInvalid beyond the POI (" + str.tostring(dm ? bb : tp, format.mintick) + ").\nTarget: the " + N1 + " external " + (dm ? "high." : "low."))
        k -= 1

// ── The levels at the last candle ────────────────────────────────────────────
var array<line>  cl = array.new<line>()
var array<label> cb = array.new<label>()
var array<box>   cx = array.new<box>()
f_lvl(int t, float y, string txt, color c, string st, int w) =>
    if not na(t) and not na(y)
        array.push(cl, line.new(t, y, time, y, xloc = xloc.bar_time, extend = extend.right, color = c, style = st, width = w))
        array.push(cb, label.new(bar_index + 3, y, txt + "  " + str.tostring(y, format.mintick), style = label.style_label_left,
             color = color.new(color.black, 100), textcolor = lv_tx, size = f_sz(lv_sz)))

f_tpos(string p) =>
    p == "Top right" ? position.top_right : p == "Bottom right" ? position.bottom_right : p == "Top left" ? position.top_left : position.bottom_left
var table tb = table.new(f_tpos(tb_pos), 2, 8, bgcolor = tb_bg, border_width = 1, border_color = color.new(color.gray, 75))
f_row(int r, string a, string b) =>
    table.cell(tb, 0, r, a, text_color = color.gray, text_size = size.small, text_halign = text.align_left)
    table.cell(tb, 1, r, b, text_color = tb_tx, text_size = size.small, text_halign = text.align_left)

if barstate.islast
    for l in cl
        line.delete(l)
    for b in cb
        label.delete(b)
    for x in cx
        box.delete(x)
    array.clear(cl)
    array.clear(cb)
    array.clear(cx)
    if chart_ok
        if t1_on and not na(a_chi) and not na(a_clo)
            f_lvl(a_chit, a_chi, N1 + " external high", t1_col, f_sty(t1_sty), t1_w)
            f_lvl(a_clot, a_clo, N1 + " external low", t1_col, f_sty(t1_sty), t1_w)
            if rg_on
                array.push(cx, box.new(math.min(a_chit, a_clot), a_chi, time, a_clo, xloc = xloc.bar_time, extend = extend.right,
                     border_color = color.new(rg_col, 100), bgcolor = color.new(rg_col, rg_op)))
        if D1 != 0 and ph >= 1 and ph <= 3
            if rx_on
                float s1 = D1 > 0 ? r_s1 : r_b1
                float s2 = D1 > 0 ? r_s2 : r_b2
                if not na(s1)
                    f_lvl(time, s1, N1 + " " + f_kind(D1 > 0 ? r_s1k : r_b1k, D1 > 0) + " (reaction level)", rx_col, line.style_dashed, 1)
                if not na(s2)
                    f_lvl(time, s2, N1 + " " + f_kind(D1 > 0 ? r_s2k : r_b2k, D1 > 0) + " (reaction level)", rx_col, line.style_dashed, 1)
            if fv_on
                float zh = D1 > 0 ? r_fsh : r_fbh
                float zl = D1 > 0 ? r_fsl : r_fbl
                if not na(zh) and not na(zl)
                    array.push(cx, box.new(bar_index - 20, zh, bar_index + 12, zl, border_color = fv_col, bgcolor = color.new(fv_col, fv_op),
                         text = N1 + (D1 > 0 ? " bearish FVG (reaction zone)" : " bullish FVG (reaction zone)"), text_size = f_sz(lv_sz), text_color = lv_tx))
        if mn_on and not na(mn_lvl) and (ph == 3 or ph == 4)
            f_lvl(mn_t, mn_lvl, "main " + N2 + (D1 > 0 ? " high" : " low") + " (" + N2 + " stays against the " + N1 + " until it is taken out)", mn_col, line.style_solid, 2)
    if tb_on
        table.clear(tb, 0, 0, 1, 7)
        if not chart_ok
            f_row(0, plan, "Put the chart on " + N2 + " or lower (" + N3 + " for the entries)")
        else
            string phs = ph == 0 ? "waiting for a " + N1 + " breakout" : ph == 1 ? "pullback expected: watch the reaction levels" : ph == 2 ? "reaction level reached: watch for an " + N2 + " breakout against" : ph == 3 ? N1 + " pullback confirmed: watch for an " + N2 + " CHoCH back" : ph == 4 ? N2 + " pullback, in line: watch the main " + N2 + (D1 > 0 ? " high" : " low") : "aligned: entries at the " + N2 + " POIs with an " + N3 + " confirmation"
            f_row(0, "Plan", plan + " · breaks by " + (brk_wick ? "wick" : "body close"))
            f_row(1, N1, D1 > 0 ? "bullish · external range " + str.tostring(a_clo, format.mintick) + " – " + str.tostring(a_chi, format.mintick) : D1 < 0 ? "bearish · external range " + str.tostring(a_clo, format.mintick) + " – " + str.tostring(a_chi, format.mintick) : "—")
            f_row(2, N2, D2 > 0 ? "bullish" : D2 < 0 ? "bearish" : "—")
            f_row(3, "Story", phs)
            if not na(mn_lvl) and (ph == 3 or ph == 4)
                f_row(4, "Main " + N2, str.tostring(mn_lvl, format.mintick))
            f_row(5, "Entries", N3 + " " + (en_conf == "Both" ? "sweep or sweep and break" : en_conf == "Sweep" ? "sweep" : "sweep and break") + (e_own ? "" : " (read from " + N3 + ")"))
            if array.get(st_last, 0) != ""
                f_row(6, "✎", array.get(st_last, 0))
'''

# the story's phase is "sph" (keeps clear of the pivot variables inside the functions)
i_st = EXTRA.index('// ── The story ──')
EXTRA = EXTRA[:i_st] + re.sub(r'\bph\b', 'sph', EXTRA[i_st:])
body = HEAD + ENGINE + EXTRA
open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
print(OUT, body.count('\n'), 'lines,', n_before, 'breaks routed through the wick / body setting')
