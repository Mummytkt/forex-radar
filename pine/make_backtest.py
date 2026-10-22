# Builds MummyTKT_BiasPointer_Backtest.pine from the live script. Re-run after every live Pine change:
#   python pine/make_backtest.py
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
// Same logic as the live alert script, line for line. Wherever the live script
// sends a bias alert, this one puts an "H4 aligned - Alert" label on that H4
// candle, filtered the way Alert Filters filter Telegram (defaults = defaults):
//   Origin (BUY / SELL CONFIRMED)   External on, Internal off
//   H4 back in line                 External on, Internal off
//   H4 breakout in line, Breaker Origin / retest, OC reaction, Engulfing (wick)
// A third line "Weekly AGAINST" marks alerts that went against the Weekly.
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
bool   bt_ext      = input.bool(true,  "External H4 breakouts (Origin / back in line)", group=GBT)
bool   bt_int      = input.bool(false, "Internal H4 breakouts (Origin / back in line)", group=GBT)
bool   bt_origin   = input.bool(true,  "Origin — BUY / SELL CONFIRMED", group=GBT)
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
color  bt_buy_col  = input.color(#00C853, "Buy label", group=GBT, inline="btc")
color  bt_sell_col = input.color(#FF1744, "Sell label", group=GBT, inline="btc")
// counts: 0 Origin, 1 Back in line, 2 In line, 3 Breaker Origin, 4 Breaker retest, 5 OC, 6 Engulfing, 7 Buys, 8 Sells
var bt_cnt  = array.new_int(9, 0)
var int bt_t0 = time
// External / Internal of the setup's latest H4 confirmation (Origin or back in line);
// continuations follow it, like the server: Internal off = no continuations of Internal setups
var bt_scls = array.from("")
var bt_last = array.new<label>(1, na)   // the alert label currently on the chart
var BT_NAMES = array.from("Origin", "Back in line", "H4 breakout in line", "Breaker Origin", "Breaker retest", "OC reaction", "Engulfing")''')

# Label function: after f_wk(), so it can read the Weekly relation
rep('''    h4_brk_lvl            := na
    bo_wk_rel := ""
''', '''    h4_brk_lvl            := na
    array.set(bt_scls, 0, "")
    bo_wk_rel := ""
''')
rep('''// Weekly context sent with every bias alert (empty when there is no Weekly setup)
f_wk() =>
''', '''// Backtest: label where an alert is sent (returns true if labelled)
f_btlbl(bool bull, int kind, string cls, float h4lvl, float dlvl, string note) =>
    bool on = kind == 0 ? bt_origin : kind == 1 ? bt_realign : kind == 2 ? bt_inline : kind <= 4 ? bt_breaker : kind == 5 ? bt_oc : bt_engulf
    if kind <= 1
        array.set(bt_scls, 0, cls)
    string c = array.get(bt_scls, 0)
    bool cls_ok = c == "" or (c == "external" ? bt_ext : bt_int)
    string head = kind == 0 ? (bull ? "BUY CONFIRMED" : "SELL CONFIRMED") : (bull ? "BUY" : "SELL") + " · " + array.get(BT_NAMES, kind)
    string tag  = c == "" ? "" : kind <= 1 ? (c == "external" ? " (External)" : " (Internal)") : (c == "external" ? " (External setup)" : " (Internal setup)")
    if bt_grey and not (on and cls_ok and time >= bt_from)
        string why = time < bt_from ? "before the backtest start" : not cls_ok ? "Internal is switched off" : "this type is switched off"
        if bt_latest
            label.delete(array.get(bt_last, 0))
        array.set(bt_last, 0, label.new(bar_index, bull ? low : high, "Not counted: " + why + "\\n" + head + tag,
             style=bull ? label.style_label_up : label.style_label_down, color=color.new(color.gray, 35),
             textcolor=color.white, size=size.small))
    if on and cls_ok and time >= bt_from
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
        array.set(bt_cnt, bull ? 7 : 8, array.get(bt_cnt, bull ? 7 : 8) + 1)
    on and cls_ok and time >= bt_from

// Weekly context sent with every bias alert (empty when there is no Weekly setup)
f_wk() =>
''')

ALERT = "                if barstate.isrealtime\n                    alert(f_hdrw("
for d, lvl in (("bullish", "h4_a_lvl"), ("bearish", "h4_v_lvl")):
    bull = "true" if d == "bullish" else "false"
    rep(f'''{ALERT}"CONFIRMED")
                          + '","direction":"{d}","source":"' + retest_src''',
        f'''                f_btlbl({bull}, 0, h4_cls, {lvl}, bo_level, "Daily reaction: " + (na(retest_src) ? "-" : retest_src) + " @ " + str.tostring(src_lvl, format.mintick))
{ALERT}"CONFIRMED")
                          + '","direction":"{d}","source":"' + retest_src''')
    rep(f'''{ALERT}"H4_CONTINUATION")
                          + '","direction":"{d}","cont_type":"breakout_cont"''',
        f'''                f_btlbl({bull}, 1, h4_cls, {lvl}, bo_level, "Daily reaction: " + (na(retest_src) ? "-" : retest_src) + " @ " + str.tostring(src_lvl, format.mintick))
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

# Weekly display follows the backtest's Weekly switch
rep('    if show_wk_lbls and show_wk_on_tf and not na(wk_dir)', '    if bt_weekly and show_wk_lbls and show_wk_on_tf and not na(wk_dir)')
rep('    if show_wk_ext and show_wk_on_tf and not na(w_cdir) and w_cdir != "none"',
    '    if bt_weekly and show_wk_ext and show_wk_on_tf and not na(w_cdir) and w_cdir != "none"')
rep('string _wk_txt = na(wk_dir) ? "" :', 'string _wk_txt = not bt_weekly or na(wk_dir) ? "" :')

s = s.rstrip('\n') + '''

// ── Backtest count ────────────────────────────────────────────────────────────
var table bt_tbl = table.new(position.top_right, 2, 11, bgcolor=color.new(#0F1120, 10), border_width=1, border_color=color.new(color.gray, 70))
if bt_table and barstate.islast
    int bt_total = array.get(bt_cnt, 7) + array.get(bt_cnt, 8)
    table.cell(bt_tbl, 0, 0, "H4 aligned alerts", text_color=color.white, text_size=size.small)
    table.cell(bt_tbl, 1, 0, str.tostring(bt_total), text_color=color.white, text_size=size.small)
    for i = 0 to 6
        table.cell(bt_tbl, 0, i + 1, array.get(BT_NAMES, i), text_color=color.silver, text_size=size.tiny)
        table.cell(bt_tbl, 1, i + 1, str.tostring(array.get(bt_cnt, i)), text_color=color.silver, text_size=size.tiny)
    table.cell(bt_tbl, 0, 8, "Buys", text_color=bt_buy_col, text_size=size.small)
    table.cell(bt_tbl, 1, 8, str.tostring(array.get(bt_cnt, 7)), text_color=bt_buy_col, text_size=size.small)
    table.cell(bt_tbl, 0, 9, "Sells", text_color=bt_sell_col, text_size=size.small)
    table.cell(bt_tbl, 1, 9, str.tostring(array.get(bt_cnt, 8)), text_color=bt_sell_col, text_size=size.small)
    table.cell(bt_tbl, 0, 10, "Since", text_color=color.gray, text_size=size.tiny)
    table.cell(bt_tbl, 1, 10, str.format_time(math.max(bt_from, bt_t0), "dd MMM yyyy"), text_color=color.gray, text_size=size.tiny)
'''
open(os.path.join(R, 'MummyTKT_BiasPointer_Backtest.pine'), 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
