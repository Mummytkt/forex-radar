"""Builds the MERGE TEST (user, 2026-10-31) as TWO scripts on the same 4H chart (one script would be
117,359 compiled tokens; TradingView's limit is 100,256 and the Bias Pointer alone is ~92,000):

  MummyTKT_BiasPointer_MergeTEST.pine  the live Bias Pointer exactly as it is + the 4 choices, which
                                       switch its own steps off where the Aligned way replaces them.
  MummyTKT_AlignedCompanion_TEST.pine  the Aligned Story features (merge_layer.pine) with the SAME 4
                                       choices, on a copy of the Bias Pointer's Daily engine.

  1. After a Daily breakout, watch: Bias Pointer post-breakout Daily levels | Aligned H4 continuations,
     then the Daily range levels after the pullback.
  2. Daily reaction + H4 breakout shows as: Bias Pointer CONFIRMED | Daily + H4 aligned.
  3. At the H4 levels confirm with: Bias Pointer H4 key-level reactions | M15 sweep and break.
  4. Alert: Daily pullback confirmed.
The live MummyTKT_BiasPointer.pine is not touched. Picture: Documents/Merged_Plan_*.png.
"""
import re

SRC = 'C:/Users/u/forex-radar/pine/MummyTKT_BiasPointer.pine'
OUT = 'C:/Users/u/forex-radar/pine/MummyTKT_BiasPointer_MergeTEST.pine'
OUT2 = 'C:/Users/u/forex-radar/pine/MummyTKT_AlignedCompanion_TEST.pine'
src = open(SRC, encoding='utf-8').read()
s = src


def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (a[:70], s.count(a))
    s = s.replace(a, b)


STY = 'options = ["Solid", "Dashed", "Dotted"]'
CHOICES = r'''string ag_daily = input.string("Bias Pointer: post-breakout Daily levels", "1. After a Daily breakout, watch",
     options = ["Bias Pointer: post-breakout Daily levels", "Aligned: H4 continuations, then the Daily range levels after the pullback"], group = G_AG,
     tooltip = "Set the SAME 4 choices in the Bias Pointer (Merge TEST) and the Aligned Companion. Bias Pointer: as now. Aligned: every H4 External break with the Daily is an H4 continuation until the Daily pulls back (an H4 close beyond the pullback line, the last H4 low); then the Daily range high (target), low and 0.5 and the Daily levels of the current leg inside it; their reaction + an H4 External breakout = aligned.")
string ag_conf  = input.string("Bias Pointer: CONFIRMED", "2. Daily reaction + H4 breakout shows as", options = ["Bias Pointer: CONFIRMED", "Aligned: Daily + H4 aligned"], group = G_AG)
string ag_h4    = input.string("Bias Pointer: H4 key-level reactions", "3. At the H4 levels, confirm with",
     options = ["Bias Pointer: H4 key-level reactions", "Aligned: M15 sweep and break"], group = G_AG,
     tooltip = "Bias Pointer: H4 Breaker, OC, engulfing, H4 FVG alerts (as now). Aligned: an M15 candle sweeps an H4 level (wick through, close back) and price closes beyond the last M15 high (sells: low) = M15 entry confirmed (shown by the Aligned Companion).")
bool   ag_pb_al = input.bool(true, "4. Alert: Daily pullback confirmed (sent by the Aligned Companion)", group = G_AG)
color  ag_alb   = input.color(#00C853, "Aligned tag · buys", group = G_AG, inline = "tg")
color  ag_als   = input.color(#FF1744, "sells", group = G_AG, inline = "tg")
bool AG_D = ag_daily != "Bias Pointer: post-breakout Daily levels"
bool AG_C = ag_conf != "Bias Pointer: CONFIRMED"
bool AG_H = ag_h4 != "Bias Pointer: H4 key-level reactions"
'''

# ── 1. the Bias Pointer with the choices ──
rep('indicator("MummyTKT Bias Pointer",', 'indicator("MummyTKT Bias Pointer — Merge TEST",')
for nm in ("bt_origin", "bt_react", "bt_realign", "bt_inline", "bt_lvls", "bt_breaker", "bt_oc", "bt_engulf", "bt_h4fvg"):
    s, k = re.subn(r"^bool(\s+)" + nm + r"(\s*)=", r"bool\g<1>" + nm + r"_in\g<2>=", s, count=1, flags=re.M)
    assert k == 1, nm
rep('// counts: 0 Origin, 1 Back in line,', '''// ── MERGE TEST: how each step runs (the Aligned Companion shows / alerts the Aligned ones) ──
const string G_AG = "11 · Aligned Story: choose how each step runs"
''' + CHOICES + '''// The choices switch the Bias Pointer's own steps off where the Aligned way replaces them
bool bt_origin  = bt_origin_in and not AG_D
bool bt_react   = bt_react_in and not AG_D
bool bt_realign = bt_realign_in and not AG_D
bool bt_inline  = bt_inline_in and not AG_D
bool bt_lvls    = bt_lvls_in and not AG_D
bool bt_breaker = bt_breaker_in and not AG_H
bool bt_oc      = bt_oc_in and not AG_H
bool bt_engulf  = bt_engulf_in and not AG_H
bool bt_h4fvg   = bt_h4fvg_in and not AG_H

// counts: 0 Origin, 1 Back in line,''')
rep('''kind == 0 ? (bull ? "BUY CONFIRMED" : "SELL CONFIRMED") : (bull ? "BUY" : "SELL") + " · " + array.get(BT_NAMES, kind)''',
    '''AG_C and (kind == 0 or kind == 7) ? "Daily + H4 aligned (" + (bull ? "buys" : "sells") + ")" : kind == 0 ? (bull ? "BUY CONFIRMED" : "SELL CONFIRMED") : (bull ? "BUY" : "SELL") + " · " + array.get(BT_NAMES, kind)''')
rep('''            color  acol = kind >= 10 ? bt_h4fvg_col : bull ? bt_buy_col : bt_sell_col''',
    '''            color  acol = AG_C and (kind == 0 or kind == 7) ? (bull ? ag_alb : ag_als) : kind >= 10 ? bt_h4fvg_col : bull ? bt_buy_col : bt_sell_col''')
open(OUT, 'w', encoding='utf-8', newline='\n').write(s)
print(OUT, s.count('\n'), 'lines')

# ── 2. the Aligned Companion ──
lines = src.split('\n')
a = next(i for i, l in enumerate(lines) if l.startswith('// High / low of the daily candle'))
b = next(i for i, l in enumerate(lines) if l.startswith('[s_cdir, s_chi'))
ENGINE = '\n'.join(lines[a:b]).rstrip() + '\n'
SEC = '\n'.join(lines[b:b + 3]) + '\n'
assert 'request.security' in SEC
LAYER = open('C:/Users/u/forex-radar/pine/merge_layer.pine', encoding='utf-8').read()
HEAD = r'''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// MummyTKT — Aligned Companion (MERGE TEST) · 2026-10-31
// Runs next to "MummyTKT Bias Pointer — Merge TEST" on the 4H chart. Set the SAME 4 choices in both.
// It shows (and alerts) the Aligned Story parts you choose: H4 continuations + the pullback line,
// Daily pullback confirmed + range high / low / 0.5 + the Daily levels of the current leg (merged
// names, demand / supply), Daily + H4 aligned, and M15 sweep and break entries at the H4 levels.
// The Daily breakout is the Bias Pointer's (a copy of its Daily engine, same "Daily levels from").
// ─────────────────────────────────────────────────────────────────────────────
indicator("MummyTKT — Aligned Companion (Merge TEST)", overlay = true, behind_chart = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 300, max_bars_back = 2000, calc_bars_count = 3000)

const string G_AG  = "1 · Aligned Story: choose how each step runs (same as in the Bias Pointer)"
const string G_AGL = "2 · Lines, levels, tags"
string wh_secret = input.string("", "Webhook Secret (as in the Bias Pointer)", group = G_AG)
bool   d_body    = input.string("Body", "Daily levels from (as in the Bias Pointer)", options = ["Body", "Wick"], group = G_AG) == "Body"
''' + CHOICES + r'''int    ag_win   = input.int(20, "M15 candles from the sweep to the break", minval = 1, maxval = 100, group = G_AG)
int    ag_frn   = input.int(2, "M15 fractal: candles each side", minval = 1, maxval = 5, group = G_AG)
bool   ag_zone  = input.bool(true, "Demand / supply as reaction levels", group = G_AGL, inline = "z")
bool   ag_merge = input.bool(true, "Levels on the same price show as one", group = G_AGL, inline = "z")
color  ag_tl_c  = input.color(#29B6F6, "Pullback line", group = G_AGL, inline = "tl")
string ag_tl_s  = input.string("Solid", "", ''' + STY + ''', group = G_AGL, inline = "tl")
int    ag_tl_w  = input.int(2, "", minval = 1, maxval = 4, group = G_AGL, inline = "tl")
color  ag_rg_c  = input.color(#E0E0E0, "Daily range", group = G_AGL, inline = "rg")
string ag_rg_s  = input.string("Solid", "", ''' + STY + ''', group = G_AGL, inline = "rg")
color  ag_eq_c  = input.color(#9E9E9E, "0.5", group = G_AGL, inline = "rg")
string ag_eq_s  = input.string("Dashed", "", ''' + STY + ''', group = G_AGL, inline = "rg")
color  ag_hl_c  = input.color(#FFA726, "H4 range line", group = G_AGL, inline = "hl")
string ag_hl_s  = input.string("Solid", "", ''' + STY + ''', group = G_AGL, inline = "hl")
color  ag_cn_c  = input.color(#B39DDB, "H4 continuation lines", group = G_AGL, inline = "cn")
string ag_cn_s  = input.string("Dotted", "", ''' + STY + ''', group = G_AGL, inline = "cn")
color  ag_l1b   = input.color(#26A69A, "Daily levels · buys", group = G_AGL, inline = "l1")
color  ag_l1s   = input.color(#EF5350, "sells", group = G_AGL, inline = "l1")
color  ag_l2b   = input.color(#80CBC4, "H4 levels · buys", group = G_AGL, inline = "l2")
color  ag_l2s   = input.color(#EF9A9A, "sells", group = G_AGL, inline = "l2")
int    ag_op    = input.int(18, "Box opacity %", minval = 0, maxval = 100, group = G_AGL, inline = "bo")
int    ag_max   = input.int(10, "Most levels shown", minval = 1, maxval = 30, group = G_AGL, inline = "bo")
string ag_vs_s  = input.string("Solid", "V / A-shape line", ''' + STY + ''', group = G_AGL, inline = "ls")
string ag_oc_s  = input.string("Dashed", "OC", ''' + STY + ''', group = G_AGL, inline = "ls")
string ag_bk_s  = input.string("Dotted", "Breaker", ''' + STY + ''', group = G_AGL, inline = "ls")
color  ag_enc   = input.color(#7C4DFF, "M15 entry tag", group = G_AGL, inline = "te")
color  ag_tgx   = input.color(color.white, "tag text", group = G_AGL, inline = "te")
color  ag_lvx   = input.color(#E0E0E0, "Level label text", group = G_AGL, inline = "lx")
string ag_lvz   = input.string("Small", "size", options = ["Tiny", "Small", "Normal"], group = G_AGL, inline = "lx")

f_hdrw(string t) =>
    '{"secret":"' + wh_secret + '","type":"' + t + '","timeframe":"' + timeframe.period + '","exchange":"' + syminfo.prefix + '","instrument":"' + syminfo.ticker

'''
body = HEAD + ENGINE + '\n' + SEC + '\n' + LAYER
open(OUT2, 'w', encoding='utf-8', newline='\n').write(body)
print(OUT2, body.count('\n'), 'lines')
