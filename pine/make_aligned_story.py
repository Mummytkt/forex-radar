"""Builds MummyTKT_AlignedStory.pine — the Bias Pointer + Pullback Story merged (2026-10-31),
drawn first in Documents/Aligned_Story_Buys.png / _Sells.png (pine/aligned_story_picture.py).

  1. T1 (top) external breakout (the Bias Pointer engine).
  2. T2 (story) continuations: a line tracks the last T2 low and moves up after every T2 BOS.
  3. A T2 close through that low = the T1 pullback. The last high is the T1 range high, the
     T1 low that caused the breakout the range low; 0.5 splits premium / discount.
  4. T1 levels in the discount: boxes (FVG, demand) and lines (V-shape, OC, Breaker). Only a
     T1 close through one removes it.
  5. Price reaches one, then a T2 External breakout up = "T1 + T2 aligned". Target: range high.
     T2 range = range high <-> the T2 low that caused that breakout; a T2 close below it first
     = T2 still bearish inside the bullish T1 (the pullback goes on).
  6. T2 levels in the T2 range (an T2 close through one removes it). A T3 sweep of a T2 level
     (wick through, close back) and a break of the last T3 high = "T3 entry confirmed".
Plans: W -> D -> H4 · D -> H4 -> M15 · H4 -> M15 -> M5 · Custom.

The external engine and the story-note helpers are copied from MummyTKT_PullbackStory.pine
(run make_pullback_story.py first if the engine changes).
"""
SRC = 'C:/Users/u/forex-radar/pine/MummyTKT_PullbackStory.pine'
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_AlignedStory.pine'

src = open(SRC, encoding='utf-8').read().split('\n')


def cut(start, stop):
    a = next(i for i, l in enumerate(src) if l.startswith(start))
    b = next(i for i, l in enumerate(src) if i > a and l.startswith(stop))
    return '\n'.join(src[a:b]).rstrip() + '\n'


ENGINE = cut('f_sz(string s) =>', '// ── Top timeframe: the reaction levels')
NOTES = cut('var array<label> st_l', '// POIs: demand (buys)')

HEAD = r'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — Aligned Story (Bias Pointer + Pullback Story · display only, no alerts) · 2026-10-31
//
// One story on three timeframes (pick the plan in the settings: W → D → H4, D → H4 → M15,
// H4 → M15 → M5 or your own). Buys; sells are the mirror.
//   1. Top timeframe external breakout (the Bias Pointer's external high / low).
//   2. Story-timeframe continuations: a line tracks the last story-timeframe low and moves up
//      after every story-timeframe BOS up (pullback readiness).
//   3. A story-timeframe close below that low = the top timeframe's pullback is confirmed.
//      The last high is the range high (the target), the low that caused the breakout the
//      range low; the 0.5 line splits premium and discount.
//   4. The top-timeframe levels in the discount: boxes for FVGs and demand, lines for
//      V-shapes, OCs and the Breaker. A level dies ONLY on a close of its own timeframe
//      through it (top-timeframe levels: a top-timeframe close; an FVG stays while price is
//      inside it).
//   5. Price reaches one of them, then a story-timeframe External breakout up (its level
//      formed before price reached the level) = "aligned". Target: the range high.
//      Story-timeframe range = the range high and the story-timeframe low that caused that
//      breakout. A close below that low first = the story timeframe is still bearish inside
//      the bullish top timeframe: the pullback goes on.
//   6. The story-timeframe levels inside its range (a story-timeframe close through one
//      removes it). Entry: an entry-timeframe candle sweeps one of them (wick through the
//      level, close back) and price then closes above the last entry-timeframe high =
//      "entry confirmed".
// ─────────────────────────────────────────────────────────────────────────────

indicator("MummyTKT — Aligned Story", overlay = true, behind_chart = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 300, max_bars_back = 5000)

const string G_PL = "1 · Plan and breaks"
const string G_ST = "2 · Story notes and tags"
const string G_RG = "3 · Ranges and lines"
const string G_L1 = "4 · Top-timeframe levels (in the discount / premium)"
const string G_L2 = "5 · Story-timeframe levels (in its range)"
const string G_EN = "6 · Entries"
const string G_TB = "7 · Status table"

string plan     = input.string("D → H4 → M15", "Plan (top → story → entry)", options = ["W → D → H4", "D → H4 → M15", "H4 → M15 → M5", "Custom"], group = G_PL,
     tooltip = "Weekly story: W → D → H4. The top timeframe's breakout starts the story, the story timeframe tells it, the entry timeframe confirms. Put the chart on the story timeframe or lower (the entry timeframe for the entries).")
string cu_t1    = input.timeframe("D", "Custom: top", group = G_PL, inline = "cu")
string cu_t2    = input.timeframe("240", "story", group = G_PL, inline = "cu")
string cu_t3    = input.timeframe("15", "entry", group = G_PL, inline = "cu")
bool   brk_wick = input.string("Wick", "Top-timeframe breakout confirmed by", options = ["Wick", "Body close"], group = G_PL,
     tooltip = "Wick (default, as the Bias Pointer): a wick beyond the external level breaks it. Body close: the candle must close beyond it.") == "Wick"
bool   bos_wick = input.string("Body close", "Story-timeframe BOS confirmed by", options = ["Body close", "Wick"], group = G_PL,
     tooltip = "Body close (default): a story-timeframe breakout, the break of the tracked low and of its range low need a candle body to close beyond the level.") == "Wick"
bool   d_body   = input.string("Wick", "Highs / lows / A / V-shapes from", options = ["Wick", "Body"], group = G_PL,
     tooltip = "Wick (default): external highs / lows, A-shapes and V-shapes on the candle wicks. Body: on the bodies.") == "Body"
bool   show_int = input.bool(true, "Show breaks that don't move the story (Internal, or before a level is reached)", group = G_PL)

string st_mode  = input.string("Dots only (hover)", "Story on the chart", options = ["Dots only (hover)", "Latest note + dots (hover)", "Latest note only", "Last N notes", "Off"], group = G_ST)
int    st_n     = input.int(8, "N (notes or dots kept)", minval = 1, maxval = 40, group = G_ST)
color  st_bg    = input.color(#0E3B43, "Note background", group = G_ST, inline = "sb")
int    st_op    = input.int(90, "opacity %", minval = 0, maxval = 100, group = G_ST, inline = "sb")
color  st_tx    = input.color(color.white, "Note text", group = G_ST, inline = "st")
string st_sz    = input.string("Small", "size", options = ["Tiny", "Small", "Normal"], group = G_ST, inline = "st")
color  st_dot   = input.color(#26C6DA, "Note dots", group = G_ST)
bool   sk_on    = input.bool(true, "Story table (separate from the status table)", group = G_ST, inline = "sk")
string sk_pos   = input.string("Bottom right", "", options = ["Top right", "Bottom right", "Top left", "Bottom left", "Middle right", "Middle left"], group = G_ST, inline = "sk")
int    sk_n     = input.int(3, "Notes in the story table (newest first)", minval = 1, maxval = 10, group = G_ST)
color  sk_bg    = input.color(color.new(#0E3B43, 10), "Story table background", group = G_ST, inline = "sc")
color  sk_tx    = input.color(color.white, "text", group = G_ST, inline = "sc")
bool   sl_on    = input.bool(true, "Break lines (BOS from the level to the candle that broke it)", group = G_ST)
color  sl_col   = input.color(color.new(color.white, 20), "Break line colour", group = G_ST, inline = "sl")
color  sl_tx    = input.color(color.white, "text", group = G_ST, inline = "sl")
bool   tg_on    = input.bool(true, "Tags (aligned, entry confirmed)", group = G_ST, inline = "tg")
string tg_sz    = input.string("Small", "size", options = ["Tiny", "Small", "Normal"], group = G_ST, inline = "tg")
color  tg_alb   = input.color(#00C853, "Aligned · buys", group = G_ST, inline = "ta")
color  tg_als   = input.color(#FF1744, "sells", group = G_ST, inline = "ta")
color  tg_en    = input.color(#7C4DFF, "Entry confirmed", group = G_ST, inline = "te")
color  tg_tx    = input.color(color.white, "tag text", group = G_ST, inline = "te")
int    tg_op    = input.int(100, "Tag opacity %", minval = 0, maxval = 100, group = G_ST)

bool   t1x_on   = input.bool(true, "Top-timeframe external high / low (until the pullback)", group = G_RG, inline = "tx")
color  t1x_col  = input.color(#E0E0E0, "", group = G_RG, inline = "tx")
int    t1x_w    = input.int(2, "width", minval = 1, maxval = 4, group = G_RG, inline = "tx")
bool   tl_on    = input.bool(true, "Last story-timeframe low / high (pullback readiness)", group = G_RG, inline = "tl")
color  tl_col   = input.color(#29B6F6, "", group = G_RG, inline = "tl")
int    tl_w     = input.int(2, "width", minval = 1, maxval = 4, group = G_RG, inline = "tl")
bool   rg_on    = input.bool(true, "Top-timeframe range: high (target), low, 0.5", group = G_RG, inline = "rg")
color  rg_col   = input.color(#E0E0E0, "", group = G_RG, inline = "rg")
color  eq_col   = input.color(#9E9E9E, "0.5", group = G_RG, inline = "rg")
int    rg_w     = input.int(2, "width", minval = 1, maxval = 4, group = G_RG, inline = "rg")
bool   sh_on    = input.bool(true, "Shade discount / premium", group = G_RG, inline = "sh")
int    sh_op    = input.int(5, "opacity %", minval = 0, maxval = 100, group = G_RG, inline = "sh")
bool   hl_on    = input.bool(true, "Story-timeframe range low / high (after aligned)", group = G_RG, inline = "hl")
color  hl_col   = input.color(#FFA726, "", group = G_RG, inline = "hl")
color  lv_tx    = input.color(#E0E0E0, "Level label text", group = G_RG, inline = "lt")
string lv_sz    = input.string("Small", "size", options = ["Tiny", "Small", "Normal"], group = G_RG, inline = "lt")

bool   l1_on    = input.bool(true, "Show", group = G_L1, inline = "l1")
color  l1_bull  = input.color(#26A69A, "buys", group = G_L1, inline = "l1")
color  l1_bear  = input.color(#EF5350, "sells", group = G_L1, inline = "l1")
int    l1_op    = input.int(18, "Box opacity %", minval = 0, maxval = 100, group = G_L1, inline = "l1b")
int    l1_w     = input.int(2, "line width", minval = 1, maxval = 4, group = G_L1, inline = "l1b")
int    l1_max   = input.int(12, "Most shown", minval = 1, maxval = 40, group = G_L1)
float  mg_pct   = input.float(0.03, "Merge levels that overlap or are closer than (% of price)", minval = 0, maxval = 2, step = 0.01, group = G_L1,
     tooltip = "Overlapping levels on the same side are shown as one (e.g. Daily bullish FVG + demand). Each part still dies on its own close: if a candle closes through the demand but not the FVG, it shows as the FVG only.")
bool   k_fvg    = input.bool(true, "FVGs (box)", group = G_L1, inline = "k1")
bool   k_zone   = input.bool(true, "Demand / supply (box)", group = G_L1, inline = "k1")
bool   k_vs     = input.bool(true, "V / A-shapes (line)", group = G_L1, inline = "k2")
bool   k_oc     = input.bool(true, "OCs (line)", group = G_L1, inline = "k2")
bool   k_brk    = input.bool(true, "Breaker (line)", group = G_L1, inline = "k2",
     tooltip = "These kinds are used on both timeframes. FVG: dies only when a candle of its own timeframe closes beyond its far side; it stays while price is inside it. Demand / supply: the candle with the lowest low (highest high) before each breakout, from its wick to its body.")

bool   l2_on    = input.bool(true, "Show", group = G_L2, inline = "l2")
color  l2_bull  = input.color(#80CBC4, "buys", group = G_L2, inline = "l2")
color  l2_bear  = input.color(#EF9A9A, "sells", group = G_L2, inline = "l2")
int    l2_op    = input.int(25, "Box opacity %", minval = 0, maxval = 100, group = G_L2, inline = "l2b")
int    l2_w     = input.int(1, "line width", minval = 1, maxval = 4, group = G_L2, inline = "l2b")
int    l2_max   = input.int(10, "Most shown", minval = 1, maxval = 40, group = G_L2)

bool   en_on    = input.bool(true, "Entry: sweep and break at the story-timeframe levels", group = G_EN)
int    fr_n     = input.int(2, "Entry-timeframe fractal: candles each side", minval = 1, maxval = 5, group = G_EN,
     tooltip = "The break level is the last entry-timeframe fractal high (sells: low) before the sweep.")
int    en_win   = input.int(20, "Candles from the sweep to the break", minval = 1, maxval = 100, group = G_EN)

bool   tb_on    = input.bool(true, "Status table", group = G_TB, inline = "tb")
string tb_pos   = input.string("Top right", "", options = ["Top right", "Bottom right", "Top left", "Bottom left"], group = G_TB, inline = "tb")
color  tb_bg    = input.color(color.new(#0F1120, 10), "Background", group = G_TB, inline = "tc")
color  tb_tx    = input.color(color.white, "Text", group = G_TB, inline = "tc")

// The plan's three timeframes and their names
string T1 = plan == "W → D → H4" ? "W" : plan == "D → H4 → M15" ? "D" : plan == "H4 → M15 → M5" ? "240" : cu_t1
string T2 = plan == "W → D → H4" ? "D" : plan == "D → H4 → M15" ? "240" : plan == "H4 → M15 → M5" ? "15" : cu_t2
string T3 = plan == "W → D → H4" ? "240" : plan == "D → H4 → M15" ? "15" : plan == "H4 → M15 → M5" ? "5" : cu_t3
f_tfn(string tf) =>
    int s = timeframe.in_seconds(tf)
    s >= 2419200 ? "Monthly" : s == 604800 ? "Weekly" : s == 86400 ? "Daily" : s % 3600 == 0 ? "H" + str.tostring(math.round(s / 3600)) : "M" + str.tostring(math.round(s / 60))
string N1 = f_tfn(T1)
string N2 = f_tfn(T2)
string N3 = f_tfn(T3)
string PLAN = N1 + " → " + N2 + " → " + N3

'''

BODY = r'''
// ── Candles of each timeframe (the last closed one) ──────────────────────────
f_cnd() =>
    [open[1], high[1], low[1], close[1], time[1]]

// entry timeframe: candle and the last fractal high / low
f_c3(simple int n) =>
    float ph_ = ta.pivothigh(high, n, n)
    float pl_ = ta.pivotlow(low, n, n)
    var float lfh = na
    var float lfl = na
    if not na(ph_)
        lfh := ph_
    if not na(pl_)
        lfl := pl_
    [open, high, low, close, time, lfh, lfl]
f_c3d(simple int n) =>
    [a1, a2, a3, a4, a5, a6, a7] = f_c3(n)
    [a1[1], a2[1], a3[1], a4[1], a5[1], a6[1], a7[1]]

[a_cdir, a_chi, a_clo, a_chif, a_clof, a_chit, a_clot, a_bcnt, a_bdir, a_blvl, a_bopp, a_da, a_dat, a_dv, a_dvt, a_bt] = request.security(syminfo.tickerid, T1, f_structure(d_body, brk_wick), lookahead = barmerge.lookahead_on)
[b_cdir, b_chi, b_clo, b_chif, b_clof, b_chit, b_clot, b_bcnt, b_bdir, b_blvl, b_bopp, b_da, b_dat, b_dv, b_dvt, b_bt] = request.security(syminfo.tickerid, T2, f_structure(d_body, bos_wick), lookahead = barmerge.lookahead_on)
[x1o, x1h, x1l, x1c, x1t] = request.security(syminfo.tickerid, T1, f_cnd(), lookahead = barmerge.lookahead_on)
[x2o, x2h, x2l, x2c, x2t] = request.security(syminfo.tickerid, T2, f_cnd(), lookahead = barmerge.lookahead_on)
[q3o, q3h, q3l, q3c, q3t, q3fh, q3fl] = request.security(syminfo.tickerid, T3, f_c3d(fr_n), lookahead = barmerge.lookahead_on)
[d3o, d3h, d3l, d3c, d3t, d3fh, d3fl] = f_c3(fr_n)
// on the entry timeframe itself, its own candles (no one-candle delay)
bool  e_own = timeframe.in_seconds() == timeframe.in_seconds(T3)
float e3h  = e_own ? d3h : q3h
float e3l  = e_own ? d3l : q3l
float e3c  = e_own ? d3c : q3c
int   e3t  = e_own ? d3t : q3t
float e3fh = e_own ? d3fh : q3fh
float e3fl = e_own ? d3fl : q3fl
bool  e_new  = not na(e3t) and e3t != nz(e3t[1]) and (not e_own or barstate.isconfirmed)
bool  x1_new = not na(x1t) and x1t != nz(x1t[1])
bool  x2_new = not na(x2t) and x2t != nz(x2t[1])
bool  chart_ok = timeframe.in_seconds() <= timeframe.in_seconds(T2)

int AD = a_bdir == "bullish" ? 1 : a_bdir == "bearish" ? -1 : 0      // the engine's latest break
var int D1 = 0                                                          // the story's direction
int D2 = b_bdir == "bullish" ? 1 : b_bdir == "bearish" ? -1 : 0
string up = D1 > 0 ? "up" : "down"
string dn = D1 > 0 ? "down" : "up"
string HI = D1 > 0 ? "high" : "low"
string LO = D1 > 0 ? "low" : "high"

// ── The levels of one timeframe ──────────────────────────────────────────────
// Buy side (support): V-shapes, bullish OCs, bullish FVGs, demand, the Breaker of a break up.
// Sell side: the mirror. A level dies ONLY when a candle of its own timeframe closes beyond it
// (an FVG: beyond its far side, so it stays while price is inside it).
type Lv
    int   kind      // 1 V / A-shape · 2 OC · 3 FVG · 4 demand / supply · 5 Breaker
    bool  bull
    float top
    float bot
    int   t
    bool  hit  = false
    bool  used = false

f_kname(int k, bool bull) =>
    k == 1 ? (bull ? "V-shape" : "A-shape") : k == 2 ? (bull ? "bullish OC" : "bearish OC") : k == 3 ? (bull ? "bullish FVG" : "bearish FVG") : k == 4 ? (bull ? "demand" : "supply") : "Breaker"
f_kon(int k) =>
    k == 1 ? k_vs : k == 2 ? k_oc : k == 3 ? k_fvg : k == 4 ? k_zone : k_brk
// the level overlaps the price band a – b
f_inz(Lv v, float a, float b) =>
    not na(a) and not na(b) and v.top >= math.min(a, b) and v.bot <= math.max(a, b)

f_add(array<Lv> bk, int k, bool bull, float p1, float p2, int t) =>
    if not na(p1) and not na(p2) and not na(t)
        array.push(bk, Lv.new(k, bull, math.max(p1, p2), math.min(p1, p2), t))
        while array.size(bk) > 200
            array.shift(bk)

// one closed candle of this timeframe: remove the levels it closed through, add the new ones
f_feed(array<Lv> bk, array<float> ho, array<float> hh, array<float> hl_, array<float> hc, array<int> ht, float o, float h, float l, float c, int t, bool bd) =>
    int k = array.size(bk) - 1
    while k >= 0
        Lv v = array.get(bk, k)
        if v.bull ? c < v.bot : c > v.top
            array.remove(bk, k)
        k -= 1
    array.push(ho, o)
    array.push(hh, h)
    array.push(hl_, l)
    array.push(hc, c)
    array.push(ht, t)
    while array.size(ho) > 3
        array.shift(ho)
        array.shift(hh)
        array.shift(hl_)
        array.shift(hc)
        array.shift(ht)
    int n = array.size(ho)
    if n >= 2
        float o1 = array.get(ho, n - 2)
        float h1 = array.get(hh, n - 2)
        float l1 = array.get(hl_, n - 2)
        float c1 = array.get(hc, n - 2)
        int   t1 = array.get(ht, n - 2)
        float b0h = bd ? math.max(o, c) : h
        float b0l = bd ? math.min(o, c) : l
        float b1h = bd ? math.max(o1, c1) : h1
        float b1l = bd ? math.min(o1, c1) : l1
        if c1 < o1 and c > o
            f_add(bk, 1, true, math.min(b0l, b1l), math.min(b0l, b1l), b0l <= b1l ? t : t1)
        if c1 > o1 and c < o
            f_add(bk, 1, false, math.max(b0h, b1h), math.max(b0h, b1h), b0h >= b1h ? t : t1)
        if c1 > o1 and c > o
            f_add(bk, 2, true, c1, c1, t1)
        if c1 < o1 and c < o
            f_add(bk, 2, false, c1, c1, t1)
    if n >= 3
        float h2 = array.get(hh, n - 3)
        float l2 = array.get(hl_, n - 3)
        int   t2 = array.get(ht, n - 3)
        if h2 < l
            f_add(bk, 3, true, l, h2, t2)
        if l2 > h
            f_add(bk, 3, false, l2, h, t2)

var array<Lv>    bk1 = array.new<Lv>()
var array<float> h1o = array.new<float>()
var array<float> h1h = array.new<float>()
var array<float> h1l = array.new<float>()
var array<float> h1c = array.new<float>()
var array<int>   h1t = array.new<int>()
var array<Lv>    bk2 = array.new<Lv>()
var array<float> h2o = array.new<float>()
var array<float> h2h = array.new<float>()
var array<float> h2l = array.new<float>()
var array<float> h2c = array.new<float>()
var array<int>   h2t = array.new<int>()
// the candle with the lowest low / highest high since the last break (demand / supply)
var float z1lo = na
var float z1lt = na
var int   z1t  = na
var float z1hi = na
var float z1hb = na
var int   z1ht = na
var float z2lo = na
var float z2lt = na
var int   z2t  = na
var float z2hi = na
var float z2hb = na
var int   z2ht = na

// ── Story notes, break lines, tags ───────────────────────────────────────────
'''

STORY = r'''
f_tag(string txt, bool above, color c) =>
    if chart_ok and tg_on
        label.new(bar_index, above ? high : low, txt, style = above ? label.style_label_down : label.style_label_up,
             color = color.new(c, 100 - tg_op), textcolor = tg_tx, size = f_sz(tg_sz))

var array<line> tl_seg = array.new<line>()
f_seg(int t0, float y) =>
    if chart_ok and tl_on and not na(t0) and not na(y)
        array.push(tl_seg, line.new(t0, y, time, y, xloc = xloc.bar_time, color = tl_col, width = tl_w))
        while array.size(tl_seg) > 40
            line.delete(array.shift(tl_seg))

// ── The story ────────────────────────────────────────────────────────────────
// phase: 0 none · 1 top-timeframe breakout, story-timeframe continuations · 2 the top
// timeframe's pullback (its range and levels) · 3 aligned (story-timeframe range, entries)
var int   sph    = 0
var int   k1     = 0
var int   k2     = 0
var float tl     = na      // the last story-timeframe low (buys) / high (sells)
var int   tl_t   = na
var float fl     = na      // the story's top-timeframe external low (buys) / high (sells)
var int   fl_t   = na
var float pb_x   = na      // the pullback's extreme on the top timeframe (causes the next breakout)
var int   pb_t   = na
var float xt     = na      // the extreme since the top-timeframe breakout (the range high / low)
var int   xt_t   = na
var float rh     = na      // top-timeframe range: high (target) · low · 0.5 (buys; sells mirror)
var int   rh_t   = na
var float rl     = na
var int   rl_t   = na
var float req    = na
var float hl     = na      // story-timeframe range low (buys) / high (sells), after aligned
var int   hl_t   = na
var int   rx_t   = na      // when price first reached a top-timeframe level in this pullback
var bool  tg_done = false
var float lb_lvl = na      // the last story-timeframe breakout: the same one again is skipped
var int   lb_dir = 0
var int   lb_t   = na
var bool  ea_on  = false   // an entry-timeframe sweep at a level, waiting for the break
var float ea_sw  = na
var float ea_br  = na
var float ea_lvl = na
var int   ea_n   = 0
var Lv    ea_lv  = na

// 1. feed each timeframe's levels with its closed candles
if x1_new
    f_feed(bk1, h1o, h1h, h1l, h1c, h1t, x1o, x1h, x1l, x1c, x1t, d_body)
    if na(z1lo) or x1l < z1lo
        z1lo := x1l
        z1lt := math.max(x1o, x1c)
        z1t  := x1t
    if na(z1hi) or x1h > z1hi
        z1hi := x1h
        z1hb := math.min(x1o, x1c)
        z1ht := x1t
if x2_new
    f_feed(bk2, h2o, h2h, h2l, h2c, h2t, x2o, x2h, x2l, x2c, x2t, d_body)
    if na(z2lo) or x2l < z2lo
        z2lo := x2l
        z2lt := math.max(x2o, x2c)
        z2t  := x2t
    if na(z2hi) or x2h > z2hi
        z2hi := x2h
        z2hb := math.min(x2o, x2c)
        z2ht := x2t

// 2. the engine's breaks feed the levels (Breaker, demand / supply)
bool a_new  = not na(a_bcnt) and a_bcnt != k1
bool first_ = k1 == 0
if a_new
    k1 := a_bcnt
    if AD > 0
        f_add(bk1, 5, true, a_blvl, a_blvl, a_bt)
        f_add(bk1, 4, true, z1lt, z1lo, z1t)
    else if AD < 0
        f_add(bk1, 5, false, a_blvl, a_blvl, a_bt)
        f_add(bk1, 4, false, z1hi, z1hb, z1ht)
    z1lo := na
    z1hi := na
// The story. It starts on a top-timeframe external breakout (the Bias Pointer engine) when none
// is running. While one runs, only ITS external levels move it: a break beyond its external low
// (buys) = the breakout the other way (a new story); beyond the range high after the pullback =
// a new breakout the same way. Structures that form inside the range don't change it.
if x1_new and sph == 1 and D1 != 0
    if D1 > 0 ? x1h > nz(xt, x1h - 1) : x1l < nz(xt, x1l + 1)
        xt   := D1 > 0 ? x1h : x1l
        xt_t := x1t
if x1_new and sph >= 2 and D1 != 0
    if na(pb_x) or (D1 > 0 ? x1l < pb_x : x1h > pb_x)
        pb_x := D1 > 0 ? x1l : x1h
        pb_t := x1t
int   s_dir = 0
float s_lvl = na
int   s_lvt = na
float s_lo  = na
int   s_lot = na
float s_hi  = na
int   s_hit = na
if sph == 0 and a_new and not first_ and AD != 0
    s_dir := AD
    s_lvl := a_blvl
    s_lvt := a_bt
    s_lo  := AD > 0 ? a_clo : x1l
    s_lot := AD > 0 ? a_clot : x1t
    s_hi  := AD > 0 ? x1h : a_chi
    s_hit := AD > 0 ? x1t : a_chit
else if sph >= 1 and D1 != 0 and x1_new and not na(fl) and (D1 > 0 ? (brk_wick ? x1l : x1c) < fl : (brk_wick ? x1h : x1c) > fl)
    float ox  = sph == 1 ? xt : rh
    int   oxt = sph == 1 ? xt_t : rh_t
    s_dir := -D1
    s_lvl := fl
    s_lvt := fl_t
    s_lo  := D1 > 0 ? x1l : ox
    s_lot := D1 > 0 ? x1t : oxt
    s_hi  := D1 > 0 ? ox : x1h
    s_hit := D1 > 0 ? oxt : x1t
else if sph >= 2 and D1 != 0 and x1_new and not na(rh) and (D1 > 0 ? (brk_wick ? x1h : x1c) > rh : (brk_wick ? x1l : x1c) < rh)
    float px  = nz(pb_x, rl)
    int   pxt = na(pb_x) ? rl_t : pb_t
    s_dir := D1
    s_lvl := rh
    s_lvt := rh_t
    s_lo  := D1 > 0 ? px : x1l
    s_lot := D1 > 0 ? pxt : x1t
    s_hi  := D1 > 0 ? x1h : px
    s_hit := D1 > 0 ? x1t : pxt
if s_dir != 0
    if sph >= 1
        f_add(bk1, 5, s_dir > 0, s_lvl, s_lvl, s_lvt)
    D1 := s_dir
    up := D1 > 0 ? "up" : "down"
    dn := D1 > 0 ? "down" : "up"
    HI := D1 > 0 ? "high" : "low"
    LO := D1 > 0 ? "low" : "high"
    sph  := 1
    fl   := D1 > 0 ? s_lo : s_hi
    fl_t := D1 > 0 ? s_lot : s_hit
    xt   := D1 > 0 ? s_hi : s_lo
    xt_t := D1 > 0 ? s_hit : s_lot
    tl   := D2 == D1 ? (D1 > 0 ? b_clo : b_chi) : na
    tl_t := D2 == D1 ? (D1 > 0 ? b_clot : b_chit) : na
    rh := na
    rl := na
    req := na
    hl := na
    rx_t := na
    pb_x := na
    tg_done := false
    ea_on := false
    f_story(time, D1 > 0 ? high : low, D1 > 0, N1 + " " + (D1 > 0 ? "bullish" : "bearish") + " external breakout (" + (brk_wick ? "wick" : "body close") + " beyond " + str.tostring(s_lvl, format.mintick) + ").\nEvery " + N2 + " breakout " + up + " now is a continuation. The " + N1 + " pullback is confirmed\nonce an " + N2 + " candle closes beyond the last " + N2 + " " + LO + " (pullback line).")

bool conf_now = false
if D1 != 0 and x2_new
    // the extreme since the breakout: the range high once the pullback is confirmed
    if sph == 1
        if D1 > 0 ? x2h > nz(xt, x2h - 1) : x2l < nz(xt, x2l + 1)
            xt   := D1 > 0 ? x2h : x2l
            xt_t := x2t
    // 3. a story-timeframe close beyond the last low = the top timeframe's pullback
    // (on the top timeframe's own chart it only sees one story-timeframe candle per candle, so
    // there the story timeframe turning against it also counts)
    if sph == 1 and ((not na(tl) and (D1 > 0 ? (bos_wick ? x2l : x2c) < tl : (bos_wick ? x2h : x2c) > tl)) or (not chart_ok and D2 == -D1))
        sph := 2
        conf_now := true
        rh   := xt
        rh_t := xt_t
        rl   := fl
        rl_t := fl_t
        if na(rl) or (D1 > 0 ? rl >= rh : rl <= rh)
            rl   := D1 > 0 ? math.min(x1l, tl) : math.max(x1h, tl)
            rl_t := tl_t
        req  := (rh + rl) / 2
        rx_t := na
        f_sline(tl_t, time, tl, N2 + " BOS " + dn + ": " + N1 + " pullback confirmed", D1 < 0)
        f_story(time, D1 > 0 ? low : high, D1 < 0, "The last " + N2 + " " + LO + " " + str.tostring(tl, format.mintick) + " is broken (" + N2 + " close): the " + N1 + " pullback is confirmed.\n" + N1 + " range: " + HI + " " + str.tostring(rh, format.mintick) + " (target) · " + LO + " " + str.tostring(rl, format.mintick) + " · 0.5 " + str.tostring(req, format.mintick) + ".\nWatch the " + N1 + " levels in the " + (D1 > 0 ? "discount" : "premium") + " for a reaction.")
        tl := na
    // the story-timeframe range low broken first: still against the top timeframe
    if sph == 3 and not na(hl) and (D1 > 0 ? (bos_wick ? x2l : x2c) < hl : (bos_wick ? x2h : x2c) > hl)
        sph := 2
        conf_now := true
        rx_t := na
        ea_on := false
        f_sline(hl_t, time, hl, N2 + " BOS " + dn + " · " + N2 + " range " + LO + " broken", D1 < 0)
        f_story(time, D1 > 0 ? low : high, D1 < 0, "The " + N2 + " range " + LO + " " + str.tostring(hl, format.mintick) + " is broken (" + N2 + " close):\n" + N2 + " is still " + (D1 > 0 ? "bearish inside the bullish " : "bullish inside the bearish ") + N1 + " (a continuation " + dn + ").\nThe " + N1 + " pullback goes on: watch the " + N1 + " levels in the " + (D1 > 0 ? "discount." : "premium."))
        hl := na
    // the target
    if sph == 3 and not tg_done and not na(rh) and (D1 > 0 ? x2h >= rh : x2l <= rh)
        tg_done := true
        f_story(time, D1 > 0 ? high : low, D1 > 0, "Target reached: the " + N1 + " range " + HI + " " + str.tostring(rh, format.mintick) + ".")

// 4. price reaches a top-timeframe level in the discount (premium for sells)
if sph == 2 and D1 != 0 and array.size(bk1) > 0
    for v in bk1
        if v.bull == (D1 > 0) and not v.hit and f_kon(v.kind) and f_inz(v, rl, req) and (D1 > 0 ? low <= v.top : high >= v.bot)
            v.hit := true
            if na(rx_t)
                rx_t := time
                f_story(time, D1 > 0 ? low : high, D1 < 0, "Price reached the " + N1 + " " + f_kname(v.kind, v.bull) + " " + str.tostring(D1 > 0 ? v.top : v.bot, format.mintick) + ".\nWatch for an " + N2 + " External breakout " + up + ": " + N1 + " + " + N2 + " aligned.")

// 5. a story-timeframe breakout (the same one counted twice by the engine is skipped)
bool b_dup = D2 == lb_dir and not na(lb_t) and not na(x2t) and ((not na(lb_lvl) and not na(b_blvl) and math.abs(b_blvl - lb_lvl) <= syminfo.mintick * 2) or x2t - lb_t <= timeframe.in_seconds(T2) * 1000)
if not na(b_bcnt) and b_bcnt != k2 and b_dup
    k2 := b_bcnt
if not na(b_bcnt) and b_bcnt != k2
    k2 := b_bcnt
    lb_lvl := b_blvl
    lb_dir := D2
    lb_t   := x2t
    if D2 > 0
        f_add(bk2, 5, true, b_blvl, b_blvl, b_bt)
        f_add(bk2, 4, true, z2lt, z2lo, z2t)
    else if D2 < 0
        f_add(bk2, 5, false, b_blvl, b_blvl, b_bt)
        f_add(bk2, 4, false, z2hi, z2hb, z2ht)
    z2lo := na
    z2hi := na
    if D1 != 0 and not conf_now
        if D2 == D1
            if sph == 1
                // a continuation: the last low moves up to the low that caused it
                f_seg(tl_t, tl)
                tl   := D1 > 0 ? b_clo : b_chi
                tl_t := D1 > 0 ? b_clot : b_chit
                f_sline(b_bt, time, b_blvl, N2 + " " + (D1 > 0 ? "bullish" : "bearish") + " continuation", D1 > 0)
                f_story(time, D1 > 0 ? high : low, D1 > 0, N2 + " " + (D1 > 0 ? "bullish" : "bearish") + " continuation: still the " + N1 + " breakout, no pullback yet.\nThe last " + N2 + " " + LO + " moves to " + str.tostring(tl, format.mintick) + ": an " + N2 + " close beyond it = the " + N1 + " pullback.")
            else if sph == 2
                if not na(rx_t) and not na(b_bt) and b_bt < rx_t
                    sph := 3
                    hl   := D1 > 0 ? b_clo : b_chi
                    hl_t := D1 > 0 ? b_clot : b_chit
                    tg_done := false
                    ea_on := false
                    f_sline(b_bt, time, b_blvl, N2 + " BOS " + up + " · External", D1 > 0)
                    f_tag(N1 + " + " + N2 + " aligned", D1 > 0, D1 > 0 ? tg_alb : tg_als)
                    f_story(time, D1 > 0 ? high : low, D1 > 0, "The reaction gives an " + N2 + " External breakout " + up + ": " + N1 + " + " + N2 + " aligned.\nTarget: the " + N1 + " range " + HI + " " + str.tostring(rh, format.mintick) + ". " + N2 + " range: " + str.tostring(rh, format.mintick) + " ↔ " + str.tostring(hl, format.mintick) + ".\nIf " + str.tostring(hl, format.mintick) + " breaks first, " + N2 + " is still " + (D1 > 0 ? "bearish" : "bullish") + " inside the " + N1 + ".\nEntries: an " + N3 + " sweep and break at the " + N2 + " levels in its range.")
                else if show_int
                    string why = na(rx_t) ? "no " + N1 + " level reached yet" : "Internal: its level formed after price reached the " + N1 + " level"
                    f_sline(b_bt, time, b_blvl, N2 + " BOS " + up + (na(rx_t) ? "" : " · Internal"), D1 > 0)
                    f_story(time, D1 > 0 ? high : low, D1 > 0, N2 + " breakout " + up + " (" + why + "):\nnot aligned yet. Waiting for an " + N2 + " External breakout " + up + " after a reaction.")
            else if sph == 3
                hl   := D1 > 0 ? b_clo : b_chi
                hl_t := D1 > 0 ? b_clot : b_chit
                f_sline(b_bt, time, b_blvl, N2 + " BOS " + up, D1 > 0)
                f_story(time, D1 > 0 ? high : low, D1 > 0, N2 + " breakout " + up + ": a continuation, still aligned with the " + N1 + ".\nThe " + N2 + " range " + LO + " moves to " + str.tostring(hl, format.mintick) + "; new " + N2 + " levels in the range.")
        else if D2 == -D1
            if sph == 2
                f_sline(b_bt, time, b_blvl, N2 + " BOS " + dn, D1 < 0)
                f_story(time, D1 > 0 ? low : high, D1 < 0, N2 + " breakout " + dn + ": the " + N1 + " pullback goes on.\nWatch the " + N1 + " levels in the " + (D1 > 0 ? "discount." : "premium."))
            else if sph == 3 and show_int
                f_sline(b_bt, time, b_blvl, N2 + " BOS " + dn + " · inside the range", D1 < 0)
                f_story(time, D1 > 0 ? low : high, D1 < 0, N2 + " breakout " + dn + " inside the " + N2 + " range: the range " + LO + " " + str.tostring(hl, format.mintick) + " holds.\nOnly an " + N2 + " close beyond it puts " + N2 + " back against the " + N1 + ".")

// 6. entries: an entry-timeframe sweep of a story-timeframe level in its range, then a break
if chart_ok and en_on and sph == 3 and D1 != 0 and e_new
    bool just = false
    if ea_on
        ea_n += 1
        if (D1 > 0 ? e3c < ea_sw : e3c > ea_sw) or ea_n > en_win
            ea_on := false
        else if D1 > 0 ? e3c > ea_br : e3c < ea_br
            ea_on := false
            just := true
            if not na(ea_lv)
                ea_lv.used := true
            f_tag(N3 + " entry confirmed", D1 < 0, tg_en)
            f_story(time, D1 > 0 ? low : high, D1 < 0, N3 + " sweep and break at the " + N2 + " level " + str.tostring(ea_lvl, format.mintick) + ": " + N3 + " entry confirmed.\nInvalid beyond the sweep (" + str.tostring(ea_sw, format.mintick) + "). Target: the " + N1 + " range " + HI + " " + str.tostring(rh, format.mintick) + ".")
    if not ea_on and not just and array.size(bk2) > 0
        for v in bk2
            if v.bull == (D1 > 0) and not v.used and f_kon(v.kind) and f_inz(v, hl, rh)
                float lv_ = na
                if D1 > 0
                    if e3l < v.top and e3c > v.top
                        lv_ := v.top
                    else if v.top != v.bot and e3l < v.bot and e3c > v.bot
                        lv_ := v.bot
                else
                    if e3h > v.bot and e3c < v.bot
                        lv_ := v.bot
                    else if v.top != v.bot and e3h > v.top and e3c < v.top
                        lv_ := v.top
                float br = D1 > 0 ? e3fh : e3fl
                if not na(lv_) and not na(br) and (D1 > 0 ? br > e3c : br < e3c)
                    ea_on  := true
                    ea_sw  := D1 > 0 ? e3l : e3h
                    ea_br  := br
                    ea_lvl := lv_
                    ea_lv  := v
                    ea_n   := 0
                    break

// ── The levels at the last candle ────────────────────────────────────────────
var array<line>  cl = array.new<line>()
var array<label> cb = array.new<label>()
var array<box>   cx = array.new<box>()
f_lvl(int t, float y, string txt, color c, string st, int w) =>
    if not na(t) and not na(y)
        array.push(cl, line.new(t, y, time, y, xloc = xloc.bar_time, extend = extend.right, color = c, style = st, width = w))
        array.push(cb, label.new(bar_index + 3, y, txt + "  " + str.tostring(y, format.mintick), style = label.style_label_left,
             color = color.new(color.black, 100), textcolor = lv_tx, size = f_sz(lv_sz)))
f_draw(Lv v, string tfn, color c, int op, int w) =>
    string nm = tfn + " " + f_kname(v.kind, v.bull) + (v.hit ? " · reached" : "") + (v.used ? " · entry" : "")
    if v.kind == 3 or v.kind == 4
        int r = time + 12 * timeframe.in_seconds() * 1000
        array.push(cx, box.new(v.t, v.top, r, v.bot, xloc = xloc.bar_time, border_color = color.new(c, 30), bgcolor = color.new(c, 100 - op),
             text = nm, text_size = f_sz(lv_sz), text_color = lv_tx, text_halign = text.align_right, text_valign = text.align_center))
    else
        f_lvl(v.t, v.top, nm, c, v.kind == 2 ? line.style_dashed : v.kind == 5 ? line.style_dotted : line.style_solid, w)

// the levels of one book on the story's side inside the band a – b; overlapping ones (or closer than
// tol) are drawn as one: a box if any of them is a box, else their lines with one label
f_book(array<Lv> bk, float a, float b, string tfn, color c, int op, int w, int mx, float tol) =>
    array<int> cand = array.new<int>()
    int n = array.size(bk)
    if n > 0
        for i = n - 1 to 0
            Lv v = array.get(bk, i)
            if array.size(cand) < mx and v.bull == (D1 > 0) and f_kon(v.kind) and f_inz(v, a, b)
                array.push(cand, i)
    int m = array.size(cand)
    array<bool> done = array.new<bool>(m, false)
    if m > 0
        for g = 0 to m - 1
            if not array.get(done, g)
                array.set(done, g, true)
                Lv v0 = array.get(bk, array.get(cand, g))
                float  gt   = v0.top
                float  gb   = v0.bot
                int    t0   = v0.t
                bool   isbx = v0.kind == 3 or v0.kind == 4
                bool   hit  = v0.hit
                bool   used = v0.used
                string nm   = f_kname(v0.kind, v0.bull)
                array<int> mem = array.from(array.get(cand, g))
                for pass = 0 to 2
                    for j = 0 to m - 1
                        if not array.get(done, j)
                            Lv vj = array.get(bk, array.get(cand, j))
                            if vj.top >= gb - tol and vj.bot <= gt + tol
                                array.set(done, j, true)
                                array.push(mem, array.get(cand, j))
                                gt := math.max(gt, vj.top)
                                gb := math.min(gb, vj.bot)
                                t0 := math.min(t0, vj.t)
                                isbx := isbx or vj.kind == 3 or vj.kind == 4
                                hit := hit or vj.hit
                                used := used or vj.used
                                string kn = f_kname(vj.kind, vj.bull)
                                if not str.contains(nm, kn)
                                    nm := nm + " + " + kn
                string lab = tfn + " " + nm + (hit ? " · reached" : "") + (used ? " · entry" : "")
                if isbx
                    int r = time + 12 * timeframe.in_seconds() * 1000
                    array.push(cx, box.new(t0, gt, r, gb, xloc = xloc.bar_time, border_color = color.new(c, 30), bgcolor = color.new(c, 100 - op),
                         text = lab, text_size = f_sz(lv_sz), text_color = lv_tx, text_halign = text.align_right, text_valign = text.align_center))
                else
                    for k in mem
                        Lv vk = array.get(bk, k)
                        array.push(cl, line.new(vk.t, vk.top, time, vk.top, xloc = xloc.bar_time, extend = extend.right, color = c,
                             style = vk.kind == 2 ? line.style_dashed : vk.kind == 5 ? line.style_dotted : line.style_solid, width = w))
                    string px = gt - gb > syminfo.mintick ? str.tostring(gb, format.mintick) + " – " + str.tostring(gt, format.mintick) : str.tostring(gt, format.mintick)
                    array.push(cb, label.new(bar_index + 3, (gt + gb) / 2, lab + "  " + px, style = label.style_label_left,
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
    float tol = close * mg_pct / 100
    if D1 != 0 and sph >= 1
        string dw = D1 > 0 ? "bullish" : "bearish"
        if sph == 1 and t1x_on
            f_lvl(xt_t, xt, N1 + " " + dw + " external " + HI, t1x_col, line.style_solid, t1x_w)
            f_lvl(fl_t, fl, N1 + " " + dw + " external " + LO, t1x_col, line.style_solid, t1x_w)
        if sph == 1 and tl_on and not na(tl)
            f_lvl(tl_t, tl, "pullback line: last " + N2 + " " + LO + " (an " + N2 + " close beyond it = the " + N1 + " pullback)", tl_col, line.style_solid, tl_w)
        if sph >= 2 and not na(rh) and not na(rl)
            if rg_on
                f_lvl(rh_t, rh, N1 + " " + dw + " external " + HI + " · range " + HI + " (target)", rg_col, line.style_solid, rg_w)
                f_lvl(rl_t, rl, N1 + " " + dw + " external " + LO + " · range " + LO, rg_col, line.style_solid, rg_w)
                f_lvl(math.min(rh_t, rl_t), req, N1 + " range 0.5 · " + (D1 > 0 ? "discount below" : "premium above"), eq_col, line.style_dashed, 1)
            if sh_on
                int r0 = math.min(rh_t, rl_t)
                array.push(cx, box.new(r0, math.max(rl, req), time, math.min(rl, req), xloc = xloc.bar_time, extend = extend.right,
                     border_color = color.new(color.black, 100), bgcolor = color.new(D1 > 0 ? l1_bull : l1_bear, 100 - sh_op)))
                array.push(cx, box.new(r0, math.max(rh, req), time, math.min(rh, req), xloc = xloc.bar_time, extend = extend.right,
                     border_color = color.new(color.black, 100), bgcolor = color.new(D1 > 0 ? l1_bear : l1_bull, 100 - sh_op)))
            if l1_on
                f_book(bk1, rl, req, N1, D1 > 0 ? l1_bull : l1_bear, l1_op, l1_w, l1_max, tol)
        if chart_ok and sph == 3 and not na(hl)
            if hl_on
                f_lvl(hl_t, hl, N2 + " range " + LO + " (an " + N2 + " close beyond it: " + N2 + " still against the " + N1 + ")", hl_col, line.style_solid, 2)
            if l2_on
                f_book(bk2, hl, rh, N2, D1 > 0 ? l2_bull : l2_bear, l2_op, l2_w, l2_max, tol)
    // the story table: the newest notes first, each with its time
    // both tables in the same corner (even with the status table off, its empty table holds that
    // corner): TradingView shows only one, so the story goes into the status table, under it
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
        table.clear(tb, 0, 0, 1, 7)
        if not chart_ok
            f_row(0, PLAN, "On this chart: the " + N1 + " external high / low and the pullback line")
            f_row(1, N1, D1 > 0 ? "bullish" : D1 < 0 ? "bearish" : "—")
            f_row(2, N2, D2 == 0 ? "—" : D2 == D1 ? "with the " + N1 + ": no pullback yet" : "against the " + N1 + ": the pullback")
            f_row(3, "Story", "put the chart on " + N2 + " or lower (" + N3 + " for the entries)")
        else
            string phs = sph == 0 ? "waiting for a " + N1 + " breakout" : sph == 1 ? N1 + " breakout: " + N2 + " continuations; an " + N2 + " close beyond the last " + N2 + " " + LO + " = the pullback" : sph == 2 ? (na(rx_t) ? N1 + " pullback: watch the " + N1 + " levels in the " + (D1 > 0 ? "discount" : "premium") : N1 + " level reached: watch for an " + N2 + " External breakout " + up) : N1 + " + " + N2 + " aligned: " + N3 + " sweep and break at the " + N2 + " levels"
            f_row(0, "Plan", PLAN + " · " + N1 + " breaks by " + (brk_wick ? "wick" : "body close") + " · " + N2 + " by " + (bos_wick ? "wick" : "body close"))
            f_row(1, N1, D1 > 0 ? "bullish" : D1 < 0 ? "bearish" : "—")
            f_row(2, N2, D2 > 0 ? "bullish" : D2 < 0 ? "bearish" : "—")
            f_row(3, "Story", phs)
            if sph >= 2 and not na(rh)
                f_row(4, N1 + " range", str.tostring(rl, format.mintick) + " – " + str.tostring(rh, format.mintick) + " · 0.5 " + str.tostring(req, format.mintick) + " · target " + str.tostring(rh, format.mintick))
            if sph == 3 and not na(hl)
                f_row(5, N2 + " range", str.tostring(hl, format.mintick) + " – " + str.tostring(rh, format.mintick))
            f_row(6, "Entries", en_on ? N3 + " sweep and break at the " + N2 + " levels" + (timeframe.in_seconds() <= timeframe.in_seconds(T3) ? "" : " (put the chart on " + N3 + ")") : "off")
'''

NOTES = NOTES.replace('    if not na(t) and not na(y)', '    if chart_ok and not na(t) and not na(y)').replace('    if sl_on and not na(t1)', '    if chart_ok and sl_on and not na(t1)')
assert NOTES.count('if chart_ok and') == 2
body = HEAD + ENGINE + BODY + NOTES + STORY
open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
print(OUT, body.count('\n'), 'lines')
