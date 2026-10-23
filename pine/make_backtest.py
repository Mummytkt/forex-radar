# Builds MummyTKT_BiasPointer_Backtest.pine from the live script. Re-run after every live Pine change:
#   python pine/make_backtest.py
#
# Since v7 (2026-10-23) the live script IS the backtest logic (labels, count table,
# levels-watched lines all included and switchable). The backtest copy only gets
# its own name so both can sit on one chart; it sends no alerts unless one is created.
import os

R = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(R, 'MummyTKT_BiasPointer.pine'), encoding='utf-8').read()

a = 'indicator("MummyTKT Bias Pointer", overlay=true'
assert s.count(a) == 1
s = s.replace(a, 'indicator("MummyTKT Bias Pointer — Backtest", overlay=true')
open(os.path.join(R, 'MummyTKT_BiasPointer_Backtest.pine'), 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
