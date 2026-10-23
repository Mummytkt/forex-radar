# Builds MummyTKT_BiasPointer_Backtest.pine from the live script. Re-run after every live Pine change:
#   python pine/make_backtest.py
#
# The backtest copy can also carry NEW rules the user is trying out before they go
# live (see "Backtest-only rules" below). Once the user confirms them, port them to
# the live script and delete them here.
import os

R = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(R, 'MummyTKT_BiasPointer.pine'), encoding='utf-8').read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:90], s.count(a))
    s = s.replace(a, b)


rep('''// MummyTKT's Bias Pointer v6 — TradingView Edition
''', '''// MummyTKT's Bias Pointer v6 — BACKTEST EDITION (on-chart labels)
//
// The live alert script plus labels: wherever the live script sends a bias
// alert, this one puts an "H4 aligned - Alert" label on that H4 candle,
// filtered the way Alert Filters filter Telegram (defaults = defaults):
//   Origin (BUY / SELL CONFIRMED)   External on, Internal off
//   H4 back in line                 External on, Internal off
//   H4 breakout in line, Breaker Origin / retest, OC reaction, Engulfing (wick)
// Continuations follow the setup's latest H4 confirmation (External / Internal).
//
// BEING TRIED OUT HERE FIRST (not in the live alerts yet):
//   • Daily V-shapes (A-shapes for sells) formed after the Daily breakout,
//     beyond the Daily Breaker, are reaction levels while the direction holds
//     (they die on a Daily close through them, like every Daily level).
//   • A fresh Daily reaction followed by an H4 breakout alerts EVERY time,
//     also while H4 is still aligned after the Origin:
//     "Daily reaction + H4 breakout". Each fresh reaction after a confirmation
//     starts its own External / Internal check.
//   • A new Daily breakout in the SAME direction doesn't reset H4: in-line
//     breakouts and H4 reactions keep firing. A reaction at the new breakout's
//     Daily levels + an H4 breakout then becomes what H4 rides on. Only a Daily
//     breakout the other way resets H4.
//
// The label sits on the candle that CLOSED to confirm: entry = next candle's open.
// Daily data is read from completed candles only, so history doesn't repaint.
// No alert needs to be created on this copy.
//
''')
rep('indicator("MummyTKT Bias Pointer", overlay=true, max_bars_back=2000, max_lines_count=100, max_labels_count=100)',
    '''indicator("MummyTKT Bias Pointer — Backtest", overlay=true, max_bars_back=2000, max_lines_count=100, max_labels_count=500)

// ── Backtest labels (same switches as Alert Filters) ──────────────────────────
GBT = "Backtest labels"
bool   bt_weekly   = input.bool(false, "Weekly (lines, labels, Weekly AGAINST marks)", group=GBT,
     tooltip="Off: Daily + H4 only. The Weekly never changes which alerts fire; it only adds context.")
bool   bt_ext      = input.bool(true,  "External H4 breakouts", group=GBT)
bool   bt_int      = input.bool(false, "Internal H4 breakouts", group=GBT)
bool   bt_origin   = input.bool(true,  "Origin — BUY / SELL CONFIRMED", group=GBT)
bool   bt_react    = input.bool(true,  "Daily reaction + H4 breakout (after the Origin)", group=GBT)
bool   bt_realign  = input.bool(true,  "H4 back in line", group=GBT)
bool   bt_inline   = input.bool(true,  "H4 breakout in line", group=GBT)
bool   bt_breaker  = input.bool(true,  "H4 Breaker (Origin + retests)", group=GBT)
bool   bt_oc       = input.bool(true,  "H4 OC reaction", group=GBT)
bool   bt_engulf   = input.bool(true,  "H4 engulfing", group=GBT)
string bt_eng_mode = input.string("Wick", "Engulfing covers", options=["Wick", "Body only", "Both"], group=GBT)
int    bt_from     = input.time(timestamp("2020-01-01T00:00:00"), "Backtest from", group=GBT,
     tooltip="Labels and counts start at this date. Earlier candles still build the levels.")
bool   bt_latest   = input.bool(true,  "Keep only the latest alert label (clean chart)", group=GBT,
     tooltip="Each new alert label deletes the previous one. The count table still counts every alert. Switch off to see the whole history.")
bool   bt_grey     = input.bool(true,  "Show alerts that are not counted (grey, with the reason)", group=GBT,
     tooltip="Alerts before the start date, Internal ones while Internal is off, and types switched off above.")
bool   bt_table    = input.bool(true,  "Show count table", group=GBT)
bool   bt_lvls     = input.bool(true,  "Show the Daily reaction levels being watched (4H)", group=GBT,
     tooltip="Every Daily level the script would accept a reaction at right now. A level that is missing here can't trigger an alert.")
color  bt_buy_col  = input.color(#00C853, "Buy label", group=GBT, inline="btc")
color  bt_sell_col = input.color(#FF1744, "Sell label", group=GBT, inline="btc")
// counts: 0 Origin, 1 Back in line, 2 In line, 3 Breaker Origin, 4 Breaker retest, 5 OC, 6 Engulfing,
//         7 Daily reaction + H4 breakout, 8 Buys, 9 Sells
var bt_cnt  = array.new_int(10, 0)
var int bt_t0 = time
// External / Internal of the setup's latest H4 confirmation (Origin, Daily reaction
// + H4 breakout, or back in line); continuations follow it, like the server
var bt_scls = array.from("")
var bt_last = array.new<label>(1, na)   // the alert label currently on the chart
// The External H4 level of the current Daily reaction: the latest H4 A (buys) /
// V (sells) when the reaction started, i.e. formed BEFORE it
var float bt_ext_a = na
var float bt_ext_v = na
var bt_seen = array.new<float>()   // Daily levels already touched since they formed
var BT_NAMES = array.from("Origin", "Back in line", "H4 breakout in line", "Breaker Origin", "Breaker retest", "OC reaction", "Engulfing", "Daily reaction + H4 breakout")''')

# Label function: after f_wk(), so it can read the Weekly relation
# 3. A new Daily breakout in the SAME direction carries the H4 ride on: H4 stays
#    confirmed / aligned with its Breaker, OCs and levels, so in-line breakouts and
#    H4 reactions keep firing. A reaction at the new breakout's Daily levels + an H4
#    breakout ("Daily reaction + H4 breakout") then becomes what H4 rides on.
#    Only a Daily breakout the other way resets H4.
rep('''    last_bcnt := s_bcnt
    bo_dir    := s_bdir
''', '''    last_bcnt := s_bcnt
    bool bt_same = bo_dir == s_bdir and h4_bo_fired   // same direction, H4 already riding
    bo_dir    := s_bdir
''')
rep('''    h4_a_lvl  := na
    h4_v_lvl  := na
    pb_consec := 0
''', '''    if not bt_same
        h4_a_lvl  := na
        h4_v_lvl  := na
    pb_consec := 0
''')
rep('''    h4_bo_fired           := false
    h4_breaker_orig_fired := false
    h4_breaker_lvl        := na
    h4_invalid_lvl        := na
    h4_aligned            := false
    array.clear(h4_ocs)
    array.clear(h4_ocb)
    h4_brk_lvl            := na
    bo_wk_rel := ""
''', '''    if not bt_same
        h4_bo_fired           := false
        h4_breaker_orig_fired := false
        h4_breaker_lvl        := na
        h4_invalid_lvl        := na
        h4_aligned            := false
        array.clear(h4_ocs)
        array.clear(h4_ocb)
        h4_brk_lvl            := na
        array.set(bt_scls, 0, "")
    bo_wk_rel := ""
''')
rep('''// Weekly context sent with every bias alert (empty when there is no Weekly setup)
f_wk() =>
''', '''f_bt_src(string s) =>
    s == "daily_breaker" ? "Daily Breaker" : s == "post_breakout_oc" ? "Daily OC after the breakout" : s == "post_breakout_v" ? "Daily V/A-shape after the breakout" : s == "inside_range" ? "Daily level inside the broken range" : "-"

// Backtest: label where an alert is sent (returns true if labelled)
f_btlbl(bool bull, int kind, string cls, float h4lvl, float dlvl, string note) =>
    bool conf = kind <= 1 or kind == 7   // an H4 confirmation after a Daily reaction
    bool tf_ok = timeframe.period == "240"   // the H4 steps only mean something on 4H candles
    bool on = kind == 7 ? bt_react : kind == 0 ? bt_origin : kind == 1 ? bt_realign : kind == 2 ? bt_inline : kind <= 4 ? bt_breaker : kind == 5 ? bt_oc : bt_engulf
    if conf
        array.set(bt_scls, 0, cls)
    string c = array.get(bt_scls, 0)
    bool cls_ok = c == "" or (c == "external" ? bt_ext : bt_int)
    string head = kind == 0 ? (bull ? "BUY CONFIRMED" : "SELL CONFIRMED") : (bull ? "BUY" : "SELL") + " · " + array.get(BT_NAMES, kind)
    string tag  = c == "" ? "" : conf ? (c == "external" ? " (External)" : " (Internal)") : (c == "external" ? " (External setup)" : " (Internal setup)")
    if tf_ok and bt_grey and not (on and cls_ok and time >= bt_from)
        string why = time < bt_from ? "before the backtest start" : not cls_ok ? "Internal is switched off" : "this type is switched off"
        if bt_latest
            label.delete(array.get(bt_last, 0))
        array.set(bt_last, 0, label.new(bar_index, bull ? low : high, "Not counted: " + why + "\\n" + head + tag,
             style=bull ? label.style_label_up : label.style_label_down, color=color.new(color.gray, 35),
             textcolor=color.white, size=size.small))
    if tf_ok and on and cls_ok and time >= bt_from
        if bt_latest
            label.delete(array.get(bt_last, 0))
        array.set(bt_last, 0, label.new(bar_index, bull ? low : high, "H4 aligned - Alert\\n" + head + tag + (bt_weekly and bo_wk_rel == "against" ? "\\nWeekly AGAINST" : ""),
             style=bull ? label.style_label_up : label.style_label_down, color=bull ? bt_buy_col : bt_sell_col,
             textcolor=color.white, size=kind == 0 ? size.normal : size.small,
             tooltip=array.get(BT_NAMES, kind) + " @ " + str.tostring(h4lvl, format.mintick)
             + (note == "" ? "" : "\\n" + note) + "\\nDaily breakout @ " + str.tostring(dlvl, format.mintick)
             + "\\nConfirmed at this candle's close: " + str.tostring(close, format.mintick)
             + "\\nEntry = next candle's open"))
        array.set(bt_cnt, kind, array.get(bt_cnt, kind) + 1)
        array.set(bt_cnt, bull ? 8 : 9, array.get(bt_cnt, bull ? 8 : 9) + 1)
    tf_ok and on and cls_ok and time >= bt_from

// Weekly context sent with every bias alert (empty when there is no Weekly setup)
f_wk() =>
''')

# ── Backtest-only rules (being tried out before they go live) ─────────────────
# 1. Daily V-shapes (A-shapes for sells) beyond the Daily Breaker = formed in the
#    move after the breakout. (One beyond the Breaker that formed BEFORE the
#    breakout has already been closed through on the way there, so it is dead.)
rep('''// ── Post-breakout OC tracking ─''', '''// Daily V-shapes (A-shapes for sells) beyond the Daily Breaker: formed in the move
// after the breakout. Deepest one this H4 candle touches exactly and holds.
f_pv_pick(array<float> lv, bool bull, float b_lo, float b_hi, float t) =>
    float best = na
    if array.size(lv) > 0
        for i = 0 to array.size(lv) - 1
            float L = array.get(lv, i)
            bool beyond  = bull ? L > b_hi : L < b_lo
            bool touched = low <= L and high >= L
            bool held    = bull ? close >= L - t : close <= L + t
            if beyond and touched and held and (na(best) or (bull ? L < best : L > best))
                best := L
    best

// ── Post-breakout OC tracking ─''')
rep('''    bool ir_zone = not na(ir_hit)
''', '''    bool ir_zone = not na(ir_hit)

    // ── Zone 4 (backtest): Daily V/A-shape after the breakout ─────────────
    float pv_hit  = f_pv_pick(bo_dir == "bullish" ? d_vs : d_as, bo_dir == "bullish", band_lo, band_hi, tol)
    bool  pv_zone = not na(pv_hit)
''')
rep('''        else if retest_src == "inside_range"
            failed := bo_dir == "bullish" ? close < retest_lvl - tol : close > retest_lvl + tol
''', '''        else if retest_src == "inside_range"
            failed := bo_dir == "bullish" ? close < retest_lvl - tol : close > retest_lvl + tol
        else if retest_src == "post_breakout_v"
            failed := bo_dir == "bullish" ? close < retest_lvl - tol : close > retest_lvl + tol
''')
# 2. Daily reactions are watched all the time (also while H4 is aligned after the Origin)
rep('''    if not retest_on and (not h4_bo_fired or not h4_aligned)
''', '''    if not retest_on
''')
rep('''        else if db_zone and was_est
''', '''        else if pv_zone and was_est
            retest_on  := true
            retest_bar := bar_index
            retest_src := "post_breakout_v"
            retest_lvl := pv_hit
            if na(anchor_lvl) or math.abs(anchor_lvl - pv_hit) > pip * 0.1
                anchor_lvl := pv_hit
                anchor_bar := bar_index
        else if db_zone and was_est
''')
rep('''        float src_lvl = na(retest_lvl) ? bo_level : retest_lvl
''', '''        float src_lvl = na(retest_lvl) ? bo_level : retest_lvl
        bool  bt_was_aligned = h4_bo_fired and h4_aligned   // a fresh Daily reaction while H4 is still aligned
''')
# 4. External / Internal against the reaction's OWN External level. When a reaction
#    starts, the latest H4 A (V for sells) is its External level. A close beyond it
#    is an External breakout, even if newer (Internal) A/V-shapes formed during the
#    pullback. A close beyond a newer A/V only is Internal, and with Internal off it
#    does NOT use up the reaction: the script keeps waiting for the External one.
#    The External level is set at the FIRST H4 touch of a Daily level (see 6).
for v in ("pb_hit", "pv_hit", "bo_level", "ir_hit"):
    rep(f'''            if na(anchor_lvl) or math.abs(anchor_lvl - {v}) > pip * 0.1
                anchor_lvl := {v}
                anchor_bar := bar_index
''', f'''            if na(anchor_lvl)   // backtest: normally set by the first-touch scan below
                anchor_lvl := {v}
                anchor_bar := bar_index
                bt_ext_a   := h4_a_lvl
                bt_ext_v   := h4_v_lvl
''')
# Out-of-line status label names the External level awaited
rep('''" · waiting for H4 to break " + bo_dir
''', '''" · waiting for H4 External breakout " + (bo_dir == "bullish" ? "above " + str.tostring(bt_ext_a, format.mintick) : "below " + str.tostring(bt_ext_v, format.mintick))
''')
rep('''        if bo_dir == "bullish" and not na(h4_a_lvl) and not new_a and close > h4_a_lvl
            string h4_cls = h4a_origin <= anchor_bar ? "external" : "internal"
''', '''        bool bt_xb = not na(bt_ext_a) and close > bt_ext_a                      // External level broken
        bool bt_lb = not na(h4_a_lvl) and not new_a and close > h4_a_lvl       // latest A broken
        if bo_dir == "bullish" and (bt_xb or (bt_lb and (h4a_origin <= anchor_bar or bt_int)))
            string h4_cls = (bt_xb or h4a_origin <= anchor_bar) ? "external" : "internal"
            float  bt_brk = bt_xb ? bt_ext_a : h4_a_lvl
''')
rep('''        if bo_dir == "bearish" and not na(h4_v_lvl) and not new_v and close < h4_v_lvl
            string h4_cls = h4v_origin <= anchor_bar ? "external" : "internal"
''', '''        bool bt_xs = not na(bt_ext_v) and close < bt_ext_v
        bool bt_ls = not na(h4_v_lvl) and not new_v and close < h4_v_lvl
        if bo_dir == "bearish" and (bt_xs or (bt_ls and (h4v_origin <= anchor_bar or bt_int)))
            string h4_cls = (bt_xs or h4v_origin <= anchor_bar) ? "external" : "internal"
            float  bt_brkv = bt_xs ? bt_ext_v : h4_v_lvl
''')
rep('''                h4_breaker_lvl        := h4_a_lvl
''', '''                h4_breaker_lvl        := bt_brk
''', n=2)
rep('''                h4_breaker_lvl        := h4_v_lvl
''', '''                h4_breaker_lvl        := bt_brkv
''', n=2)

# Status label: while H4 is aligned, show the Daily reaction and the H4 level awaited
rep('''    _state_txt := "CONFIRMED | " + bo_dir + " | H4 aligned"
''', '''    _state_txt := "CONFIRMED | " + bo_dir + " | H4 aligned" + (retest_on ? "\\nDaily reaction at " + f_bt_src(retest_src) + " @ " + str.tostring(retest_lvl, format.mintick) + " · waiting for H4 External breakout " + (bo_dir == "bullish" ? "above " + str.tostring(bt_ext_a, format.mintick) : "below " + str.tostring(bt_ext_v, format.mintick)) : "")
''')

# each fresh reaction after a confirmation starts its own External / Internal check
rep('''                          alert.freq_once_per_bar)
            retest_on  := false
            retest_src := na
            retest_lvl := na
''', '''                          alert.freq_once_per_bar)
            retest_on  := false
            retest_src := na
            retest_lvl := na
            anchor_lvl := na
''', n=2)

ALERT = "                if barstate.isrealtime\n                    alert(f_hdrw("
NOTE = '"Daily reaction: " + f_bt_src(retest_src) + " @ " + str.tostring(src_lvl, format.mintick)'
for d, lvl in (("bullish", "h4_a_lvl"), ("bearish", "h4_v_lvl")):
    bull = "true" if d == "bullish" else "false"
    brk = "bt_brk" if d == "bullish" else "bt_brkv"
    rep(f'''{ALERT}"CONFIRMED")
                          + '","direction":"{d}","source":"' + retest_src''',
        f'''                f_btlbl({bull}, 0, h4_cls, {brk}, bo_level, {NOTE})
{ALERT}"CONFIRMED")
                          + '","direction":"{d}","source":"' + retest_src''')
    rep(f'''{ALERT}"H4_CONTINUATION")
                          + '","direction":"{d}","cont_type":"breakout_cont"''',
        f'''                f_btlbl({bull}, bt_was_aligned ? 7 : 1, h4_cls, {brk}, bo_level, {NOTE})
{ALERT}"H4_CONTINUATION")
                          + '","direction":"{d}","cont_type":"breakout_cont"''')

rep(f'''{ALERT}"H4_CONTINUATION")
                          + '","direction":"' + bo_dir + '","cont_type":"inline_break"\'''',
    f'''                f_btlbl(ilb, 2, "", brk_lvl, bo_level, "")
{ALERT}"H4_CONTINUATION")
                          + '","direction":"' + bo_dir + '","cont_type":"inline_break"\'''')

rep('''                    if barstate.isrealtime
                        alert(f_hdrw("H4_CONTINUATION")
                              + '","direction":"' + bo_dir + '","cont_type":"' + bk_type + '"\'''',
    '''                    f_btlbl(bo_dir == "bullish", bk_type == "breaker_origin" ? 3 : 4, "", h4_breaker_lvl, bo_level, "")
                    if barstate.isrealtime
                        alert(f_hdrw("H4_CONTINUATION")
                              + '","direction":"' + bo_dir + '","cont_type":"' + bk_type + '"\'''')

rep('''    if not na(oc_hit) and barstate.isrealtime
''', '''    if not na(oc_hit)
        f_btlbl(ocb, 5, "", oc_hit, bo_level, "")
    if not na(oc_hit) and barstate.isrealtime
''')

rep('''        if eng and barstate.isrealtime
''', '''        if eng and (bt_eng_mode == "Both" or (bt_eng_mode == "Wick") == eng_wick)
            f_btlbl(ocb, 6, "", eng_wick ? (ocb ? high[1] : low[1]) : open[1], bo_level, eng_wick ? "Covers the previous candle's wick" : "Covers the previous candle's body only")
        if eng and barstate.isrealtime
''')

# 6. The touch that matters is the FIRST H4 touch of a Daily level after that level
#    formed (a level only exists once its Daily candle has closed). External = the
#    closest H4 A (V for sells) formed before that first touch; everything formed
#    after it is Internal. A first touch of a NEW level starts a new check, even
#    while price is already reacting at another level.
rep('''// ── Post-breakout OC tracking ─''', '''f_bt_seen(float L) =>
    bool found = false
    for x in bt_seen
        if math.abs(x - L) <= pip * 0.1
            found := true
    found

// ── Post-breakout OC tracking ─''')
rep('''    // ── RETEST_CANCELLED — only when the reaction FAILS ───────────────────
''', '''    // ── Backtest: first H4 touch of each Daily level since it formed ──────
    bool bt_bull = bo_dir == "bullish"
    array<float> bt_cand = array.new<float>()
    array.push(bt_cand, bo_level)
    for L in pb_ocs
        array.push(bt_cand, L)
    array<float> bt_shp = bt_bull ? d_vs : d_as
    array<float> bt_ocl = bt_bull ? d_boc : d_soc
    for L in bt_shp
        array.push(bt_cand, L)
    for L in bt_ocl
        array.push(bt_cand, L)
    bool bt_first = false
    for L in bt_cand
        bool bt_held = bt_bull ? close >= L - tol : close <= L + tol
        if low <= L and high >= L and bt_held and not f_bt_seen(L)
            array.push(bt_seen, L)
            bt_first := true
    if array.size(bt_seen) > 300
        array.shift(bt_seen)
    if bt_first
        anchor_bar := bar_index
        bt_ext_a   := h4_a_lvl
        bt_ext_v   := h4_v_lvl

    // ── RETEST_CANCELLED — only when the reaction FAILS ───────────────────
''')

# Weekly display follows the backtest's Weekly switch
rep('    if show_wk_lbls and show_wk_on_tf and not na(wk_dir)', '    if bt_weekly and show_wk_lbls and show_wk_on_tf and not na(wk_dir)')
rep('    if show_wk_ext and show_wk_on_tf and not na(w_cdir) and w_cdir != "none"',
    '    if bt_weekly and show_wk_ext and show_wk_on_tf and not na(w_cdir) and w_cdir != "none"')
rep('string _wk_txt = na(wk_dir) ? "" :', 'string _wk_txt = not bt_weekly or na(wk_dir) ? "" :')

s = s.rstrip('\n') + '''

// ── Backtest count ────────────────────────────────────────────────────────────
var table bt_tbl = table.new(position.top_right, 2, 12, bgcolor=color.new(#0F1120, 10), border_width=1, border_color=color.new(color.gray, 70))
if bt_table and barstate.islast and timeframe.period != "240"
    table.cell(bt_tbl, 0, 0, "Backtest labels show on the 4H chart only", text_color=color.white, text_size=size.small)
if bt_table and barstate.islast and timeframe.period == "240"
    int bt_total = array.get(bt_cnt, 8) + array.get(bt_cnt, 9)
    table.cell(bt_tbl, 0, 0, "H4 aligned alerts", text_color=color.white, text_size=size.small)
    table.cell(bt_tbl, 1, 0, str.tostring(bt_total), text_color=color.white, text_size=size.small)
    for i = 0 to 7
        table.cell(bt_tbl, 0, i + 1, array.get(BT_NAMES, i), text_color=color.silver, text_size=size.tiny)
        table.cell(bt_tbl, 1, i + 1, str.tostring(array.get(bt_cnt, i)), text_color=color.silver, text_size=size.tiny)
    table.cell(bt_tbl, 0, 9, "Buys", text_color=bt_buy_col, text_size=size.small)
    table.cell(bt_tbl, 1, 9, str.tostring(array.get(bt_cnt, 8)), text_color=bt_buy_col, text_size=size.small)
    table.cell(bt_tbl, 0, 10, "Sells", text_color=bt_sell_col, text_size=size.small)
    table.cell(bt_tbl, 1, 10, str.tostring(array.get(bt_cnt, 9)), text_color=bt_sell_col, text_size=size.small)
    table.cell(bt_tbl, 0, 11, "Since", text_color=color.gray, text_size=size.tiny)
    table.cell(bt_tbl, 1, 11, str.format_time(math.max(bt_from, bt_t0), "dd MMM yyyy"), text_color=color.gray, text_size=size.tiny)
'''
s = s.rstrip('\n') + '''

// ── Backtest: the Daily reaction levels being watched right now ──────────────
var array<line>  bt_lv_lines = array.new<line>()
var array<label> bt_lv_lbls  = array.new<label>()
f_bt_lv(float y, string txt) =>
    if not na(y) and array.size(bt_lv_lines) < 30
        array.push(bt_lv_lines, line.new(bar_index - 40, y, bar_index + 3, y, color=color.new(color.aqua, 25), style=line.style_dotted))
        array.push(bt_lv_lbls, label.new(bar_index + 3, y, txt + "  " + str.tostring(y, format.mintick),
             style=label.style_label_left, color=color.new(color.black, 100), textcolor=color.aqua, size=size.small))
if barstate.islast
    for ln in bt_lv_lines
        line.delete(ln)
    for lb in bt_lv_lbls
        label.delete(lb)
    array.clear(bt_lv_lines)
    array.clear(bt_lv_lbls)
    if bt_lvls and timeframe.period == "240" and not na(bo_dir) and not na(bo_level)
        bool bb = bo_dir == "bullish"
        f_bt_lv(bo_level, "Daily Breaker")
        for L in pb_ocs
            f_bt_lv(L, "Daily OC after the breakout")
        array<float> shp = bb ? d_vs : d_as
        for L in shp
            if bb ? L > bo_level + tol : L < bo_level - tol
                f_bt_lv(L, bb ? "Daily V-shape after the breakout" : "Daily A-shape after the breakout")
            else if not na(bo_opp) and (bb ? (L > bo_opp and L < bo_level - tol) : (L < bo_opp and L > bo_level + tol))
                f_bt_lv(L, bb ? "Daily V-shape inside the range" : "Daily A-shape inside the range")
        array<float> ocs = bb ? d_boc : d_soc
        for L in ocs
            if not na(bo_opp) and (bb ? (L > bo_opp and L < bo_level - tol) : (L < bo_opp and L > bo_level + tol))
                f_bt_lv(L, "Daily OC inside the range")
'''
open(os.path.join(R, 'MummyTKT_BiasPointer_Backtest.pine'), 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
