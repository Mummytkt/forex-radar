"""Python copy of the Swing / Internal / Fractal engine in MummyTKT_Structure_3Types_TEST.pine.

Used to test the rules on a made-up chart and to draw the explanation picture
(structure_picture.svg). Same rules as the Pine script:
  Fractal: pivot high / low with `flen` candles each side. CHoCH = a WICK beyond the
           latest fractal high (low) that turns the fractal trend.
  Internal: i-BOS = a BODY close beyond the internal high / low. The forming high is
           fixed by a bearish CHoCH (the internal pullback has started); mirror for lows.
  Swing:   BOS = a BODY close beyond the swing high / low. The forming high is fixed by
           a bearish i-BOS (the swing pullback has started); mirror for lows.
  A break in the trend direction: the new strong point is the lowest low (buys) since
  the broken high = the low that caused the break. A close through the strong point
  flips the trend: the high that took out the strong low becomes the strong high.
"""


class Lvl:
    def __init__(self):
        self.dir = 0
        self.hi = self.lo = None
        self.hb = self.lb = None
        self.hf = self.lf = False


def lo_since(c, i, b):
    j = min(range(b, i + 1), key=lambda k: (c[k][2], -k))
    return c[j][2], j


def hi_since(c, i, b):
    j = max(range(b, i + 1), key=lambda k: (c[k][1], k))
    return c[j][1], j


def step(s, c, i, fixH, fixL):
    o, h, l, cl = c[i]
    ev, flip, bl, bp, np_, npb = 0, False, None, None, None, None
    if s.dir == 0:
        if fixL:
            s.dir = 1
            s.lo, s.lb = lo_since(c, i, max(0, i - 20)); s.lf = True
            s.hi, s.hb, s.hf = h, i, False
        elif fixH:
            s.dir = -1
            s.hi, s.hb = hi_since(c, i, max(0, i - 20)); s.hf = True
            s.lo, s.lb, s.lf = l, i, False
    elif s.dir == 1:
        if not s.hf and h >= s.hi:
            s.hi, s.hb = h, i
        if fixH:
            s.hf = True
        if cl < s.lo:
            ev, flip, bl, bp = -1, True, s.lo, s.lb
            m, mb = hi_since(c, i, s.lb)
            s.dir = -1
            s.hi, s.hb, s.hf = m, mb, True
            s.lo, s.lb, s.lf = l, i, False
            np_, npb = m, mb
        elif s.hf and cl > s.hi:
            ev, bl, bp = 1, s.hi, s.hb
            m, mb = lo_since(c, i, s.hb)
            s.lo, s.lb, s.lf = m, mb, True
            s.hi, s.hb, s.hf = h, i, False
            np_, npb = m, mb
    else:
        if not s.lf and l <= s.lo:
            s.lo, s.lb = l, i
        if fixL:
            s.lf = True
        if cl > s.hi:
            ev, flip, bl, bp = 1, True, s.hi, s.hb
            m, mb = lo_since(c, i, s.hb)
            s.dir = 1
            s.lo, s.lb, s.lf = m, mb, True
            s.hi, s.hb, s.hf = h, i, False
            np_, npb = m, mb
        elif s.lf and cl < s.lo:
            ev, bl, bp = -1, s.lo, s.lb
            m, mb = hi_since(c, i, s.lb)
            s.hi, s.hb, s.hf = m, mb, True
            s.lo, s.lb, s.lf = l, i, False
            np_, npb = m, mb
    return ev, flip, bl, bp, np_, npb


def poi(c, bull, pb):
    for j in range(4):
        k = pb - j
        if k < 0:
            break
        o, h, l, cl = c[k]
        if (cl < o) if bull else (cl > o):
            return h, l, k
    o, h, l, cl = c[pb]
    return h, l, pb


def run(c, flen=2):
    IN, SW = Lvl(), Lvl()
    fh = fl = None
    fhb = flb = None
    fhx = flx = True
    fdir = 0
    events = []
    for i in range(len(c)):
        p = i - flen
        if p - flen >= 0:
            if all(c[p][1] > c[k][1] for k in range(p - flen, p + flen + 1) if k != p):
                fh, fhb, fhx = c[p][1], p, False
            if all(c[p][2] < c[k][2] for k in range(p - flen, p + flen + 1) if k != p):
                fl, flb, flx = c[p][2], p, False
        ch = 0
        if not fhx and c[i][1] > fh:
            fhx = True
            if fdir != 1:
                fdir, ch = 1, 1
                events.append(('CH', 1, fh, fhb, i))
        if not flx and c[i][2] < fl:
            flx = True
            if fdir != -1:
                fdir, ch = -1, -1
                events.append(('CH', -1, fl, flb, i))
        iev = step(IN, c, i, ch == -1, ch == 1)
        if iev[0]:
            events.append(('i-BOS', iev[0], iev[2], iev[3], i, iev[1], iev[4], iev[5], poi(c, iev[0] == 1, iev[5])))
        sev = step(SW, c, i, iev[0] == -1, iev[0] == 1)
        if sev[0]:
            events.append(('BOS', sev[0], sev[2], sev[3], i, sev[1], sev[4], sev[5], poi(c, sev[0] == 1, sev[5])))
    return events, IN, SW
