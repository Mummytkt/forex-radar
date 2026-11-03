"""Builds MummyTKT_MTF_Storyline.pine (user, 2026-11-02): the structure story drawn in
Documents/MTF_Storyline_Buys.png / _Sells.png (pine/mtf_storyline_picture.py). Buys; sells mirror.

  1. Top timeframe (T1) breakout: a body close beyond its external level. Labelled where it happened.
  2. Story timeframe (T2) with T1: every External T2 break = "T2 bullish cont". The pullback line is the
     last T2 low that made a new high (lows take out highs in a bullish move); one line, moves up.
  3. A T2 body close below it = "Pullback break": the T1 pullback. T1 range: high (also the T2 range
     high), low, 0.5.
  4. T2 against T1: each External T2 break down = "T2 bearish cont". Tracked: the last T2 high that made a
     new low (highs take out lows in a bearish move).
  5. A T2 close above it = "T2 pullback": back in alignment with T1. T2 range low = the leg's low.
  6. A T2 close below the T2 range low = T2 bearish cont again; the new T2 range high = the high that
     took out the low (not an inner high of the leg).
  7. A T1 close above the T1 range high = T1 continues (new story). A T1 close below the T1 range low
     = T1 turns bearish; its external high = the high that took out the low. Mirrored story.
Plans: W -> D -> H4 · D -> H4 -> M15 · H4 -> M15 -> M5 · Custom. The engine (first start only) and the
story-note helper are copied from MummyTKT_PullbackStory.pine.
"""
SRC = 'C:/Users/u/forex-radar/pine/MummyTKT_PullbackStory.pine'
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_MTF_Storyline.pine'
src = open(SRC, encoding='utf-8').read().split('\n')


def cut(start, stop):
    a = next(i for i, l in enumerate(src) if l.startswith(start))
    b = next(i for i, l in enumerate(src) if i > a and l.startswith(stop))
    return '\n'.join(src[a:b]).rstrip() + '\n'


ENGINE = cut('f_sz(string s) =>', '// ── Top timeframe: the reaction levels')
# The Daily external high / low: the Bias Pointer's engine exactly as it is (no changes).
NOTES = cut('var array<label> st_l', 'var array<line>  sl_l')
NOTES = NOTES.replace('    if not na(t) and not na(y)\n        array.set(st_last', '    if chart_ok and not na(t) and not na(y)\n        array.set(st_last')
assert NOTES.count('if chart_ok and') == 1

STY = 'options = ["Solid", "Dashed", "Dotted"]'
SZ = 'options = ["Tiny", "Small", "Normal"]'
HEAD = r'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — MTF Storyline (display only, no alerts) · 2026-11-02
//
// The story of the top timeframe told on the story timeframe (pick the plan: W → D → H4,
// D → H4 → M15, H4 → M15 → M5 or your own). Buys; sells are the mirror. Breaks are body closes.
//   1. Top-timeframe breakout (a close beyond its external level), labelled where it happened.
//   2. Story-timeframe continuations: every External break with it = "bullish cont". The pullback
//      line is the last story-timeframe low that made a new high (lows take out highs).
//   3. A close below the pullback line = "Pullback break": the top-timeframe pullback. Its range:
//      high (also the story-timeframe range high), low, 0.5.
//   4. The story timeframe against it: each External break down = "bearish cont". Tracked: the last
//      high that made a new low (highs take out lows).
//   5. A close above that high = "pullback": back in alignment. Range low = the leg's low.
//   6. A close below that range low = bearish cont again; the range high = the high that took out
//      the low (not an inner high of the leg).
//   7. The top timeframe's external high / low are always the Bias Pointer's (its most recent
//      structure). Each new breakout of it starts the story again, in its direction.
// ─────────────────────────────────────────────────────────────────────────────

indicator("MummyTKT — MTF Storyline", overlay = true, behind_chart = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 100, max_bars_back = 5000)

const string G_PL = "1 · Plan and breaks"
const string G_ST = "2 · Story notes and tables"
const string G_T1 = "3 · Top-timeframe lines"
const string G_T2 = "4 · Story-timeframe lines"
const string G_BR = "5 · Break lines (cont / pullback)"
const string G_TG = "6 · Tags"

string plan     = input.string("D → H4 → M15", "Plan (top → story → entry)", options = ["W → D → H4", "D → H4 → M15", "H4 → M15 → M5", "Custom"], group = G_PL,
     tooltip = "Weekly story: W → D → H4. The top timeframe sets the direction, the story timeframe tells it. Put the chart on the story timeframe or lower.")
string cu_t1    = input.timeframe("D", "Custom: top", group = G_PL, inline = "cu")
string cu_t2    = input.timeframe("240", "story", group = G_PL, inline = "cu")
string cu_t3    = input.timeframe("15", "entry", group = G_PL, inline = "cu")
bool   t1_wick  = input.string("Body close", "Top-timeframe break by", options = ["Body close", "Wick"], group = G_PL,
     tooltip = "Body close (default): the top-timeframe candle must close beyond its external level (the level is on the wick).") == "Wick"
bool   t2_wick  = input.string("Body close", "Story-timeframe break by", options = ["Body close", "Wick"], group = G_PL) == "Wick"
bool   d_body   = input.string("Wick", "External highs / lows from", options = ["Wick", "Body"], group = G_PL) == "Body"
bool   h2_body  = input.string("Body", "Story-timeframe levels from", options = ["Body", "Wick"], group = G_PL,
     tooltip = "Body: the story-timeframe lines (pullback lines, H4 range high / low) sit on the candle bodies, so a break is a body close beyond a body. Wick: they sit on the wicks.") == "Body"

string st_mode  = input.string("Dots only (hover)", "Story on the chart", options = ["Dots only (hover)", "Latest note + dots (hover)", "Latest note only", "Last N notes", "Off"], group = G_ST)
int    st_n     = input.int(8, "N (notes or dots kept)", minval = 1, maxval = 40, group = G_ST)
color  st_bg    = input.color(#0E3B43, "Note background", group = G_ST, inline = "sb")
int    st_op    = input.int(90, "opacity %", minval = 0, maxval = 100, group = G_ST, inline = "sb")
color  st_tx    = input.color(color.white, "Note text", group = G_ST, inline = "st")
string st_sz    = input.string("Small", "size", ''' + SZ + ''', group = G_ST, inline = "st")
color  st_dot   = input.color(#26C6DA, "Note dots", group = G_ST)
bool   sk_on    = input.bool(true, "Story table", group = G_ST, inline = "sk")
string sk_pos   = input.string("Bottom right", "", options = ["Top right", "Bottom right", "Top left", "Bottom left", "Middle right", "Middle left"], group = G_ST, inline = "sk")
int    sk_n     = input.int(3, "Notes in the story table (newest first)", minval = 1, maxval = 10, group = G_ST)
color  sk_bg    = input.color(color.new(#0E3B43, 10), "Story table background", group = G_ST, inline = "sc")
color  sk_tx    = input.color(color.white, "text", group = G_ST, inline = "sc")
bool   tb_on    = input.bool(true, "Status table", group = G_ST, inline = "tb")
string tb_pos   = input.string("Top right", "", options = ["Top right", "Bottom right", "Top left", "Bottom left"], group = G_ST, inline = "tb")
color  tb_bg    = input.color(color.new(#0F1120, 10), "Status table background", group = G_ST, inline = "tc")
color  tb_tx    = input.color(color.white, "text", group = G_ST, inline = "tc")

bool   x_on     = input.bool(true, "External high / low", group = G_T1, inline = "x")
color  x_col    = input.color(#E0E0E0, "", group = G_T1, inline = "x")
string x_sty    = input.string("Solid", "", ''' + STY + ''', group = G_T1, inline = "x")
int    x_w      = input.int(2, "width", minval = 1, maxval = 4, group = G_T1, inline = "x")
bool   eq_on    = input.bool(true, "Range 0.5 (after the pullback)", group = G_T1, inline = "eq")
color  eq_col   = input.color(#9E9E9E, "", group = G_T1, inline = "eq")
string eq_sty   = input.string("Dashed", "", ''' + STY + ''', group = G_T1, inline = "eq")
int    eq_w     = input.int(1, "width", minval = 1, maxval = 4, group = G_T1, inline = "eq")
bool   sh_on    = input.bool(true, "Shade premium / discount", group = G_T1, inline = "sh")
color  sh_bull  = input.color(#26A69A, "buys half", group = G_T1, inline = "sh")
color  sh_bear  = input.color(#EF5350, "sells half", group = G_T1, inline = "sh")
int    sh_op    = input.int(5, "opacity %", minval = 0, maxval = 100, group = G_T1, inline = "sh")
color  lv_tx    = input.color(#E0E0E0, "Line label text", group = G_T1, inline = "lt")
string lv_sz    = input.string("Small", "size", ''' + SZ + ''', group = G_T1, inline = "lt")
bool   lv_px    = input.bool(true, "Show prices on line labels", group = G_T1)

bool   pl_on    = input.bool(true, "Pullback line (with the top timeframe)", group = G_T2, inline = "pl")
color  pl_col   = input.color(#29B6F6, "", group = G_T2, inline = "pl")
string pl_sty   = input.string("Solid", "", ''' + STY + ''', group = G_T2, inline = "pl")
int    pl_w     = input.int(2, "width", minval = 1, maxval = 4, group = G_T2, inline = "pl")
bool   rh_on    = input.bool(true, "Story-timeframe range high / low", group = G_T2, inline = "rh")
color  rh_col   = input.color(#FFA726, "", group = G_T2, inline = "rh")
string rh_sty   = input.string("Solid", "", ''' + STY + ''', group = G_T2, inline = "rh")
int    rh_w     = input.int(2, "width", minval = 1, maxval = 4, group = G_T2, inline = "rh")
bool   rx_on    = input.bool(true, "Show the forming edge of the story-timeframe range", group = G_T2, inline = "rx")
string rx_sty   = input.string("Dashed", "style", options = ["Solid", "Dashed", "Dotted"], group = G_T2, inline = "rx")

bool   br_with  = input.bool(true, "Cont breaks with the top timeframe", group = G_BR, inline = "bw")
color  br_wcol  = input.color(#26A69A, "", group = G_BR, inline = "bw")
bool   br_agst  = input.bool(true, "Cont breaks against it", group = G_BR, inline = "ba")
color  br_acol  = input.color(#EF5350, "", group = G_BR, inline = "ba")
string br_sty   = input.string("Dotted", "Break line style", ''' + STY + ''', group = G_BR, inline = "bs")
int    br_w     = input.int(1, "width", minval = 1, maxval = 4, group = G_BR, inline = "bs")
color  br_tx    = input.color(#E0E0E0, "Break text", group = G_BR, inline = "bt")
string br_sz    = input.string("Small", "size", ''' + SZ + ''', group = G_BR, inline = "bt")
int    br_n     = input.int(12, "Break lines kept", minval = 1, maxval = 60, group = G_BR)

bool   tg_bo    = input.bool(true, "Top-timeframe breakout", group = G_TG, inline = "t1")
color  tg_boc   = input.color(#212121, "", group = G_TG, inline = "t1")
bool   tg_pb    = input.bool(true, "Pullback break", group = G_TG, inline = "t2")
color  tg_pbc   = input.color(#E53935, "", group = G_TG, inline = "t2")
bool   tg_al    = input.bool(true, "Story-timeframe pullback (back in alignment)", group = G_TG, inline = "t3")
color  tg_alc   = input.color(#00C853, "", group = G_TG, inline = "t3")
color  tg_tx    = input.color(color.white, "Tag text", group = G_TG, inline = "tt")
string tg_sz    = input.string("Small", "size", ''' + SZ + ''', group = G_TG, inline = "tt")
int    tg_op    = input.int(100, "Tag opacity % (on top of the colour box's own opacity)", minval = 0, maxval = 100, group = G_TG)
int    tg_n     = input.int(1, "Tags kept of each kind (1 = only the newest)", minval = 1, maxval = 20, group = G_TG)

string T1 = plan == "W → D → H4" ? "W" : plan == "D → H4 → M15" ? "D" : plan == "H4 → M15 → M5" ? "240" : cu_t1
string T2 = plan == "W → D → H4" ? "D" : plan == "D → H4 → M15" ? "240" : plan == "H4 → M15 → M5" ? "15" : cu_t2
string T3 = plan == "W → D → H4" ? "240" : plan == "D → H4 → M15" ? "15" : plan == "H4 → M15 → M5" ? "5" : cu_t3
f_tfn(string tf) =>
    int s = timeframe.in_seconds(tf)
    s >= 2419200 ? "Monthly" : s == 604800 ? "Weekly" : s == 86400 ? "Daily" : s % 3600 == 0 ? "H" + str.tostring(math.round(s / 3600)) : "M" + str.tostring(math.round(s / 60))
string N1 = f_tfn(T1)
string N2 = f_tfn(T2)
string PLAN = N1 + " → " + N2 + " → " + f_tfn(T3)

'''

BODY = r'''
// ── Candles of each timeframe (the last closed one) ──────────────────────────
f_cnd() =>
    [open[1], high[1], low[1], close[1], time[1]]
[a_cdir, a_chi, a_clo, a_chif, a_clof, a_chit, a_clot, a_bcnt, a_bdir, a_blvl, a_bopp, a_da, a_dat, a_dv, a_dvt, a_bt] = request.security(syminfo.tickerid, T1, f_structure(d_body, t1_wick), lookahead = barmerge.lookahead_on)
[x1o, x1h, x1l, x1c, x1t] = request.security(syminfo.tickerid, T1, f_cnd(), lookahead = barmerge.lookahead_on)
[x2o, x2h, x2l, x2c, x2t] = request.security(syminfo.tickerid, T2, f_cnd(), lookahead = barmerge.lookahead_on)
// the story-timeframe candle's high / low for the story lines (body or wick, per "Story-timeframe levels from")
float x2H = h2_body ? math.max(x2o, x2c) : x2h
float x2L = h2_body ? math.min(x2o, x2c) : x2l
bool x1_new  = not na(x1t) and x1t != nz(x1t[1])
bool x2_new  = not na(x2t) and x2t != nz(x2t[1])
bool chart_ok = timeframe.in_seconds() <= timeframe.in_seconds(T2)
int  AD = a_bdir == "bullish" ? 1 : a_bdir == "bearish" ? -1 : 0

// a beyond b in direction d (d > 0: above, d < 0: below)
f_gt(float a, float b, int d) =>
    d > 0 ? a > b : a < b

// candle history of both timeframes (high, low, time)
var array<float> q1h = array.new<float>()
var array<float> q1l = array.new<float>()
var array<int>   q1t = array.new<int>()
var array<float> q2h = array.new<float>()
var array<float> q2l = array.new<float>()
var array<int>   q2t = array.new<int>()
var array<float> q2c = array.new<float>()
if x1_new
    array.push(q1h, x1h)
    array.push(q1l, x1l)
    array.push(q1t, x1t)
    if array.size(q1t) > 600
        array.shift(q1h)
        array.shift(q1l)
        array.shift(q1t)
if x2_new
    array.push(q2h, x2H)
    array.push(q2l, x2L)
    array.push(q2t, x2t)
    array.push(q2c, x2c)
    if array.size(q2t) > 1500
        array.shift(q2c)
        array.shift(q2h)
        array.shift(q2l)
        array.shift(q2t)
// the highest high (hiSide) / lowest low of the story-timeframe candles from time t0 on
f_ext2(int t0, bool hiSide) =>
    float v  = na
    int   vt = na
    int   n  = array.size(q2t)
    if n > 0 and not na(t0)
        int k = n - 1
        while k >= 0 and array.get(q2t, k) >= t0
            float x = hiSide ? array.get(q2h, k) : array.get(q2l, k)
            if na(v) or (hiSide ? x > v : x < v)
                v  := x
                vt := array.get(q2t, k)
            k -= 1
    [v, vt]
// the tracker replayed over the story-timeframe candles from time t0, in direction w: the running
// extreme, the opposite extreme since it, and the last opposite extreme that made a new extreme
f_replay(int t0, int w_) =>
    float ex = na
    int   ext = na
    float dp = na
    int   dpt = na
    float ln = na
    int   lnt = na
    int   n = array.size(q2t)
    if n > 0 and not na(t0)
        int k = n - 1
        while k > 0 and array.get(q2t, k - 1) >= t0
            k -= 1
        for j = k to n - 1
            float ce = w_ > 0 ? array.get(q2h, j) : array.get(q2l, j)
            float co = w_ > 0 ? array.get(q2l, j) : array.get(q2h, j)
            float cc = array.get(q2c, j)
            // a new extreme counts (moves the line) only on a body close beyond it; a wick only extends it
            if na(ex) or (w_ > 0 ? cc > ex : cc < ex)
                if not na(dp)
                    ln  := dp
                    lnt := dpt
                ex  := ce
                ext := array.get(q2t, j)
                dp  := na
            else if w_ > 0 ? ce > ex : ce < ex
                ex  := ce
                ext := array.get(q2t, j)
                if na(dp) or (w_ > 0 ? co < dp : co > dp)
                    dp  := co
                    dpt := array.get(q2t, j)
            else if na(dp) or (w_ > 0 ? co < dp : co > dp)
                dp  := co
                dpt := array.get(q2t, j)
    [ex, ext, dp, dpt, ln, lnt]
// the top timeframe: lowSide = a broken LOW -> the highest high since it first formed; else a broken
// HIGH -> the lowest low since it first formed (an equal level up to 15 candles earlier counts)
f_since(bool lowSide, float lvl, int t0, float tol) =>
    int   n  = array.size(q1t)
    float v  = na
    int   vt = na
    if n > 0 and not na(lvl) and not na(t0)
        int s0 = n - 1
        while s0 > 0 and array.get(q1t, s0 - 1) >= t0
            s0 -= 1
        int k = s0 - 1
        int stop_ = math.max(0, s0 - 15)
        while k >= stop_
            float kh = array.get(q1h, k)
            float kl = array.get(q1l, k)
            if lowSide ? kl < lvl - tol : kh > lvl + tol
                break
            if lowSide ? math.abs(kl - lvl) <= tol : math.abs(kh - lvl) <= tol
                s0 := k
            k -= 1
        for j = s0 to n - 1
            float x = lowSide ? array.get(q1h, j) : array.get(q1l, j)
            if na(v) or (lowSide ? x > v : x < v)
                v  := x
                vt := array.get(q1t, j)
    [v, vt]

// ── Story-timeframe External breaks (as the Bias Pointer): a body close above the last A-shape (body
// top) that formed before the leg's pullback low (sells: below the last V-shape before the high).
// After a break only newer A-shapes count. These are the "cont" breaks.
var array<float> xa_l = array.new<float>()
var array<int>   xa_t = array.new<int>()
var array<float> xv_l = array.new<float>()
var array<int>   xv_t = array.new<int>()
var float u_hh  = na
var float u_pl  = na
var int   u_plt = na
var float d_ll  = na
var float d_ph  = na
var int   d_pht = na
var float u_plb = na      // the same pullback low / high read on the story-line side (body or wick)
var float d_phb = na
var float p2o   = na
var float p2c   = na
bool  ub     = false
float ub_lvl = na
int   ub_lt  = na
bool  db     = false
float db_lvl = na
float ub_pl  = na      // at an External break up: the last low that broke the high (sells: db_ph, the last high that broke the low)
int   ub_plt = na
float db_ph  = na
int   db_pht = na
int   db_lt  = na
f_last(array<float> l, array<int> t, int maxt) =>
    float v = na
    int   vt = na
    if array.size(l) > 0
        for i = array.size(l) - 1 to 0
            if array.get(t, i) <= maxt
                v := array.get(l, i)
                vt := array.get(t, i)
                break
    [v, vt]
float c2u = t2_wick ? x2h : x2c
float c2d = t2_wick ? x2l : x2c
if x2_new
    bool  nl  = na(u_pl) or x2l < u_pl
    int   plt = nl ? x2t : u_plt
    [ea, eat] = f_last(xa_l, xa_t, nl ? x2t - 1 : plt)
    if not na(u_hh) and not na(ea) and c2u > ea
        ub     := true
        ub_lvl := ea
        ub_lt  := eat
        ub_pl  := na(u_pl) ? x2L : u_plb
        ub_plt := na(u_pl) ? x2t : u_plt
        array.clear(xa_l)
        array.clear(xa_t)
        u_hh := x2h
        u_pl := na
        u_plb := na
    bool  nh  = na(d_ph) or x2h > d_ph
    int   pht = nh ? x2t : d_pht
    [ev, evt] = f_last(xv_l, xv_t, nh ? x2t - 1 : pht)
    if not na(d_ll) and not na(ev) and c2d < ev
        db     := true
        db_lvl := ev
        db_lt  := evt
        db_ph  := na(d_ph) ? x2H : d_phb
        db_pht := na(d_ph) ? x2t : d_pht
        array.clear(xv_l)
        array.clear(xv_t)
        d_ll := x2l
        d_ph := na
        d_phb := na
    if not na(p2o)
        if p2c > p2o and x2c < x2o
            array.push(xa_l, math.max(p2o, p2c))
            array.push(xa_t, x2t)
        if p2c < p2o and x2c > x2o
            array.push(xv_l, math.min(p2o, p2c))
            array.push(xv_t, x2t)
    if not ub
        if na(u_hh) or x2h > u_hh
            u_hh := x2h
            u_pl := na
            u_plb := na
        else
            if na(u_pl) or x2l < u_pl
                u_pl  := x2l
                u_plt := x2t
            u_plb := na(u_plb) ? x2L : math.min(u_plb, x2L)
    if not db
        if na(d_ll) or x2l < d_ll
            d_ll := x2l
            d_ph := na
            d_phb := na
        else
            if na(d_ph) or x2h > d_ph
                d_ph  := x2h
                d_pht := x2t
            d_phb := na(d_phb) ? x2H : math.max(d_phb, x2H)
    p2o := x2o
    p2c := x2c

// ── Drawing helpers ──────────────────────────────────────────────────────────
f_tcol(color c) =>
    color.new(c, 100 - (100 - color.t(c)) * tg_op / 100)
var array<label> tg_bl = array.new<label>()   // top-timeframe breakouts
var array<label> tg_pl = array.new<label>()   // pullback breaks
var array<label> tg_al_ = array.new<label>()  // story-timeframe pullbacks (back in alignment)
f_tag(array<label> arr, int t, float y, string txt, bool above, color c) =>
    if chart_ok and not na(t) and not na(y)
        array.push(arr, label.new(t, y, txt, xloc = xloc.bar_time, style = above ? label.style_label_down : label.style_label_up,
             color = f_tcol(c), textcolor = tg_tx, size = f_sz(tg_sz)))
        while array.size(arr) > tg_n
            label.delete(array.shift(arr))
var array<line>  br_l = array.new<line>()
var array<label> br_b = array.new<label>()
f_brk(int t1, float y, string txt, bool above, color c) =>
    if chart_ok and not na(t1) and not na(y)
        array.push(br_l, line.new(t1, y, time, y, xloc = xloc.bar_time, color = c, style = f_sty(br_sty), width = br_w))
        array.push(br_b, label.new(t1 + int((time - t1) / 2), y, txt, xloc = xloc.bar_time, style = above ? label.style_label_down : label.style_label_up,
             color = color.new(color.black, 100), textcolor = br_tx, size = f_sz(br_sz)))
        while array.size(br_l) > br_n
            line.delete(array.shift(br_l))
        while array.size(br_b) > br_n
            label.delete(array.shift(br_b))

'''

STORY = r'''
// ── The story ────────────────────────────────────────────────────────────────
// phase: 0 none · 1 top-timeframe breakout, story timeframe with it · 2 pullback break (the story
// timeframe against it) · 3 story-timeframe pullback (back in alignment, the story-timeframe range)
var int   sph  = 0
var int   D    = 0
var int   k1   = 0
var float XH   = na      // the top timeframe's external high / low (the Bias Pointer's)
var int   XHt  = na
var float XL   = na
var int   XLt  = na
// ONE pullback line (user rule, 2026-11-03, picture Documents/Pullback_Flow.png). Direction w:
// buys (w > 0): the line = the low that broke the last high. tk_ext = the leg's high, tk_fm = price really
// pulled back from it (a body closed beyond the far side of the body of the candle that made it), tk_dip =
// the lowest point since that high. A close above a REAL high = continuation: the line moves to tk_dip
// (the low that broke the high). A close below the line = the direction flips: the line = the highest
// point since the line (the high that broke the low). Sells mirror. Nothing else moves the line.
var int   w      = 0
var float tk_ln  = na
var int   tk_lt  = na
var float tk_ext = na
var int   tk_et  = na
var float tk_eo  = na      // the far side of the body of the candle that made tk_ext
var bool  tk_fm  = false
var float tk_dip = na
var int   tk_dt  = na
var float rg_hi  = na      // the story-timeframe range high (buys; sells: its low): the top of the leg
var int   rg_hit = na
var float rg_lo  = na      // the story-timeframe range low (buys; sells: its high)
var int   rg_lot = na
var bool  rg_lf  = false   // the range low is still forming (price closed below the one set at the pullback)
var bool  tk_bk  = false   // the pullback line is a broken high (sells: low): no low inside the move that broke it
var float tk_pv  = na      // the pullback line BEFORE the current one (the range low if the line breaks)
var int   tk_pvt = na
string up = D > 0 ? "up" : "down"
string dn = D > 0 ? "down" : "up"
string HI = D > 0 ? "high" : "low"
string LO = D > 0 ? "low" : "high"
string DW = D > 0 ? "bullish" : "bearish"
string AW = D > 0 ? "bearish" : "bullish"

// the rule run over the story-timeframe candles from time t0 in direction w_ (continuations only):
// [line, line time, leg extreme, its time, its body's far side, real pullback, dip, dip time]
// inside the move from t0 on: the last low that broke a high (sells: high that broke a low), and its time
f_inner(int t0, int w_) =>
    float ln = na
    int   lt = na
    float ex = na
    float eo = na
    bool  fm = false
    float dp = na
    int   dt = na
    int   n = array.size(q2t)
    if n > 0 and not na(t0)
        int k = n - 1
        while k > 0 and array.get(q2t, k - 1) >= t0
            k -= 1
        for j = k to n - 1
            float ce = w_ > 0 ? array.get(q2h, j) : array.get(q2l, j)
            float co = w_ > 0 ? array.get(q2l, j) : array.get(q2h, j)
            float cc = array.get(q2c, j)
            int   tj = array.get(q2t, j)
            if na(ex)
                ex := ce
                eo := co
                ln := co
                lt := tj
            else if fm and f_gt(cc, ex, w_)
                if na(dp) or f_gt(dp, co, w_)
                    dp := co
                    dt := tj
                ln := dp
                lt := dt
                ex := ce
                eo := co
                fm := false
                dp := na
                dt := na
            else if f_gt(ce, ex, w_)
                ex := ce
                eo := co
                fm := false
                dp := na
                dt := na
            else
                if f_gt(eo, cc, w_)
                    fm := true
                if na(dp) or f_gt(dp, co, w_)
                    dp := co
                    dt := tj
    [ln, lt]

f_seed(int t0, int w_) =>
    float ln = na
    int   lt = na
    float ex = na
    int   et = na
    float eo = na
    bool  fm = false
    float dp = na
    int   dt = na
    float pv = na
    int   pvt = na
    int   n = array.size(q2t)
    if n > 0 and not na(t0)
        int k = n - 1
        while k > 0 and array.get(q2t, k - 1) >= t0
            k -= 1
        for j = k to n - 1
            float ce = w_ > 0 ? array.get(q2h, j) : array.get(q2l, j)
            float co = w_ > 0 ? array.get(q2l, j) : array.get(q2h, j)
            float cc = array.get(q2c, j)
            int   tj = array.get(q2t, j)
            if na(ex)
                ex := ce
                et := tj
                eo := co
                ln := co
                lt := tj
            else if fm and f_gt(cc, ex, w_)
                if na(dp) or f_gt(dp, co, w_)
                    dp := co
                    dt := tj
                // the range low waiting = the low the breaking move came from; the pullback line = the last
                // low inside that move that broke a high, or (none) the broken high itself
                [il, ilt] = f_inner(dt, w_)
                pv  := dp
                pvt := dt
                bool inner = not na(ilt) and ilt > dt
                ln := inner ? il : ex
                lt := inner ? ilt : et
                ex := ce
                et := tj
                eo := co
                fm := false
                dp := na
                dt := na
            else if f_gt(ce, ex, w_)
                ex := ce
                et := tj
                eo := co
                fm := false
                dp := na
                dt := na
            else
                if f_gt(eo, cc, w_)
                    fm := true
                if na(dp) or f_gt(dp, co, w_)
                    dp := co
                    dt := tj
    [ln, lt, ex, et, eo, fm, dp, dt, pv, pvt]

// a new story in direction d
int   ns_d   = 0
float ns_lo  = na
int   ns_lot = na
float ns_hi  = na
int   ns_hit = na
float ns_lvl = na
bool  t1_ev  = false
bool  a_new  = not na(a_bcnt) and a_bcnt != k1
bool  first_ = k1 == 0
if a_new
    k1 := a_bcnt
// 1. the top timeframe's external high / low are ALWAYS the Bias Pointer's (its most recent structure).
//    Every breakout of it starts the story again, in its direction.
if a_new and not first_ and AD != 0
    ns_d   := AD
    ns_lvl := a_blvl
    ns_lo  := a_clo
    ns_lot := a_clot
    ns_hi  := a_chi
    ns_hit := a_chit
if ns_d != 0
    t1_ev := true
    D   := ns_d
    up  := D > 0 ? "up" : "down"
    dn  := D > 0 ? "down" : "up"
    HI  := D > 0 ? "high" : "low"
    LO  := D > 0 ? "low" : "high"
    DW  := D > 0 ? "bullish" : "bearish"
    AW  := D > 0 ? "bearish" : "bullish"
    sph := 1
    XL  := ns_lo
    XLt := ns_lot
    XH  := ns_hi
    XHt := ns_hit
    rg_hi := na
    rg_lo := na
    // the rule run over this leg (from the external low's time for buys, the high's for sells)
    [s_ln, s_lt, s_ex, s_et, s_eo, s_fm, s_dp, s_dt, s_pv, s_pvt] = f_seed(D > 0 ? XLt : XHt, D)
    tk_pv  := s_pv
    tk_pvt := s_pvt
    tk_bk  := false
    rg_lf  := false
    w      := D
    tk_ln  := s_ln
    tk_lt  := s_lt
    tk_ext := s_ex
    tk_et  := s_et
    tk_eo  := s_eo
    tk_fm  := s_fm
    tk_dip := s_dp
    tk_dt  := s_dt
    f_tag(tg_bl, x1t, D > 0 ? x1h : x1l, N1 + " " + DW + " breakout", D > 0, tg_boc)
    f_story(time, D > 0 ? high : low, D > 0, N1 + " " + DW + " breakout (" + (t1_wick ? "wick" : "body close") + " beyond " + str.tostring(ns_lvl, format.mintick) + ").\nPullback line: the " + N2 + " " + LO + " that broke the last " + HI + "; it moves only when that " + HI + " breaks.\nAn " + N2 + " close beyond it = the " + N1 + " pullback.")

// the external high / low follow the Bias Pointer's every candle (a side forms until it is fixed)
if D != 0 and not na(a_chi) and not na(a_clo)
    XH  := a_chi
    XHt := a_chit
    XL  := a_clo
    XLt := a_clot

// 2. the story timeframe, candle by candle
if D != 0 and x2_new and not t1_ev and sph >= 1
    float ce = w > 0 ? x2H : x2L
    float co = w > 0 ? x2L : x2H
    string WW = w > 0 ? "bullish" : "bearish"
    if not na(tk_ext) and tk_fm and f_gt(x2c, tk_ext, w)
        // a REAL high broken: continuation; the line moves to the low that broke it
        if (w == D ? br_with : br_agst)
            f_brk(tk_et, tk_ext, N2 + " " + WW + " cont", w > 0, w == D ? br_wcol : br_acol)
        if na(tk_dip) or f_gt(tk_dip, co, w)
            tk_dip := co
            tk_dt  := x2t
        // the range low waiting = the low the breaking move came from; the pullback line = the last low
        // inside that move that broke a high, or (none: a straight run) the broken high itself
        [i_ln, i_lt] = f_inner(tk_dt, w)
        bool inner_ = not na(i_lt) and i_lt > tk_dt
        tk_pv  := tk_dip
        tk_pvt := tk_dt
        tk_ln  := inner_ ? i_ln : tk_ext
        tk_lt  := inner_ ? i_lt : tk_et
        tk_bk  := not inner_
        tk_ext := ce
        tk_et  := x2t
        tk_eo  := co
        tk_fm  := false
        tk_dip := na
        tk_dt  := na
    else if na(tk_ext) or f_gt(ce, tk_ext, w)
        // a new high without a real pullback: the same leg goes on
        tk_ext := ce
        tk_et  := x2t
        tk_eo  := co
        tk_fm  := false
        tk_dip := na
        tk_dt  := na
    else
        if f_gt(tk_eo, x2c, w)
            tk_fm := true
        if na(tk_dip) or f_gt(tk_dip, co, w)
            tk_dip := co
            tk_dt  := x2t
    if not na(tk_ln) and f_gt(tk_ln, x2c, w)
        // a close beyond the line: the direction flips; the line = the high that broke the low
        [f0, f0t] = f_ext2(tk_lt, w > 0)
        float old_ln = tk_ln
        int   old_lt = tk_lt
        float old_pv = tk_pv
        int   old_pvt = tk_pvt
        int   ph0 = sph
        tk_pv  := na
        tk_pvt := na
        tk_bk  := false
        w      := -w
        tk_ln  := f0
        tk_lt  := f0t
        tk_ext := w > 0 ? x2H : x2L
        tk_et  := x2t
        tk_eo  := w > 0 ? x2L : x2H
        tk_fm  := false
        tk_dip := na
        tk_dt  := na
        if w != D
            // the story timeframe turns against the top timeframe
            bool rl_brk = ph0 == 3 and not na(rg_lo) and f_gt(rg_lo, x2c, D)
            sph := 2
            if ph0 == 1
                rg_lo  := na(old_pv) ? (D > 0 ? XL : XH) : old_pv
                rg_lot := na(old_pv) ? (D > 0 ? XLt : XHt) : old_pvt
                rg_lf  := false
                f_brk(old_lt, old_ln, "Pullback break", D < 0, br_acol)
                f_tag(tg_pl, time, D > 0 ? low : high, "Pullback break · " + N1 + " pullback confirmed", D < 0, tg_pbc)
            else if rl_brk
                f_brk(rg_lot, rg_lo, N2 + " range " + LO + " broken", D < 0, br_acol)
                rg_lf  := true
                rg_lo  := tk_ext
                rg_lot := tk_et
            else
                f_brk(old_lt, old_ln, "Pullback break (inside the " + N2 + " range)", D < 0, br_acol)
            if ph0 == 1 or rl_brk or na(rg_hi)
                // the range high = the top of the leg: the high that broke the low (inside the top-timeframe range)
                rg_hi  := tk_ln
                rg_hit := tk_lt
                if f_gt(rg_hi, D > 0 ? XH : XL, D)
                    rg_hi  := D > 0 ? XH : XL
                    rg_hit := D > 0 ? XHt : XLt
            f_story(time, D > 0 ? low : high, D < 0, (ph0 == 1 ? "Pullback break: the " + N1 + " pullback is confirmed. " + N1 + " range " + str.tostring(XL, format.mintick) + " – " + str.tostring(XH, format.mintick) : rl_brk ? "The " + N2 + " range " + LO + " " + str.tostring(rg_lo, format.mintick) + " is broken: " + N2 + " is " + AW + " again" : "Pullback break inside the " + N2 + " range: " + N2 + " is " + AW) + ".\n" + N2 + " pullback line: the " + HI + " that broke the " + LO + " " + str.tostring(tk_ln, format.mintick) + "; " + N2 + " range " + HI + " " + str.tostring(rg_hi, format.mintick) + ".")
        else if not na(rg_hi) and f_gt(x2c, rg_hi, D)
            // straight through the range high: the top timeframe continues
            sph   := 1
            f_brk(rg_hit, rg_hi, N2 + " range " + HI + " broken · " + N1 + " continues", D > 0, br_wcol)
            f_story(time, D > 0 ? high : low, D > 0, "The " + N2 + " range " + HI + " " + str.tostring(rg_hi, format.mintick) + " is broken: the " + N1 + " " + DW + " trend continues.\nPullback line: the " + LO + " that broke the " + HI + " " + str.tostring(tk_ln, format.mintick) + ".")
            rg_hi := na
            rg_lo := na
        else
            // the story-timeframe pullback: back in alignment, the story-timeframe range
            sph    := 3
            [b0, b0t] = f_ext2(rg_hit, D < 0)
            rg_lo  := nz(b0, tk_ln)
            rg_lot := na(b0) ? tk_lt : b0t
            rg_lf  := false
            f_brk(old_lt, old_ln, N2 + " pullback", D > 0, br_wcol)
            f_tag(tg_al_, time, D > 0 ? high : low, N2 + " pullback · back in alignment with " + N1, D > 0, tg_alc)
            f_story(time, D > 0 ? high : low, D > 0, N2 + " pullback: back in alignment with the " + N1 + ".\n" + N2 + " range: " + LO + " " + str.tostring(rg_lo, format.mintick) + " · " + HI + " " + str.tostring(rg_hi, format.mintick) + ". The pullback line starts at its " + LO + ".")
    else if sph == 3 and not na(rg_hi) and f_gt(x2c, rg_hi, D)
        // the range high broken: the top timeframe continues (the line has already followed the rule)
        sph := 1
        f_brk(rg_hit, rg_hi, N2 + " range " + HI + " broken · " + N1 + " continues", D > 0, br_wcol)
        f_story(time, D > 0 ? high : low, D > 0, "The " + N2 + " range " + HI + " " + str.tostring(rg_hi, format.mintick) + " is broken: the " + N1 + " " + DW + " trend continues.")
        rg_hi := na
        rg_lo := na

    // while the story timeframe is against the top timeframe: a close beyond the range low makes it form again
    // (it follows the leg's extreme until the story-timeframe pullback fixes it at the bottom)
    if sph == 2 and not na(rg_lo)
        if not rg_lf and f_gt(rg_lo, x2c, D)
            rg_lf := true
        if rg_lf and not na(tk_ext) and f_gt(rg_lo, tk_ext, D)
            rg_lo  := tk_ext
            rg_lot := tk_et

// ── The lines at the last candle ─────────────────────────────────────────────
var array<line>  cl = array.new<line>()
var array<label> cb = array.new<label>()
var array<box>   cx = array.new<box>()
f_lvl(int t, float y, string txt, color c, string st, int wd) =>
    if not na(t) and not na(y)
        array.push(cl, line.new(t, y, time, y, xloc = xloc.bar_time, extend = extend.right, color = c, style = f_sty(st), width = wd))
        array.push(cb, label.new(bar_index + 3, y, txt + (lv_px ? "  " + str.tostring(y, format.mintick) : ""), style = label.style_label_left,
             color = color.new(color.black, 100), textcolor = lv_tx, size = f_sz(lv_sz)))
f_tpos(string p) =>
    p == "Top right" ? position.top_right : p == "Bottom right" ? position.bottom_right : p == "Top left" ? position.top_left : p == "Middle right" ? position.middle_right : p == "Middle left" ? position.middle_left : position.bottom_left
var table sk = table.new(f_tpos(sk_pos), 2, 11, bgcolor = sk_bg, border_width = 1, border_color = color.new(color.gray, 75))
var table tb = table.new(f_tpos(tb_pos), 2, 20, bgcolor = tb_bg, border_width = 1, border_color = color.new(color.gray, 75))
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
    if not chart_ok and AD != 0 and x_on and not na(a_chi) and not na(a_clo)
        // on the top timeframe's own chart: its external high / low (the story needs the story timeframe)
        string ew = a_cdir == "bull" ? "bullish" : "bearish"
        f_lvl(a_chit, a_chi, N1 + " " + ew + " external high", x_col, x_sty, x_w)
        f_lvl(a_clot, a_clo, N1 + " " + ew + " external low", x_col, x_sty, x_w)
    if chart_ok and D != 0 and sph >= 1
        if x_on
            f_lvl(XHt, XH, N1 + " " + DW + " external high" + (D > 0 and not a_chif ? " (still forming)" : "") + (sph >= 2 ? " · " + N1 + " range high" + (D > 0 ? " (target)" : "") : ""), x_col, x_sty, x_w)
            f_lvl(XLt, XL, N1 + " " + DW + " external low" + (D < 0 and not a_clof ? " (still forming)" : "") + (sph >= 2 ? " · " + N1 + " range low" + (D < 0 ? " (target)" : "") : ""), x_col, x_sty, x_w)
        if sph >= 2 and not na(XH) and not na(XL)
            float req = (XH + XL) / 2
            int   r0  = math.min(XHt, XLt)
            if eq_on
                f_lvl(r0, req, N1 + " range 0.5 · " + (D > 0 ? "discount below" : "premium above"), eq_col, eq_sty, eq_w)
            if sh_on
                array.push(cx, box.new(r0, req, time, XL, xloc = xloc.bar_time, extend = extend.right, border_color = color.new(color.black, 100), bgcolor = color.new(sh_bull, 100 - sh_op)))
                array.push(cx, box.new(r0, XH, time, req, xloc = xloc.bar_time, extend = extend.right, border_color = color.new(color.black, 100), bgcolor = color.new(sh_bear, 100 - sh_op)))
        if pl_on and not na(tk_ln)
            string lw = w > 0 ? "low" : "high"
            string hw = w > 0 ? "high" : "low"
            f_lvl(tk_lt, tk_ln, (sph == 2 ? N2 + " pullback line" : "pullback line") + ": " + (tk_bk ? "the broken " + N2 + " " + hw + " (no " + lw + " inside the move that broke it)" : "the " + N2 + " " + lw + " that broke the last " + hw) + (sph == 1 ? " (an " + N2 + " close beyond it = the " + N1 + " pullback)" : sph == 2 ? " (an " + N2 + " close beyond it = " + N2 + " pullback)" : " (inside the " + N2 + " range)"), pl_col, pl_sty, pl_w)
        if sph == 2 and rh_on and rx_on and not na(tk_ext)
            f_lvl(tk_et, tk_ext, N2 + " " + LO + " (forming)", rh_col, rx_sty, rh_w)
        if sph >= 2 and rh_on and not na(rg_hi)
            f_lvl(rg_hit, rg_hi, N2 + " range " + HI + (sph == 3 ? " (a close beyond it: the " + N1 + " continues)" : ""), rh_col, rh_sty, rh_w)
        if sph == 1 and rh_on and not na(tk_pv)
            f_lvl(tk_pvt, tk_pv, N2 + " range " + LO + " if the pullback line breaks (the " + LO + " the breaking move came from)", rh_col, rx_sty, rh_w)
        if sph >= 2 and rh_on and not na(rg_lo)
            f_lvl(rg_lot, rg_lo, N2 + " range " + LO + (rg_lf ? " (forming)" : sph == 3 ? " (a close beyond it: " + N2 + " " + AW + " again)" : ""), rh_col, rg_lf ? rx_sty : rh_sty, rh_w)
    // the story table and the status table (one table per corner: in the same corner the story goes under the status)
    bool  sk_same = sk_pos == tb_pos
    table st_tb   = sk_same ? tb : sk
    int   so      = sk_same and tb_on ? 8 : 0
    table.clear(sk, 0, 0, 1, 10)
    table.clear(tb, 0, 0, 1, 19)
    if sk_on and chart_ok
        table.cell(st_tb, 0, so, "STORY", text_color = sk_tx, text_size = size.small, text_halign = text.align_left, bgcolor = sk_bg)
        table.cell(st_tb, 1, so, PLAN, text_color = color.new(sk_tx, 40), text_size = size.small, text_halign = text.align_left, bgcolor = sk_bg)
        int nh = array.size(st_h)
        if nh == 0
            table.cell(st_tb, 1, so + 1, "Waiting for a " + N1 + " breakout", text_color = sk_tx, text_size = size.small, text_halign = text.align_left, bgcolor = sk_bg)
        else
            for j = 0 to math.min(sk_n, nh) - 1
                int ix = nh - 1 - j
                table.cell(st_tb, 0, so + j + 1, str.format_time(array.get(st_ht, ix), "dd MMM HH:mm"), text_color = color.new(sk_tx, 40), text_size = size.tiny, text_halign = text.align_left, bgcolor = sk_bg)
                table.cell(st_tb, 1, so + j + 1, array.get(st_h, ix), text_color = j == 0 ? sk_tx : color.new(sk_tx, 35), text_size = size.small, text_halign = text.align_left, bgcolor = sk_bg)
    if tb_on
        if not chart_ok
            f_row(0, PLAN, "On this chart: the " + N1 + " external high / low. Put the chart on " + N2 + " or lower for the story")
        else
            string phs = sph == 0 ? "waiting for a " + N1 + " breakout" : sph == 1 ? N1 + " " + DW + " breakout: " + N2 + " with it; a close beyond the pullback line = the " + N1 + " pullback" : sph == 2 ? N1 + " pullback: " + N2 + " " + AW + "; a close beyond its last " + HI + " = " + N2 + " pullback" : "inside the " + N2 + " range: beyond its " + HI + " the " + N1 + " " + DW + " story continues; a close beyond its " + LO + " = " + N2 + " " + AW + " cont"
            f_row(0, "Plan", PLAN + " · breaks: " + N1 + " " + (t1_wick ? "wick" : "body close") + ", " + N2 + " " + (t2_wick ? "wick" : "body close"))
            f_row(1, N1, D > 0 ? "bullish" : D < 0 ? "bearish" : "—")
            f_row(2, "Story", phs)
            if sph >= 1 and not na(XH) and not na(XL)
                f_row(3, N1 + " range", str.tostring(XL, format.mintick) + " – " + str.tostring(XH, format.mintick))
            if sph >= 1 and not na(tk_ln)
                f_row(4, sph == 2 ? N2 + " pullback line" : "Pullback line", str.tostring(tk_ln, format.mintick))
            if sph >= 2 and not na(rg_hi)
                f_row(5, N2 + " range", (not na(rg_lo) ? str.tostring(rg_lo, format.mintick) + (rg_lf ? " (forming)" : "") + " – " : HI + " ") + str.tostring(rg_hi, format.mintick))
'''

body = HEAD + ENGINE + BODY + NOTES + STORY
open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
print(OUT, body.count('\n'), 'lines')
