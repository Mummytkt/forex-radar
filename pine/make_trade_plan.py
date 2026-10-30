"""Builds MummyTKT_TradePlan_TEST.pine: the High Level Trade Plan on the chart.

HTF objective -> MTF phase and POIs -> LTF execution (the chart). Display only.
The structure engine (f_ms / f_ms1) is copied from MummyTKT_Structure_3Types_TEST.pine,
so run make_structure_3types.py first after changing the engine.
"""
SRC = 'C:/Users/u/forex-radar/pine/MummyTKT_Structure_3Types_TEST.pine'
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_TradePlan_TEST.pine'

FIELDS = ['fdir', 'fh', 'fht', 'flo', 'flt', 'ch', 'chl', 'chp', 'chn', 'bt',
          'idir', 'ihi', 'iht', 'ihf', 'ilo', 'ilt', 'ilf', 'iev', 'ifl', 'ibl', 'ibp', 'inp', 'inpt', 'ipt', 'ipo', 'ipq', 'in_',
          'sdir', 'shi', 'sht', 'shf', 'slo', 'slt', 'slf', 'sev', 'sfl', 'sbl', 'sbp', 'snp', 'snpt', 'spt', 'spo', 'spq', 'sn']

src = open(SRC, encoding='utf-8').read().split('\n')
a = next(i for i, l in enumerate(src) if l.startswith('// ── Engine'))
b = next(i for i, l in enumerate(src) if l.startswith('[C_fdir'))
ENGINE = '\n'.join(src[a:b])

HEAD = r'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — High Level Trade Plan (TEST, display only, no alerts)
//
// HTF objective → MTF POIs → LTF execution. Pick the plan: Swing D → H4 → M15 or
// Day H4 → M15 → M5 (or custom); put the chart on its LTF.
// The MTF pullback is marked as in the picture: a = CHoCH against the swing (may be
// starting), b = i-BOS against it (confirmed; the swing high / low is fixed = weak),
// c = CHoCH back (may be ending), d = i-BOS back (phase A). Phase flow D → C → B → A.
//   HTF (default Daily): the swing direction, its strong / weak high and low, the
//       swing EQ (premium / discount) and the HTF POIs. The weak side is the objective.
//   MTF (default 4H): swing + internal structure → the phase for buys and for sells
//       (A pro swing + pro internal, B pro swing + counter internal, C counter swing
//       + pro internal, D counter both), and the MTF POIs.
//   LTF (this chart): once price reaches (mitigates) an MTF POI, an LTF CH (a wick
//       through the latest LTF fractal point) in the trade direction marks the LTF
//       entry model (▲ / ▼), if the phase and the HTF filter allow it.
// The watchlist table ticks the plan off live. Structure rules: see the Swing ·
// Internal · Fractal test script (same engine): BOS / i-BOS = body close beyond a
// wick level, CH = wick; a high is fixed by the opposite i-BOS (swing) / CH (internal).
// ─────────────────────────────────────────────────────────────────────────────

indicator("MummyTKT — Trade Plan (Test)", overlay = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 200, max_bars_back = 5000)

const string G_TF  = "1 · Timeframes (the chart is your LTF)"
const string G_ENT = "2 · LTF entry model (display only)"
const string G_SH  = "3 · What to show"
const string G_COL = "4 · Colours"

string plan = input.string("Swing: D → H4 → M15", "Plan (HTF → MTF → LTF)", options = ["Swing: D → H4 → M15", "Day: H4 → M15 → M5", "Custom (below)"], group = G_TF,
     tooltip = "Only the plan you pick is drawn. Put the chart on its LTF: M15 for Swing, M5 for Day (a lower chart works too).")
string cu_htf = input.timeframe("D",   "Custom: HTF", group = G_TF, inline = "cu")
string cu_mtf = input.timeframe("240", "MTF", group = G_TF, inline = "cu")
string cu_ltf = input.timeframe("15",  "LTF", group = G_TF, inline = "cu")
string htf = plan == "Swing: D → H4 → M15" ? "D" : plan == "Day: H4 → M15 → M5" ? "240" : cu_htf
string mtf = plan == "Swing: D → H4 → M15" ? "240" : plan == "Day: H4 → M15 → M5" ? "15" : cu_mtf
string ltf = plan == "Swing: D → H4 → M15" ? "15" : plan == "Day: H4 → M15 → M5" ? "5" : cu_ltf
int    flen = input.int(2, "Fractal: candles each side", minval = 1, maxval = 10, group = G_TF)

string ph_set  = input.string("A and B", "Mark entries in phases", options = ["A only", "A and B", "A, B and C"], group = G_ENT,
     tooltip = "The MTF phase for that trade direction. D (counter swing + counter internal) is never marked.")
string htf_flt = input.string("With the HTF direction", "HTF filter", options = ["With the HTF direction", "HTF discount for buys / premium for sells", "Off"], group = G_ENT,
     tooltip = "With the HTF direction: buys only while the HTF swing is bullish (sells: bearish). Discount / premium: buys only below the HTF swing EQ, sells only above it.")
int    ent_win = input.int(40, "LTF candles allowed after the MTF POI is reached", minval = 1, maxval = 500, group = G_ENT)
bool   use_int = input.bool(true, "MTF internal POIs count too", group = G_ENT, tooltip = "Off: only MTF swing POIs.")
bool   show_skip = input.bool(false, "Show skipped LTF CHs (grey, with the reason)", group = G_ENT)

bool show_h   = input.bool(true, "HTF swing levels + EQ", group = G_SH, inline = "s1")
bool show_hb  = input.bool(true, "HTF BOS", group = G_SH, inline = "s1")
bool show_m   = input.bool(true, "MTF swing + internal levels", group = G_SH, inline = "s2")
bool show_mb  = input.bool(true, "MTF BOS / i-BOS", group = G_SH, inline = "s2")
bool show_abcd = input.bool(true, "MTF pullback marks: CHoCH lines + a / b / c / d", group = G_SH, inline = "s3")
bool show_ph   = input.bool(true, "MTF phase changes (D / C / B / A)", group = G_SH, inline = "s3")
bool show_lch = input.bool(false, "LTF CH lines", group = G_SH)
bool show_poi = input.bool(true, "POIs (HTF swing, MTF swing + internal)", group = G_SH)
int  poi_max  = input.int(12, "POIs kept", minval = 1, maxval = 50, group = G_SH)
int  keep_n   = input.int(12, "Past breaks kept (each type)", minval = 1, maxval = 100, group = G_SH)
bool tbl_on   = input.bool(true, "Watchlist table", group = G_SH, inline = "t")
string tbl_pos = input.string("Top right", "", options = ["Top right", "Bottom right", "Top left", "Bottom left"], group = G_SH, inline = "t")

color c_bull = input.color(#26A69A, "Bullish", group = G_COL, inline = "c1")
color c_bear = input.color(#EF5350, "Bearish", group = G_COL, inline = "c1")
color c_htf  = input.color(#E0E0E0, "HTF levels", group = G_COL, inline = "c2")
color c_mtf  = input.color(#FFB74D, "MTF levels", group = G_COL, inline = "c2")
color c_eq   = input.color(#9E9E9E, "EQ", group = G_COL, inline = "c2")
color c_dem  = input.color(#26A69A, "Demand POI", group = G_COL, inline = "c3")
color c_sup  = input.color(#EF5350, "Supply POI", group = G_COL, inline = "c3")
color c_mit  = input.color(#787B86, "Mitigated / skipped", group = G_COL, inline = "c3")
color c_ent  = input.color(#7C4DFF, "LTF entry", group = G_COL, inline = "c4")

'''

TAIL = r'''
bool H_ok = timeframe.in_seconds(htf) >= timeframe.in_seconds()
bool M_ok = timeframe.in_seconds(mtf) >= timeframe.in_seconds()
bool L_ok = timeframe.in_seconds(ltf) >= timeframe.in_seconds()
bool L_eq = timeframe.in_seconds(ltf) == timeframe.in_seconds()
// The LTF CH on this candle: the chart's own when the chart is the LTF, else the
// requested LTF's (once, when its count changes)
int   L_chev = L_eq ? C_ch : (L_ok and not na(L_chn) and L_chn != nz(L_chn[1]) ? L_ch : 0)
float L_chlv = L_eq ? C_chl : L_chl
int   L_chpt = L_eq ? C_chp : L_chp

f_tfname(string tf) =>
    tf == "D" or tf == "1D" ? "D" : tf == "W" or tf == "1W" ? "W" : tf == "240" ? "H4" : tf == "60" ? "H1" : tf == "120" ? "H2" : tf == "30" ? "M30" : tf == "15" ? "M15" : tf == "5" ? "M5" : tf
string H_tf = f_tfname(htf) + " "
string M_tf = f_tfname(mtf) + " "

// ── Breaks on the chart ──────────────────────────────────────────────────────
var array<line>  l_b  = array.new<line>()
var array<label> lb_b = array.new<label>()
f_cap_l(array<line> a, int cap) =>
    while array.size(a) > cap
        line.delete(array.shift(a))
f_cap_lb(array<label> a, int cap) =>
    while array.size(a) > cap
        label.delete(array.shift(a))
f_brk(int pt, int bt, float y, int d, string txt, string st, int w) =>
    if not na(pt) and not na(y)
        color c = d > 0 ? c_bull : c_bear
        array.push(l_b, line.new(pt, y, bt, y, xloc = xloc.bar_time, style = st, color = c, width = w))
        array.push(lb_b, label.new(pt + int((bt - pt) / 2), y, txt, xloc = xloc.bar_time, style = d > 0 ? label.style_label_down : label.style_label_up,
             color = color.new(color.black, 100), textcolor = c, size = size.tiny))
        f_cap_l(l_b, keep_n * 4)
        f_cap_lb(lb_b, keep_n * 4)

// ── POIs: tf 1 = HTF, 2 = MTF; mitigated = the bar price first came back into it ──
var array<box>   pz   = array.new<box>()
var array<float> pz_t = array.new<float>()
var array<float> pz_b = array.new<float>()
var array<bool>  pz_d = array.new<bool>()
var array<int>   pz_f = array.new<int>()
var array<int>   pz_m = array.new<int>()
var array<bool>  pz_e = array.new<bool>()   // an LTF entry was already marked from it
f_pz_drop(int k) =>
    box.delete(array.get(pz, k))
    array.remove(pz, k)
    array.remove(pz_t, k)
    array.remove(pz_b, k)
    array.remove(pz_d, k)
    array.remove(pz_f, k)
    array.remove(pz_m, k)
    array.remove(pz_e, k)
f_poi_add(float top, float bot, int t, bool demand, int tf, string txt) =>
    if not na(top) and not na(bot) and not na(t)
        color c = demand ? c_dem : c_sup
        array.push(pz, box.new(t, top, time, bot, xloc = xloc.bar_time, border_color = c, bgcolor = color.new(c, tf == 1 ? 88 : 80),
             border_width = tf == 1 ? 2 : 1, text = txt, text_size = size.tiny, text_color = c, text_halign = text.align_right, text_valign = text.align_center))
        array.push(pz_t, top)
        array.push(pz_b, bot)
        array.push(pz_d, demand)
        array.push(pz_f, tf)
        array.push(pz_m, -1)
        array.push(pz_e, false)
        if not show_poi
            box.set_bgcolor(array.last(pz), color.new(c, 100))
            box.set_border_color(array.last(pz), color.new(c, 100))
            box.set_text_color(array.last(pz), color.new(c, 100))
        while array.size(pz) > poi_max
            f_pz_drop(0)

// ── HTF / MTF events ─────────────────────────────────────────────────────────
// The MTF pullback, as in the picture (buys; sells mirror):
//   a = CHoCH against the swing while internal is still with it: the pullback may be starting
//   b = i-BOS that turns internal against the swing: the pullback is confirmed, the swing
//       high is fixed (weak = the target)
//   c = CHoCH back with the swing while internal is against it: the pullback may be ending
//   d = i-BOS that turns internal back with the swing: phase A
var bool pb_a   = false   // a seen since the swing / internal last lined up
var bool pb_c   = false
var bool pb_poi = false   // during the pullback: an extreme POI on the swing side was mitigated in discount (premium)
f_badge(int t, float y, string ch, int d, string tip) =>
    if show_abcd and not na(t) and not na(y)
        label.new(t, y, ch, xloc = xloc.bar_time, style = d > 0 ? label.style_label_up : label.style_label_down,
             color = d > 0 ? c_bull : c_bear, textcolor = color.white, size = size.tiny, tooltip = tip)

var int H_k = 0
var int M_k1 = 0
var int M_k2 = 0
if H_ok and not na(H_sn) and H_sn != H_k
    H_k := H_sn
    if H_sev != 0
        if show_hb
            f_brk(H_sbp, H_bt, H_sbl, H_sev, H_tf + "BOS", line.style_solid, 3)
        f_poi_add(H_spt, H_spo, H_spq, H_sev > 0, 1, H_tf + "swing " + (H_sev > 0 ? "demand" : "supply"))
var int M_kc = 0
if M_ok and not na(M_chn) and M_chn != M_kc
    M_kc := M_chn
    if M_ch != 0 and M_sdir != 0
        if M_ch == -M_sdir and M_idir == M_sdir and not pb_a
            pb_a := true
            if show_abcd
                f_brk(M_chp, M_bt, M_chl, M_ch, M_tf + "CHoCH", line.style_dashed, 1)
            f_badge(M_bt, M_chl, "a", M_ch, M_tf + (M_ch < 0 ? "bearish" : "bullish") + " CHoCH (wick): the internal pullback may be starting. Early sign only.")
        else if M_ch == M_sdir and M_idir == -M_sdir and not pb_c
            pb_c := true
            if show_abcd
                f_brk(M_chp, M_bt, M_chl, M_ch, M_tf + "CHoCH", line.style_dashed, 1)
            f_badge(M_bt, M_chl, "c", M_ch, M_tf + (M_ch > 0 ? "bullish" : "bearish") + " CHoCH (wick): the internal pullback may be ending. The swing " + (M_sdir > 0 ? "HL" : "LH") + " may be forming.")
if M_ok and not na(M_in_) and M_in_ != M_k1
    M_k1 := M_in_
    if M_iev != 0 and M_ifl and M_sdir != 0
        if M_iev == -M_sdir
            f_badge(M_bt, M_ibl, "b", M_iev, M_tf + (M_iev < 0 ? "bearish" : "bullish") + " i-BOS (body close): the swing pullback is confirmed. The swing " + (M_sdir > 0 ? "high" : "low") + " is fixed: WEAK, the target.")
            pb_c   := false
            pb_poi := false
        else
            f_badge(M_bt, M_ibl, "d", M_iev, M_tf + (M_iev > 0 ? "bullish" : "bearish") + " i-BOS (body close): internal back in line with the swing. Phase A.")
            pb_a   := false
            pb_poi := false
    if M_iev != 0
        if show_mb
            f_brk(M_ibp, M_bt, M_ibl, M_iev, M_tf + "i-BOS", line.style_dotted, 1)
        if use_int
            f_poi_add(M_ipt, M_ipo, M_ipq, M_iev > 0, 2, M_tf + "internal " + (M_iev > 0 ? "demand" : "supply"))
if M_ok and not na(M_sn) and M_sn != M_k2
    M_k2 := M_sn
    if M_sev != 0
        pb_a   := false
        pb_c   := false
        pb_poi := false
        if show_mb
            f_brk(M_sbp, M_bt, M_sbl, M_sev, M_tf + "BOS", line.style_solid, 2)
        f_poi_add(M_spt, M_spo, M_spq, M_sev > 0, 2, M_tf + "swing " + (M_sev > 0 ? "demand" : "supply"))
if show_lch and L_chev != 0 and not na(L_chpt)
    f_brk(L_chpt, time, L_chlv, L_chev, "CH", line.style_dashed, 1)

// ── The plan ─────────────────────────────────────────────────────────────────
// Phase for a trade direction: A pro swing + pro internal, B pro swing + counter
// internal, C counter swing + pro internal, D counter both
f_phase(int s, int i, bool long) =>
    int ws = long ? s : -s
    int wi = long ? i : -i
    s == 0 or i == 0 ? "—" : ws > 0 ? (wi > 0 ? "A" : "B") : (wi > 0 ? "C" : "D")
f_phtxt(string p) =>
    p == "A" ? "A · full alignment" : p == "B" ? "B · internal still pulling back" : p == "C" ? "C · counter swing (quick targets)" : p == "D" ? "D · avoid" : "—"
f_phok(string p) =>
    p == "A" or (p == "B" and ph_set != "A only") or (p == "C" and ph_set == "A, B and C")

float h_eq  = (H_shi + H_slo) / 2
float m_eq  = (M_shi + M_slo) / 2
bool  in_disc = not na(h_eq) and close < h_eq
string phL = f_phase(M_sdir, M_idir, true)
string phS = f_phase(M_sdir, M_idir, false)
bool htfL = htf_flt == "Off" ? true : htf_flt == "With the HTF direction" ? H_sdir > 0 : in_disc
bool htfS = htf_flt == "Off" ? true : htf_flt == "With the HTF direction" ? H_sdir < 0 : not na(h_eq) and close > h_eq

// The MTF phase as the picture walks it (on the MTF swing direction):
//   internal with the swing:      A (trade with the swing) · D once an "a" CHoCH came (wait for the i-BOS)
//   internal against the swing:   C (play the pullback) · B once an extreme POI was mitigated in discount / premium
f_flow() =>
    M_sdir == 0 or M_idir == 0 ? "" : M_idir == M_sdir ? (pb_a ? "D" : "A") : (pb_poi ? "B" : "C")
f_flowtxt(string f) =>
    bool up = M_sdir > 0
    f == "A" ? "A · " + (up ? "longs" : "shorts") + " → the weak swing " + (up ? "high" : "low")
     : f == "D" ? "D · " + (up ? "shorts" : "longs") + ": wait for the i-BOS"
     : f == "C" ? "C · " + (up ? "shorts" : "longs") + ": play the pullback, quick targets"
     : f == "B" ? "B · " + (up ? "longs" : "shorts") + ": extreme POI mitigated in " + (up ? "discount" : "premium")
     : "—"
var string flow_now = ""

var int    ent_bar  = na     // the last LTF entry model marked
var int    ent_dir  = 0
var string ent_txt  = ""

// POIs: invalidate (closed through), mitigate (first touch), extend; LTF entries
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
            if array.get(pz_m, k) < 0
                box.set_right(bx, time)
                if dm ? low <= tp : high >= bb
                    array.set(pz_m, k, bar_index)
                    if M_sdir != 0 and M_idir == -M_sdir and dm == (M_sdir > 0) and not na(m_eq) and (M_sdir > 0 ? close < m_eq : close > m_eq)
                        pb_poi := true
                    if show_poi
                        box.set_bgcolor(bx, color.new(c_mit, 85))
                        box.set_border_color(bx, c_mit)
                        box.set_text_color(bx, c_mit)
            // LTF entry model: an LTF CH in the POI's direction after the MTF POI was reached
            int mb = array.get(pz_m, k)
            if array.get(pz_f, k) == 2 and mb >= 0 and not array.get(pz_e, k) and bar_index - mb <= ent_win and L_chev == (dm ? 1 : -1)
                string ph  = dm ? phL : phS
                bool   hok = dm ? htfL : htfS
                if f_phok(ph) and hok
                    array.set(pz_e, k, true)
                    float tgt = dm ? M_shi : M_slo
                    string tip = (dm ? "BUY" : "SELL") + " · LTF entry model\nMTF " + (dm ? "demand " : "supply ") + str.tostring(bb, format.mintick) + " – " + str.tostring(tp, format.mintick)
                         + "\nMTF phase " + ph + " · HTF " + (H_sdir > 0 ? "bullish" : H_sdir < 0 ? "bearish" : "—") + (in_disc ? " · price in HTF discount" : " · price in HTF premium")
                         + "\nInvalid beyond the POI: " + str.tostring(dm ? bb : tp, format.mintick)
                         + "\nTarget: MTF weak " + (dm ? "high " : "low ") + str.tostring(tgt, format.mintick)
                    label.new(bar_index, dm ? low : high, dm ? "▲" : "▼", yloc = dm ? yloc.belowbar : yloc.abovebar, style = label.style_none,
                         textcolor = c_ent, size = size.normal, tooltip = tip)
                    ent_bar := bar_index
                    ent_dir := dm ? 1 : -1
                    ent_txt := tip
                else if show_skip
                    array.set(pz_e, k, true)
                    label.new(bar_index, dm ? low : high, dm ? "△" : "▽", yloc = dm ? yloc.belowbar : yloc.abovebar, style = label.style_none,
                         textcolor = c_mit, size = size.small, tooltip = "Skipped: " + (not f_phok(ph) ? "MTF phase " + ph : "HTF filter (" + htf_flt + ")"))
        k -= 1

// Phase changes on the chart
string flow = M_ok ? f_flow() : ""
if flow != flow_now
    flow_now := flow
    if show_ph and flow != "" and barstate.isconfirmed
        color fc = flow == "A" ? c_bull : flow == "D" ? c_bear : color.new(#FFB74D, 0)
        label.new(bar_index, low, "Phase " + flow, yloc = yloc.belowbar, style = label.style_none, textcolor = fc, size = size.small,
             tooltip = M_tf + "phase " + f_flowtxt(flow))

// ── Current levels (strong / weak), EQ, merged labels ────────────────────────
var array<line>   cur_l = array.new<line>()
var array<label>  cur_b = array.new<label>()
var array<float>  pv_y  = array.new<float>()
var array<string> pv_s  = array.new<string>()
var array<color>  pv_c  = array.new<color>()
f_pend(float y, string txt, color c) =>
    array.push(pv_y, y)
    array.push(pv_s, txt)
    array.push(pv_c, c)
f_cur(string tf, string nm, int dir, float hi, int ht, bool hf, float lo, int lt, bool lf, string st, color c, int w, bool eq) =>
    if dir != 0 and not na(hi) and not na(lo) and not na(ht) and not na(lt)
        string d  = dir > 0 ? "Bullish " : "Bearish "
        string hs = dir < 0 ? "strong" : hf ? "weak (target)" : "weak, still forming"
        string ls = dir > 0 ? "strong" : lf ? "weak (target)" : "weak, still forming"
        array.push(cur_l, line.new(ht, hi, time, hi, xloc = xloc.bar_time, extend = extend.right, style = st, color = c, width = w))
        array.push(cur_l, line.new(lt, lo, time, lo, xloc = xloc.bar_time, extend = extend.right, style = st, color = c, width = w))
        f_pend(hi, tf + d + nm + " high · " + hs, c)
        f_pend(lo, tf + d + nm + " low · " + ls, c)
        if eq
            float e = (hi + lo) / 2
            array.push(cur_l, line.new(math.max(ht, lt), e, time, e, xloc = xloc.bar_time, extend = extend.right, style = line.style_dashed, color = c_eq))
            f_pend(e, tf + "swing EQ 50% · price in " + (close > e ? "premium" : "discount"), c_eq)

f_tpos(string p) =>
    p == "Top right" ? position.top_right : p == "Bottom right" ? position.bottom_right : p == "Top left" ? position.top_left : position.bottom_left
var table tb = table.new(f_tpos(tbl_pos), 2, 14, bgcolor = color.new(#0F1120, 8), border_width = 1, border_color = color.new(color.gray, 75))
f_row(int r, bool ok, string txt) =>
    table.cell(tb, 0, r, ok ? "✓" : "·", text_color = ok ? c_bull : color.gray, text_size = size.small)
    table.cell(tb, 1, r, txt, text_color = color.white, text_size = size.small, text_halign = text.align_left)
f_dirw(int d) =>
    d > 0 ? "Bullish" : d < 0 ? "Bearish" : "no direction yet"

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
    if show_h and H_ok
        f_cur(H_tf, "HTF swing", H_sdir, H_shi, H_sht, H_shf, H_slo, H_slt, H_slf, line.style_solid, c_htf, 2, true)
    if show_m and M_ok
        f_cur(M_tf, "MTF swing", M_sdir, M_shi, M_sht, M_shf, M_slo, M_slt, M_slf, line.style_solid, c_mtf, 1, false)
        f_cur(M_tf, "MTF internal", M_idir, M_ihi, M_iht, M_ihf, M_ilo, M_ilt, M_ilf, line.style_dotted, c_mtf, 1, false)
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

    // ── Watchlist ──
    if tbl_on
        table.clear(tb, 0, 0, 1, 13)
        bool  bull = H_sdir > 0
        bool  bear = H_sdir < 0
        bool  lng  = not bear          // the plan's side: with the HTF (buys when no HTF direction yet)
        string side = bull ? "BUYS" : bear ? "SELLS" : "RANGE · no HTF direction yet"
        table.cell(tb, 0, 0, "", text_size = size.small)
        table.cell(tb, 1, 0, "WATCHLIST · " + side, text_color = color.new(#B39DDB, 0), text_size = size.normal, text_halign = text.align_left)
        if not H_ok or not M_ok or not L_ok
            f_row(1, false, plan + ": put the chart on " + f_tfname(ltf) + " (or lower)")
        else
            // 1 HTF objective
            f_row(1, H_sdir != 0, H_tf + "swing " + f_dirw(H_sdir) + (H_sdir > 0 ? " · objective: weak high " + str.tostring(H_shi, format.mintick) : H_sdir < 0 ? " · objective: weak low " + str.tostring(H_slo, format.mintick) : ""))
            // 2 premium / discount
            bool good_side = lng ? in_disc : not in_disc
            f_row(2, good_side, "Price in HTF " + (in_disc ? "discount" : "premium") + " (EQ " + str.tostring(h_eq, format.mintick) + ")" + (good_side ? "" : lng ? " · careful with buys in premium" : " · careful with sells in discount"))
            // 3 HTF pullback = MTF swing against the HTF
            bool pull = H_sdir != 0 and M_sdir != 0 and M_sdir != H_sdir
            f_row(3, not pull, M_tf + "swing " + f_dirw(M_sdir) + ", internal " + f_dirw(M_idir) + (pull ? " · HTF pullback in progress" : H_sdir != 0 and M_sdir == H_sdir ? " · MTF with the HTF" : ""))
            // 4 phase for the plan's side, and the other side
            string pmain = lng ? phL : phS
            string poth  = lng ? phS : phL
            f_row(4, pmain == "A" or pmain == "B", (lng ? "Buys" : "Sells") + ": phase " + f_phtxt(pmain))
            f_row(5, false, (lng ? "Sells" : "Buys") + ": phase " + f_phtxt(poth))
            // 5 extreme HTF POI and the MTF POI reached
            int   hk = -1
            int   mk = -1
            if array.size(pz) > 0
                for k2 = array.size(pz) - 1 to 0
                    if array.get(pz_d, k2) == lng
                        if hk < 0 and array.get(pz_f, k2) == 1
                            hk := k2
                        if mk < 0 and array.get(pz_f, k2) == 2 and array.get(pz_m, k2) >= 0
                            mk := k2
            bool hmit = hk >= 0 and array.get(pz_m, hk) >= 0
            f_row(6, hmit, hk < 0 ? "No HTF " + (lng ? "demand" : "supply") + " POI yet" : "HTF " + (lng ? "demand " : "supply ") + str.tostring(array.get(pz_b, hk), format.mintick) + " – " + str.tostring(array.get(pz_t, hk), format.mintick) + (hmit ? " · mitigated" : " · not reached yet"))
            bool mrecent = mk >= 0 and bar_index - array.get(pz_m, mk) <= ent_win
            f_row(7, mrecent, mk < 0 ? "No MTF " + (lng ? "demand" : "supply") + " POI reached yet" : "MTF " + (lng ? "demand " : "supply ") + str.tostring(array.get(pz_b, mk), format.mintick) + " – " + str.tostring(array.get(pz_t, mk), format.mintick) + (mrecent ? " · reached: look at the LTF" : " · reached " + str.tostring(bar_index - array.get(pz_m, mk)) + " candles ago"))
            // 6 LTF entry
            bool ent_now = not na(ent_bar) and ent_dir == (lng ? 1 : -1) and bar_index - ent_bar <= ent_win
            f_row(8, ent_now, ent_now ? "LTF CH inside the MTF POI: entry model " + str.tostring(bar_index - ent_bar) + " candles ago" : "Waiting for an LTF CH " + (lng ? "up" : "down") + " after an MTF POI is reached")
            string status = ent_now ? "ENTRY MODEL · manage the trade" : mrecent and (pmain == "A" or pmain == "B") ? "WATCH THE LTF · price is at an MTF POI" : pmain == "D" ? "WAIT · phase D" : "WAIT for an MTF POI"
            table.cell(tb, 0, 9, "", text_size = size.small)
            table.cell(tb, 1, 9, status, text_color = ent_now ? c_bull : mrecent ? color.new(#FFB74D, 0) : color.gray, text_size = size.normal, text_halign = text.align_left)
            if H_sdir == 0
                f_row(10, false, "Range: stay out of the middle · buys bottom 33%, sells top 33%, or wait for the breakout")
            f_row(11, false, "Always ask: what is the HTF objective? What has been mitigated?")
            string pbs = M_sdir == 0 ? "—" : M_idir == M_sdir ? (pb_a ? "a · CHoCH against the swing: pullback may be starting" : "d · internal with the swing") : (pb_c ? "c · CHoCH back with the swing: pullback may be ending" : "b · i-BOS: pullback confirmed")
            f_row(12, flow == "A", M_tf + "phase now: " + f_flowtxt(flow) + "  ·  last mark " + pbs)
            table.cell(tb, 1, 13, plan + (L_eq ? "" : " · LTF " + f_tfname(ltf) + " read from a lower chart"), text_color = color.gray, text_size = size.tiny, text_halign = text.align_left)
'''


def names(p):
    return ', '.join(p + f for f in FIELDS)


body = HEAD + ENGINE + '\n'
body += f'[{names("C_")}] = f_ms(flen)\n'
body += f'[{names("H_")}] = request.security(syminfo.tickerid, htf, f_ms1(flen), lookahead = barmerge.lookahead_on)\n'
body += f'[{names("M_")}] = request.security(syminfo.tickerid, mtf, f_ms1(flen), lookahead = barmerge.lookahead_on)\n'
body += f'[{names("L_")}] = request.security(syminfo.tickerid, ltf, f_ms1(flen), lookahead = barmerge.lookahead_on)\n'
body += TAIL
open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
print(OUT, body.count('\n'), 'lines')
