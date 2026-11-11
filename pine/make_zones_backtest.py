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
    'var array<float> zb_lv = array.from(0.0)   // the level it broke (its structure line)\n'
    'f_al(bool on, string ev, string txt, int dir, float lvl, bool with_, string ab) =>\n    if on\n'
    '        array.set(zb_ev, 0, dir)\n'
    '        array.set(zb_lv, 0, lvl)\n')
# no tables in the backtest copy (user, 2026-11-11: lighter): their settings, the tables and their drawing go
L = s.split('\n')
TBL_IN = ('bool   sk_on ', 'string sk_pos ', 'int    sk_n ', 'color  sk_bg ', 'color  sk_tx ', 'bool   tb_on ', 'string tb_pos ',
          'color  tb_bg ', 'color  tb_tx ', 'bool   ky_on ', 'string ky_pos ')
n0 = len(L)
L = [l for l in L if not l.startswith(TBL_IN)]
assert n0 - len(L) == len(TBL_IN), n0 - len(L)
a = L.index('var table sk = table.new(f_tpos(sk_pos), 2, 11, bgcolor = sk_bg, border_width = 1, border_color = color.new(color.gray, 75))')
b = next(k for k in range(a, len(L)) if L[k].startswith('    table.cell(tb, 1, r, b,'))
del L[a:b + 1]
c = L.index('    // the story table and the status table (one table per corner: in the same corner the story goes under the status)')
L = L[:c]
s = '\n'.join(L)
assert 'table.' not in s and 'f_row(' not in s and 'f_key(' not in s, 'a table is left'
s = s.replace('const string G_ST = "2 · Story notes and tables"', 'const string G_ST = "2 · Story notes"')
s = s.replace('"Short tags (abbreviations, explained in the key table)"', '"Short tags (abbreviations)"')
s = s.rstrip('\n') + '\n' + layer
open(os.path.join(R, 'MummyTKT_ZonesBacktest.pine'), 'w', encoding='utf-8', newline='\n').write(s)
print('ok', s.count('\n'), 'lines')
