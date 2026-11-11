from fx_sim import *  # the rules of zones_layer.pine in Python; run: python zones_rules.py  (expected output: see the 14 pictures, memory planned-zones-script)
KN = {0: 'V/A', 1: 'OC', 2: 'Breaker', 3: 'QM'}
import sys
TOL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
TICK = 0.00001; SCN = 3; QMS = 120

def levels(d, k, lvl, q0=None):
    """key levels of the break at k (flipped by d: buy levels below). returns (s, [lo,hi,t,kind])"""
    s = k; bc = zc(k, d); mn = zl(k, d); j = k - 1
    while j >= max(1, k - 150):
        if zh(j, d) > bc: break
        if zl(j, d) < mn: mn = zl(j, d); s = j
        j -= 1
    lv = []
    for jj in range(max(1, s if q0 is None else min(s, q0)), k + 1):
        o1, c1, l1 = zo(jj-1, d), zc(jj-1, d), zl(jj-1, d)
        o2, c2, l2 = zo(jj, d), zc(jj, d), zl(jj, d)
        kd = -1
        if c1 < o1 and c2 > o2: zlo, zhi, kd = min(l1, l2), c1, 0
        elif c1 > o1 and c2 > o2: zlo, zhi, kd = min(l2, c1), max(c1, o2), 1
        if kd < 0: continue
        dead = False; st = 0
        for m in range(jj + 1, k + 1):
            if st == 0:
                if zc(m, d) < zlo:
                    if kd == 0: st = 1
                    else: dead = True; break
            elif st == 1:
                if zc(m, d) > zhi: st = 2
            elif zl(m, d) <= zhi: dead = True; break
        if dead or st == 1: continue
        if st == 0 and jj < max(1, s): continue      # intact levels: only inside the leg
        lv.append([zlo, zhi, jj - 1, 3 if st == 2 else kd])
    if lvl is not None:
        lf = d * lvl; jb = -1
        for m in range(k - 1, max(1, k - 300) - 1, -1):
            if abs(zh(m, d) - lf) <= TICK * 2: jb = m; break
        if jb >= 1:
            bu = zc(jb, d) > zo(jb, d); pu = zc(jb-1, d) > zo(jb-1, d)
            lv.append([zc(jb, d) if bu else zc(jb-1, d) if pu else zo(jb, d), zh(jb, d), jb if (bu or not pu) else jb - 1, 2])
    return s, lv

def cands(d, a, b, s_lo, s_hi, last):
    """liquidity candidates from candle a..b: (level, candle, kind 0 single / 1 swing). last = newest closed candle"""
    out = []
    for j in range(max(1, a), b + 1):
        if s_lo <= j <= s_hi and zc(j, d) > zo(j, d):
            out.append((zl(j, d), j, 0))
        if j + 1 <= last and zc(j, d) < zc(j-1, d) and zc(j, d) < zc(j+1, d):
            out.append((min(zl(j, d), zl(j+1, d)), j, 1))
    return out

def pick(lv, ok, cs):
    """the level closest to price (highest hi) with a candidate above it; the candidate closest to it"""
    best = None
    cs = [c for c in cs if not any(ok[i] and l[0] < c[0] < l[1] for i, l in enumerate(lv))]
    for i, (lo, hi, t, kd) in enumerate(lv):
        if not ok[i]: continue
        ab = [c for c in cs if c[0] > hi]
        if ab and (best is None or hi > lv[best[0]][1]):
            best = (i, min(ab))
    return best

def rp(d, v): return d * v
def box(d, l): 
    a, b = sorted((d*l[0], d*l[1])); return f"{KN[l[3]]} {a:.5f}-{b:.5f} (from {lab(l[2])})"

BREAKS = [(113, 1, 1.11236), (117, 1, 1.11883), (121, 1, 1.12108), (133, -1, 1.11815), (137, -1, 1.11635),
          (143, 1, 1.11709), (150, -1, 1.11571), (151, -1, 1.11548)]

def opposite(bi):
    k, d, _ = BREAKS[bi]; dz = -d
    for kr, dr, lv_ in reversed(BREAKS[:bi]):
        if dr != dz: continue
        s, lv = levels(dz, kr, lv_)
        aft = min([zl(i, dz) for i in range(kr + 1, k)] + [zc(k, dz) + TOL])
        ok = [aft > l[1] for l in lv]
        cs = []
        for lvl, j, kd in cands(dz, kr, k - 1, kr, kr + SCN, k):
            later = [zl(i, dz) for i in range(j + 1 + kd, k)] + [zc(k, dz) + TOL]
            if min(later) >= lvl: cs.append((lvl, j, kd))
        b = pick(lv, ok, cs)
        if b:
            return f"opposite {'BUY' if dz>0 else 'SELL'}: {box(dz, lv[b[0]])} | liq {rp(dz,b[1][0]):.5f} ({'single' if b[1][2]==0 else 'swing'} {lab(b[1][1])}) | range of break {lab(kr)}"
    return "opposite: none"

def leg(bi, upto):
    kb, d, lvl = BREAKS[bi]
    q0 = None
    for kr, dr, _ in reversed(BREAKS[:bi]):
        if dr == -d:
            q0 = levels(dr, kr, None)[0]; break
    s, lv = levels(d, kb, lvl, q0)
    ok = [True] * len(lv)
    poi = None; liq = None
    for n in range(kb, upto + 1):
        if n > kb:
            for i, l in enumerate(lv):
                if ok[i] and zc(n, d) < l[0]: ok[i] = False
            if poi is not None and not ok[poi]: poi = None; print(f"   {lab(n)}: POI closed through")
        pre = []
        for lvl_, j, kd in cands(d, s, kb, s, kb, kb):
            later = [zl(i, d) for i in range(j + 1 + kd, kb + 1)]
            if not later or min(later) >= lvl_: pre.append((lvl_, j, kd))
        post = cands(d, kb + 1, n, kb + 1, kb + SCN, n)
        # Breaker / QM usable only while fresh: no wick into them since the break
        tap = min([zl(i, d) for i in range(kb + 1, n + 1)] or [float('inf')])
        okn = [ok[i] and (lv[i][3] not in (2, 3) or tap > lv[i][1] or poi == i) for i in range(len(lv))]
        b = pick(lv, okn, pre + post)
        new = None
        if b:
            if poi is None: new = b
            elif lv[poi][3] == 2:
                if b[0] == poi and liq[2] == 0 and b[1] != liq: new = b       # the Breaker's liquidity may still tighten until it is a swing
            elif lv[b[0]][3] == 2: new = b                                     # it moves once: to the fresh Breaker
        if new and (poi != new[0] or liq != new[1]):
            poi, liq = new
            print(f"   {lab(n)}: {'BUY' if d>0 else 'SELL'} POI {box(d, lv[poi])} | liq {rp(d, liq[0]):.5f} ({'single' if liq[2]==0 else 'swing'} {lab(liq[1])})")
    return

for bi in range(2, len(BREAKS)):
    k, d, lvl = BREAKS[bi]
    nxt = BREAKS[bi + 1][0] - 1 if bi + 1 < len(BREAKS) else k + 6
    print(f"== BREAK {lab(k)} {'bull' if d>0 else 'bear'} (line {lvl}) ==")
    print("  ", opposite(bi))
    leg(bi, nxt)
