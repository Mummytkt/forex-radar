"""Python port of the zones logic, run on real EURUSD H4 candles, to check against the user's 14 pictures.
Times printed in UTC+1 (the user's chart)."""
import json, datetime as dt, sys

H1 = json.load(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'eurusd_h1_dec2019_jan2020.json')))
# H4 candles open at 22:00 UTC + 4n (FOREXCOM, winter)
bars = {}
order = []
for ts, o, h, l, c in H1:
    t = dt.datetime.fromisoformat(ts)
    b = t - dt.timedelta(hours=(t.hour - 22) % 4)
    if b not in bars:
        bars[b] = [o, h, l, c]
        order.append(b)
    else:
        x = bars[b]
        x[1] = max(x[1], h); x[2] = min(x[2], l); x[3] = c
T = order
O = [bars[b][0] for b in T]; Hh = [bars[b][1] for b in T]; L = [bars[b][2] for b in T]; C = [bars[b][3] for b in T]


def lab(i):
    return (T[i] + dt.timedelta(hours=1)).strftime('%d%b %H:%M')


def zh(j, d): return Hh[j] if d > 0 else -L[j]
def zl(j, d): return L[j] if d > 0 else -Hh[j]
def zo(j, d): return d * O[j]
def zc(j, d): return d * C[j]


def ix(s):
    """index of the candle that opens at 'DDMon HH:MM' (UTC+1)"""
    for i in range(len(T)):
        if lab(i) == s:
            return i
    raise KeyError(s)


if __name__ == '__main__':
    a = ix(sys.argv[1]) if len(sys.argv) > 1 else 0
    b = ix(sys.argv[2]) if len(sys.argv) > 2 else len(T) - 1
    for i in range(a, b + 1):
        print(i, lab(i), f"O {O[i]:.5f} H {Hh[i]:.5f} L {L[i]:.5f} C {C[i]:.5f}", 'bull' if C[i] > O[i] else 'bear')
