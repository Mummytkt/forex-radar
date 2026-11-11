# Builds MummyTKT_ZonesBacktest.pine from the live Bias Pointer + zones_layer.pine. Re-run after every
# live Pine change (or a zones_layer change):
#   python pine/make_zones_backtest.py
#
# The copy keeps the live story and alerts exactly; every alert it would send (any kind) starts the zones
# instead. It never sends the Bias Pointer's webhooks (al_ok is off), and it calculates every candle.
import os

R = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(R, 'MummyTKT_BiasPointer.pine'), encoding='utf-8').read()
layer = open(os.path.join(R, 'zones_layer.pine'), encoding='utf-8').read()


def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)


rep('indicator("MummyTKT Bias Pointer", overlay = true, calc_bars_count = 3000, behind_chart = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 100, max_bars_back = 5000)',
    'indicator("MummyTKT Zones Backtest", overlay = true, behind_chart = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 500, max_bars_back = 2000)')  # 2000 = the most the story looks back (f_bt); less memory
rep('// MummyTKT\'s Bias Pointer v14: the MTF Storyline with alerts · 2026-11-04\n',
    '// MummyTKT\'s Zones Backtest (2026-11-10): the Bias Pointer v14 story + the BUY / SELL zones after every\n'
    '// alert and a backtest of trading them (section 9 at the end). Built by pine/make_zones_backtest.py.\n'
    '// Put it on the H4 chart (it reads M5, M15 and H1 inside each H4 candle). It sends no webhooks.\n//\n')
rep('bool al_ok = T1 == "D" and T2 == "240" and timeframe.period == "240"',
    'bool al_ok = false   // the backtest copy never sends the Bias Pointer\'s webhooks')
rep('f_al(bool on, string ev, string txt, int dir, float lvl, bool with_, string ab) =>\n    if on\n',
    '// every alert (any kind) starts the zones backtest: its direction, read at the end of the candle\n'
    'var array<int> zb_ev = array.from(0)\n'
    'f_al(bool on, string ev, string txt, int dir, float lvl, bool with_, string ab) =>\n    if on\n'
    '        array.set(zb_ev, 0, dir)\n')
# the results table needs a corner: the key and story tables start off (switchable)
rep('bool   ky_on    = input.bool(true, "Key table"', 'bool   ky_on    = input.bool(false, "Key table"')
rep('bool   sk_on    = input.bool(true, "Story table"', 'bool   sk_on    = input.bool(false, "Story table"')
rep('bool   tb_on    = input.bool(true, "Status table"', 'bool   tb_on    = input.bool(false, "Status table"')
s = s.rstrip('\n') + '\n' + layer
open(os.path.join(R, 'MummyTKT_ZonesBacktest.pine'), 'w', encoding='utf-8', newline='\n').write(s)
print('ok', s.count('\n'), 'lines')
