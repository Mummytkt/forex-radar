"""
Auto-check for Quick Backtest (owner request 2026-11-23).

The owner marks the setup by eye (her edge: the liquidity and the POI closest to it). This does the rest:
  1. loads that period's real candles (Dukascopy free minute data, cached on disk) and builds M5, M15, H1 and H4
     (H4 on the forex day: New York 17:00, so 22:00 UTC in winter / 21:00 in summer, like TradingView);
  2. finds the entry confirmations with EXACTLY the Entry Confirmations script's rules (pine/MummyTKT_EntryConfirmations.pine,
     f_forms), one timeframe at a time;
  3. keeps the ones whose wick reached the POI after the watch start, until an H4 candle CLOSES beyond the POI
     (a buy: close below its bottom; a sell: close above its top);
  4. trades each confirmation the owner's way: entry at the confirmation candle's close, SL at its wick (the
     script's touch), TP at tp_r R (3), stop to breakeven at be_r R (2), played on 1-minute candles (if the SL and the
     TP fall in the same minute, the SL counts). A loss is retaken at that confirmation's next formation whose wick reaches
     the old SL or goes past it (the live re-entry rule), while the setup lasts; the takes stop at the first win or breakeven;
  5. stars the confirmation that formed first.

The prices are Dukascopy's (bid), not her TradingView feed: a pattern that forms by a fraction of a pip can differ.
"""
from __future__ import annotations

import lzma
import os
import struct
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # straight to the data server, no system proxy
WATCH_DAYS = 21      # a setup is followed at most this long after its start
LOOKBACK_DAYS = 3    # candles before the start, so runs and OCs that began earlier are known

# Quick Backtest keys -> (timeframe minutes, pattern). OCTGD 1 / OCTGD 2 are the owner's own split (not in the script).
KEYS = {"pcl": (60, "pcl"), "eng": (60, "eng"), "octgd1": (60, "octgd"), "octgd2": (60, "octgd2"), "cisd": (60, "cisd"),
        "octgd15": (15, "octgd"), "octgd215": (15, "octgd2"), "cisd15": (15, "cisd"), "cisd5": (5, "cisd")}
OCWIN, CIWIN = 10, 20   # the script's defaults: OCTGD / CISD candles allowed


# ── Data ─────────────────────────────────────────────────────────────────────
def _point(pair: str) -> float:
    return 1e3 if pair.endswith("JPY") else 1e5


def _cache_dir(base: str, pair: str) -> str:
    d = os.path.join(base, "candle_cache", pair)
    os.makedirs(d, exist_ok=True)
    return d


def day_minutes(pair: str, day: date, cache: str) -> list[tuple]:
    """One UTC day of 1-minute candles: [(utc datetime, o, h, l, c)]. Weekends are empty."""
    if day.weekday() == 5:
        return []
    path = os.path.join(_cache_dir(cache, pair), f"{day.isoformat()}.bi5")
    raw = None
    if os.path.exists(path):
        raw = open(path, "rb").read()
    else:
        url = URL.format(pair=pair, y=day.year, m=day.month - 1, d=day.day)
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                raw = _DIRECT.open(req, timeout=30).read()
                break
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        if raw is None:
            raise RuntimeError(f"The candles for {day.isoformat()} aren't downloaded yet and the free data server is busy. "
                               "I've put this setup's days at the front of the download queue: try again in 10-20 minutes.")
        if raw or day < datetime.now(UTC).date() - timedelta(days=3):   # don't cache today's half-written file
            with open(path, "wb") as f:
                f.write(raw)
    if not raw:
        return []
    data = lzma.decompress(raw)
    pt = _point(pair)
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    out = []
    for i in range(len(data) // 24):
        t, o, c, lo, h, _v = struct.unpack(">IIIIIf", data[i * 24:(i + 1) * 24])
        out.append((start + timedelta(seconds=t), o / pt, h / pt, lo / pt, c / pt))
    return out


def _bucket(ts: datetime, tf: int) -> datetime:
    if tf < 240:
        m = (ts.hour * 60 + ts.minute) // tf * tf
        return ts.replace(hour=m // 60, minute=m % 60, second=0, microsecond=0)
    ny = ts.astimezone(NY)
    s = ny.replace(hour=17, minute=0, second=0, microsecond=0)
    if ny < s:
        s -= timedelta(days=1)
    k = int((ny - s).total_seconds() // (tf * 60))
    return (s + timedelta(minutes=k * tf)).astimezone(UTC)


def resample(mins: list[tuple], tf: int) -> list[dict]:
    """Candles of tf minutes: [{t (open, UTC), ct (close time), o, h, l, c}] from 1-minute candles."""
    out: list[dict] = []
    for ts, o, h, l, c in mins:
        b = _bucket(ts, tf)
        if out and out[-1]["t"] == b:
            k = out[-1]
            k["h"] = max(k["h"], h); k["l"] = min(k["l"], l); k["c"] = c
        else:
            out.append({"t": b, "ct": b + timedelta(minutes=tf), "o": o, "h": h, "l": l, "c": c})
    return out


# ── The script's confirmations (f_forms), one timeframe ──────────────────────
def confirmations(cs: list[dict]) -> list[dict]:
    """Every PCL / Engulfing / OCTGD / CISD the script would flag on these candles, both directions.
    Each: {i, ct, pat, dir ('buy'/'sell'), close, touch (the wick at the POI = the SL), level}."""
    ev = []
    boc = soc = None            # [level, wick, bar]
    bci = sci = None            # [line, extreme, bar]
    dn = up = None              # current run: [open, extreme, n]
    for i, k in enumerate(cs):
        o, h, l, c = k["o"], k["h"], k["l"], k["c"]
        cbull, cbear = c > o, c < o
        p = cs[i - 1] if i else None
        pbull = bool(p) and p["c"] > p["o"]
        pbear = bool(p) and p["c"] < p["o"]
        add = lambda pat, d, touch, lvl, lim=None: ev.append({"i": i, "ct": k["ct"], "pat": pat, "dir": d, "close": c,
                                                              "touch": touch, "level": lvl, "limit": lim})
        if p:
            if pbear and cbull and l < p["l"] and c > p["l"]:
                add("pcl", "buy", l, p["l"], o)
            if pbull and cbear and h > p["h"] and c < p["h"]:
                add("pcl", "sell", h, p["h"], o)
            if pbear and cbull and o <= p["c"] and c > p["o"]:
                add("eng", "buy", min(l, p["l"]), p["o"], p["o"])
            if pbull and cbear and o >= p["c"] and c < p["o"]:
                add("eng", "sell", max(h, p["h"]), p["o"], p["o"])
        # OCTGD: checked before this candle can start a new OC
        b_oc = s_oc = False
        if boc:
            if i - boc[2] > OCWIN:
                boc = None
            elif cbull and c > boc[0]:
                add("octgd", "buy", boc[1], boc[0], boc[0]); boc = None; b_oc = True
        if soc:
            if i - soc[2] > OCWIN:
                soc = None
            elif cbear and c < soc[0]:
                add("octgd", "sell", soc[1], soc[0], soc[0]); soc = None; s_oc = True
        if p and pbear and cbear:
            boc = [p["c"], min(l, p["l"]), i]
        if p and pbull and cbull:
            soc = [p["c"], max(h, p["h"]), i]
        # CISD: checked before this candle can change the run
        b_ci = s_ci = False
        if bci:
            if l < bci[1]:
                bci[1], bci[2] = l, i
            if i - bci[2] > CIWIN:
                bci = None
            elif cbull and c > bci[0]:
                add("cisd", "buy", bci[1], bci[0], bci[0]); bci = None; b_ci = True
        if sci:
            if h > sci[1]:
                sci[1], sci[2] = h, i
            if i - sci[2] > CIWIN:
                sci = None
            elif cbear and c < sci[0]:
                add("cisd", "sell", sci[1], sci[0], sci[0]); sci = None; s_ci = True
        if cbear:
            dn = [o, l, 1] if not pbear or dn is None else [dn[0], min(dn[1], l), dn[2] + 1]
            if not b_ci and dn[2] >= 2 and (bci is None or dn[1] <= bci[1]):
                bci = [dn[0], dn[1], i]
        if cbull:
            up = [o, h, 1] if not pbull or up is None else [up[0], max(up[1], h), up[2] + 1]
            if not s_ci and up[2] >= 2 and (sci is None or up[1] >= sci[1]):
                sci = [up[0], up[1], i]
    return ev


# ── Trading it ───────────────────────────────────────────────────────────────
def play(mins: list[tuple], start_i: int, side: str, entry: float, sl: float, tp_r: float, be_r: float) -> dict:
    """Follow one trade on 1-minute candles from index start_i. Returns outcome, exit time and index."""
    buy = side == "buy"
    risk = abs(entry - sl)
    tp = entry + (tp_r * risk if buy else -tp_r * risk)
    be = entry + (be_r * risk if buy else -be_r * risk) if be_r and be_r < tp_r else None
    stop, at_be = sl, False
    for j in range(start_i, len(mins)):
        ts, o, h, l, c = mins[j]
        if (l <= stop) if buy else (h >= stop):
            return {"outcome": "be" if at_be else "loss", "exit": ts, "j": j, "tp": tp, "sl": sl}
        if (h >= tp) if buy else (l <= tp):
            return {"outcome": "win", "exit": ts, "j": j, "tp": tp, "sl": sl}
        if be is not None and not at_be and ((h >= be) if buy else (l <= be)):
            stop, at_be = entry, True
    return {"outcome": "open", "exit": None, "j": len(mins), "tp": tp, "sl": sl}


def octgd2(cs: list[dict], side: str, level: float, start: datetime, tol: float = 0.0) -> list[dict]:
    """OCTGD 2 (owner, 2026-11-23, confirmed with Documents/OCTGD2_Rule_Check.png). At each touch of the level (a
    candle whose wick reaches it, after one that didn't), only the FIRST two candles count:
      - the touch candle closes in the trade's direction (a sell: bearish) -> it is the 1st, the next one the 2nd;
      - otherwise the two candles right after the touch.
    Both must be in the trade's direction, or there is no OCTGD 2 for that touch (later pairs don't count).
    Entry = their OC (the 1st's close = the 2nd's open) as a limit; SL = the pair's wick. Buys are the mirror."""
    buy = side == "buy"
    hit = lambda k: (k["l"] <= level + tol) if buy else (k["h"] >= level - tol)
    with_trade = lambda k: (k["c"] > k["o"]) if buy else (k["c"] < k["o"])
    out, touch_no = [], 0
    for i, k in enumerate(cs):
        if k["ct"] <= start or not hit(k) or (i and cs[i - 1]["ct"] > start and hit(cs[i - 1])):
            continue                              # not a NEW touch
        touch_no += 1
        a = i if with_trade(k) else i + 1
        if a + 1 >= len(cs):
            continue
        c1, c2 = cs[a], cs[a + 1]
        if not (with_trade(c1) and with_trade(c2)):
            continue                              # the first two aren't both in the trade's direction
        wick = min(c1["l"], c2["l"]) if buy else max(c1["h"], c2["h"])
        out.append({"i": a + 1, "ct": c2["ct"], "pat": "octgd2", "dir": side, "close": c2["c"], "touch": wick,
                    "level": c1["c"], "limit": c1["c"], "touch_no": touch_no})
    return out


def play_limit(mins, j0, side, limit, sl, tp_r, be_r, cancel_at):
    """A limit order from minute j0: filled when price comes back to it, cancelled if price reaches the TP first or
    the setup ends (cancel_at) before the fill. Then played like play()."""
    buy = side == "buy"
    risk = abs(limit - sl)
    tp = limit + (tp_r * risk if buy else -tp_r * risk)
    for j in range(j0, len(mins)):
        ts, o, h, l, c = mins[j]
        if cancel_at and ts >= cancel_at:
            return {"outcome": "cancelled", "exit": ts, "j": j, "tp": tp, "sl": sl, "filled": None}
        if (l <= limit) if buy else (h >= limit):
            if (l <= sl) if buy else (h >= sl):      # filled and stopped in the same minute: count the loss
                return {"outcome": "loss", "exit": ts, "j": j, "tp": tp, "sl": sl, "filled": ts}
            r = play(mins, j + 1, side, limit, sl, tp_r, be_r)
            r["filled"] = ts
            return r
        if (h >= tp) if buy else (l <= tp):
            return {"outcome": "cancelled", "exit": ts, "j": j, "tp": tp, "sl": sl, "filled": None}
    return {"outcome": "open", "exit": None, "j": len(mins), "tp": tp, "sl": sl, "filled": None}


def run(pair: str, side: str, level: float, start: datetime, cache: str, tp_r: float = 3.0, be_r: float = 2.0,
        mode: str = "limit", end_at: Optional[datetime] = None, tol_pips: float = 1.0, pictures: bool = False) -> dict:
    """Auto-check one setup: the level line, when the watch starts, and optionally the next breakout (end_at)."""
    start = start.astimezone(UTC)
    if end_at:
        end_at = end_at.astimezone(UTC)
    d0 = (start - timedelta(days=LOOKBACK_DAYS)).date()
    last_day = (start + timedelta(days=WATCH_DAYS)).date()
    today = datetime.now(UTC).date()
    want(pair, [d0 + timedelta(days=k) for k in range((min(last_day, today) - d0).days + 1)], cache)
    buy = side == "buy"
    # a wick within tol of the line counts as reaching it: her FOREX.com feed and this data differ by fractions of a pip
    tol = tol_pips * (0.01 if pair.endswith("JPY") else 0.0001)
    mins: list[tuple] = []
    d, h4_end, armed = d0, None, None
    # load day by day until an H4 candle closes beyond the level, the next breakout, or the watch's limit
    while d <= min(last_day, today):
        mins += day_minutes(pair, d, cache)
        d += timedelta(days=1)
        if d <= start.date() or not mins:
            continue
        last_t = mins[-1][0] + timedelta(minutes=1)
        for k in resample([m for m in mins if m[0] >= start - timedelta(hours=4)], 240):
            if k["t"] < start - timedelta(hours=4) or k["ct"] <= start:
                continue
            if k["ct"] > last_t:
                break
            if armed is not None and k["ct"] <= armed:
                continue
            if armed is None:
                # the setup starts once price has moved away: a whole H4 candle on the trade side of the level
                # (a sell: its high below the level), owner 2026-11-23. Touches before that aren't the setup.
                if (k["l"] > level) if buy else (k["h"] < level):
                    armed = k["ct"]
                continue
            # it ends when an H4 candle closes beyond the level (by more than the tolerance: feeds differ a little)
            if (k["c"] < level - tol) if buy else (k["c"] > level + tol):
                h4_end = k["ct"]
                break
        if h4_end or (end_at and last_t >= end_at):
            break
    if not mins:
        raise RuntimeError("No candles for that date (weekend, holiday, or the data isn't published yet).")
    if armed is None:
        return {"_pictures": [], "results": {}, "first": None, "poi_failed_at": None, "setup_end": start.isoformat(),
                "end_reason": "price never moved away from the level (no whole H4 candle on the trade side of it)",
                "watched_until": start.isoformat(), "armed_at": None,
                "note": "Check the level and the side: for a sell the level must be above price, for a buy below."}
    start = armed
    end = min(x for x in (h4_end, end_at, mins[-1][0]) if x)
    # open trades run on after the setup ends: a week more of candles
    while d <= min((end + timedelta(days=7)).date(), today):
        mins += day_minutes(pair, d, cache)
        d += timedelta(days=1)
    index = {m[0]: j for j, m in enumerate(mins)}
    frames = {tf: resample(mins, tf) for tf in {60, 15, 5}}
    found = {tf: confirmations(frames[tf]) for tf in frames}

    def formations(key: str, until: datetime) -> list[dict]:
        tf, pat = KEYS[key]
        if pat == "octgd2":
            evs = octgd2(frames[tf], side, level, start, tol)
        else:
            evs = [e for e in found[tf] if e["pat"] == pat and e["dir"] == side
                   and ((e["touch"] <= level + tol) if buy else (e["touch"] >= level - tol))]
        return [e for e in evs if start < e["ct"] <= until]

    def trade(key: str, until: datetime) -> Optional[dict]:
        trades, free_at, old_sl = [], start, None
        for e in formations(key, until):
            if e["ct"] < free_at:
                continue                     # one trade at a time
            if e.get("touch_no", 1) > 1 and old_sl is None:
                continue                     # OCTGD 2: only the first touch, unless a stop has been hit (owner)
            if old_sl is not None and not ((e["touch"] <= old_sl) if buy else (e["touch"] >= old_sl)):
                continue                     # a retake needs its wick at or past the stopped trade's SL (live re-entry rule)
            j0 = index.get(e["ct"])
            if j0 is None:
                j0 = next((j for j, m in enumerate(mins) if m[0] >= e["ct"]), len(mins))
            lim = e.get("limit")
            use_limit = mode == "limit" and lim is not None and ((e["touch"] < lim < e["close"]) if buy
                                                                  else (e["close"] < lim < e["touch"]))
            if use_limit:
                r = play_limit(mins, j0, side, lim, e["touch"], tp_r, be_r, until)
                entry = lim
            else:
                if abs(e["close"] - e["touch"]) <= 0:
                    continue
                r = play(mins, j0, side, e["close"], e["touch"], tp_r, be_r)
                r["filled"] = e["ct"]
                entry = e["close"]
            if r["outcome"] == "cancelled":
                free_at = r["exit"]
                continue                     # never filled: not a take
            trades.append({"time": e["ct"].isoformat(), "entry": round(entry, 5), "sl": round(e["touch"], 5),
                           "tp": round(r["tp"], 5), "outcome": r["outcome"], "limit": use_limit,
                           "filled": r["filled"].isoformat() if r.get("filled") else None,
                           "exit": r["exit"].isoformat() if r["exit"] else None})
            if r["outcome"] != "loss":
                break
            free_at, old_sl = r["exit"], e["touch"]
        if not trades:
            return None
        last = trades[-1]["outcome"]
        return {"outcome": "loss" if last == "open" and len(trades) > 1 else last, "takes": len(trades),
                "trades": trades, "formed": trades[0]["time"],
                # the first trade = the one ENTERED first (a limit: when it filled), owner 2026-11-23
                "entered": trades[0]["filled"] or trades[0]["time"]}

    # pass 1: which confirmation's trade was entered first (a limit: filled first); its TP ends the setup for the others
    first_pass = {k: trade(k, end) for k in KEYS}
    taken = {k: v for k, v in first_pass.items() if v}
    # same fill minute: the limit price reached first wins (a sell: price rises, so the lower limit; a buy: the higher)
    order = lambda v: (v["entered"], v["trades"][0]["entry"] if not buy else -v["trades"][0]["entry"], v["formed"])
    first = min(taken, key=lambda k: order(taken[k])) if taken else None
    tp_end = None
    if first:
        win = next((t for t in taken[first]["trades"] if t["outcome"] == "win"), None)
        if win and win["exit"]:
            tp_end = datetime.fromisoformat(win["exit"])
    # Every confirmation keeps being checked after the first trade's TP until the level ends (owner 2026-11-24), so
    # each one gets its own record and win rate. One entered after that TP is marked after_tp (★ first stays the real trade).
    out = taken
    for k, v in out.items():
        v["after_tp"] = bool(tp_end and datetime.fromisoformat(v["entered"]) >= tp_end and k != first)
    setup_end = end
    reason = ("an H4 candle closed beyond the level" if h4_end and setup_end == h4_end else
              "the next breakout" if end_at and setup_end == end_at else "the end of the data")
    pics = trade_pictures(pair, side, level, out, frames, tp_r, be_r) if pictures else []
    return {"_pictures": pics, "results": out, "first": first, "armed_at": armed.isoformat(),
            "first_tp_at": tp_end.isoformat() if tp_end else None,
            "poi_failed_at": h4_end.isoformat() if h4_end else None,
            "setup_end": setup_end.isoformat(), "end_reason": reason, "watched_until": setup_end.isoformat(),
            "note": "Prices are Dukascopy's (bid), not your TradingView feed: a pattern formed by a fraction of a pip "
                    "can differ. " + ("Entries are limit orders (OC, CISD line, PCL candle's open, the covered "
                    "candle's open); a limit that never fills isn't a take." if mode == "limit" else
                    "Entries are at the confirmation candle's close.")}


# ── Background download of the whole period (the free data server throttles bursts) ──────────────────────
PREFETCH_FROM = date(2019, 12, 1)


def _have(pair: str, day: date, cache: str) -> bool:
    return day.weekday() == 5 or os.path.exists(os.path.join(_cache_dir(cache, pair), f"{day.isoformat()}.bi5"))


def coverage(pair: str, cache: str) -> dict:
    today = datetime.now(UTC).date()
    days = [PREFETCH_FROM + timedelta(days=k) for k in range((today - PREFETCH_FROM).days - 2)]
    have = sum(_have(pair, d, cache) for d in days)
    missing = next((d for d in days if not _have(pair, d, cache)), None)
    return {"ready": have, "total": len(days), "pct": round(have / len(days) * 100, 1) if days else 100,
            "next_missing": missing.isoformat() if missing else None}


def _wanted_path(pair: str, cache: str) -> str:
    return os.path.join(_cache_dir(cache, pair), "_wanted.txt")


def want(pair: str, days: list[date], cache: str) -> None:
    """Put days an Auto-check needed at the front of the download queue."""
    p = _wanted_path(pair, cache)
    have = set(open(p).read().split()) if os.path.exists(p) else set()
    have |= {d.isoformat() for d in days if not _have(pair, d, cache)}
    with open(p, "w") as f:
        f.write(chr(10).join(sorted(have)))


def prefetch(pair: str, cache: str, budget: int = 6, gap: float = 6.0, max_refusals: int = 4) -> int:
    """Download up to `budget` missing days: the ones an Auto-check asked for first, then oldest first. The free
    server refuses bursts (HTTP 503), so it waits between tries and stops after a few refusals in a row."""
    today = datetime.now(UTC).date()
    wp = _wanted_path(pair, cache)
    wanted = [date.fromisoformat(x) for x in (open(wp).read().split() if os.path.exists(wp) else [])]
    queue = [d for d in wanted if not _have(pair, d, cache)]
    d = PREFETCH_FROM
    while d < today - timedelta(days=2) and len(queue) < budget * 3:
        if not _have(pair, d, cache) and d not in queue:
            queue.append(d)
        d += timedelta(days=1)
    got = refused = 0
    for d in queue:
        if got >= budget or refused >= max_refusals:
            break
        url = URL.format(pair=pair, y=d.year, m=d.month - 1, d=d.day)
        try:
            raw = _DIRECT.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
        except Exception:
            refused += 1
            time.sleep(gap)
            continue
        refused = 0
        with open(os.path.join(_cache_dir(cache, pair), f"{d.isoformat()}.bi5"), "wb") as f:
            f.write(raw)
        got += 1
        time.sleep(gap)
    if wanted:
        left = [x for x in wanted if not _have(pair, x, cache)]
        with open(wp, "w") as f:
            f.write(chr(10).join(x.isoformat() for x in left))
    return got


async def run_prefetch(config) -> None:
    import asyncio
    base = os.path.dirname(os.path.abspath(config.db_path)) or "."
    await asyncio.to_thread(prefetch, "EURUSD", base)


# ── Pictures (owner, 2026-11-23): one chart per trade, saved with the setup ───────────────────────────────
TF_NAME = {60: "H1", 15: "M15", 5: "M5"}
OUT_TXT = {"win": "TP hit", "loss": "SL hit", "be": "breakeven", "open": "still open"}
LABELS = {"pcl": "H1 PCL", "eng": "H1 Engulfing", "octgd1": "H1 OCTGD 1", "octgd2": "H1 OCTGD 2", "cisd": "H1 CISD",
          "octgd15": "M15 OCTGD", "octgd215": "M15 OCTGD 2", "cisd15": "M15 CISD", "cisd5": "M5 CISD"}


def trade_pictures(pair: str, side: str, level: float, res: dict, frames: dict, tp_r: float, be_r: float) -> list[tuple]:
    """[(key, n, png bytes)] for every trade in an Auto-check result."""
    from alerts.chart_image import render
    from alerts.follow_chart import trade_levels
    from config import fmt_price
    f = lambda v: fmt_price(pair, v)
    out = []
    for key, v in res.items():
        tf = KEYS[key][0]
        cs = frames[tf]
        for n, t in enumerate(v["trades"], 1):
            at = datetime.fromisoformat(t["time"])
            fi = next((i for i, k in enumerate(cs) if k["ct"] >= at), None)
            if fi is None:
                continue
            ex = datetime.fromisoformat(t["exit"]) if t.get("exit") else None
            ei = next((i for i, k in enumerate(cs) if ex and k["ct"] > ex), None)
            a = max(0, fi - 25)
            b = min(len(cs), max(fi + 30, (ei + 6) if ei is not None else fi + 30), a + 120)
            candles = [(k["t"].isoformat(), k["o"], k["h"], k["l"], k["c"]) for k in cs[a:b]]
            bucket = lambda d: next((k["t"].isoformat() for k in cs[a:b] if k["t"] <= d < k["ct"]), None)
            marks = [(cs[fi]["t"].isoformat(), "confirmed")]
            if t.get("limit") and t.get("filled"):
                fb = bucket(datetime.fromisoformat(t["filled"]))
                if fb:
                    marks.append((fb, "filled"))
            if ex:
                xb = bucket(ex)
                if xb:
                    marks.append((xb, OUT_TXT.get(t["outcome"], t["outcome"])))
            risk = abs(t["entry"] - t["sl"])
            be = t["entry"] + (be_r * risk if side == "buy" else -be_r * risk) if be_r and be_r < tp_r else None
            meta = {"tf_title": TF_NAME[tf], "side": f"{side.upper()} · {LABELS.get(key, key)} · take {n} · {t['outcome'].upper()}"
                                                  + (" · after TP" if v.get("after_tp") else ""),
                    "subtitle": f"{'Limit' if t.get('limit') else 'Entry'} {f(t['entry'])}  ·  SL {f(t['sl'])}  ·  TP {f(t['tp'])}",
                    "fired_at": at.astimezone(timezone(timedelta(hours=1))).strftime("%d %b %Y %H:%M WAT"), "marks": marks}
            try:
                png = render(pair, TF_NAME[tf], candles,
                             trade_levels(level, t["entry"], t["sl"], t["tp"], be, tp_r, be_r,
                                          "Limit" if t.get("limit") else "Entry"), meta, fmt=f, full=True)
                out.append((key, n, png))
            except Exception:
                continue
    return out
