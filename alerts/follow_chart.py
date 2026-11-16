"""
Charts for the entry alert and every follow message after it (user, 2026-11-16):
breakeven, TP, SL (the re-entry watch), the POI failing, TP after the stop.

The candles: the ones TradingView sent with the entry alert (stored on the follow), continued with the
5-minute price feed since. Gold, oil and the indices only have a Yahoo stand-in (futures / the cash index),
so its candles are shifted onto the TradingView price: the gap between the last TradingView H4 close and
the stand-in's price at that moment. When that gap can't be measured, the chart is the TradingView H4
candles instead.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import fmt_price

logger = logging.getLogger(__name__)

TFM = {"M5": 5, "M15": 15, "H1": 60, "H2": 120}
TF_NAME = {5: "M5", 15: "M15", 60: "H1", 120: "H2", 240: "H4"}
CONTEXT = 25     # candles shown before the entry
MAX_SHOWN = 90
FIVE = timedelta(minutes=5)


def _dt(s) -> datetime:
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).replace(microsecond=0).isoformat()


# ── Lining the stand-in up with TradingView ──────────────────────────────────

def h4_rows(conn, instrument: str, n: int = 24) -> list[tuple[datetime, float]]:
    """(close time, close) of the last TradingView H4 candles, newest first."""
    try:
        rows = conn.execute("SELECT ts, c FROM candles WHERE instrument = ? AND tf = 'H4' ORDER BY ts DESC LIMIT ?",
                            (instrument, n)).fetchall()
    except Exception:
        return []
    return [(_dt(r[0]) + timedelta(hours=4), float(r[1])) for r in rows]


def standin_offset(instrument: str, bars: list, rows: list) -> Optional[float]:
    """What to add to the Yahoo price to get the TradingView price: 0 for forex and crypto (Yahoo has the real
    pair); for a stand-in, measured at the latest TradingView H4 close the 5-minute candles cover. None: unknown."""
    from alerts.price_monitor import _EXACT_MAP
    if instrument.upper() not in _EXACT_MAP:
        return 0.0
    if not bars:
        return None
    for end, close in rows:
        before = [b for b in bars if b[0] + FIVE <= end]
        if before and end - (before[-1][0] + FIVE) <= timedelta(minutes=10):
            return close - before[-1][4]
    return None


def shift(bars: list, off: Optional[float]) -> list:
    if not off:
        return list(bars)
    return [(t, o + off, h + off, l + off, c + off) for t, o, h, l, c in bars]


# ── The candles to draw ──────────────────────────────────────────────────────

def _bucket(t: datetime, disp: int, anchor: Optional[datetime]) -> datetime:
    if disp == 240:
        from zoneinfo import ZoneInfo
        ln = t.astimezone(ZoneInfo("America/New_York"))
        a = ln.replace(hour=17, minute=0, second=0, microsecond=0)
        if a > ln:
            a -= timedelta(days=1)
        return (a + timedelta(hours=4) * int((ln - a) / timedelta(hours=4))).astimezone(timezone.utc)
    a = anchor or datetime(2000, 1, 1, tzinfo=timezone.utc)
    m = timedelta(minutes=disp)
    return a + m * ((t - a) // m)


def _aggregate(fine: list, disp: int, anchor: Optional[datetime]) -> list:
    out: dict = {}
    for t, o, h, l, c in fine:
        k = _bucket(t, disp, anchor)
        if k in out:
            o0, h0, l0, _c = out[k]
            out[k] = (o0, max(h0, h), min(l0, l), c)
        else:
            out[k] = (o, h, l, c)
    return [(k, *v) for k, v in sorted(out.items())]


def build(base_cs: Optional[str], bars: list, tf_label: str, entry_at: datetime, context: int = CONTEXT) -> tuple[str, list]:
    """(timeframe shown, candles (ISO open time, o, h, l, c)) from the entry's candles and the (already lined
    up) 5-minute ones after them. The entry timeframe while the trade fits on one chart, else a bigger one."""
    from alerts.chart_image import parse_candles
    tfm = TFM.get(tf_label, 60)
    base = [(_dt(t), o, h, l, c) for t, o, h, l, c in parse_candles(base_cs)]
    fine = list(base)
    if base:
        end = base[-1][0] + timedelta(minutes=tfm)
        fine += [b for b in bars if b[0] >= end]
    else:
        fine = list(bars)
    if not fine:
        return tf_label, []
    anchor = base[-1][0] if base else None
    best = None
    for disp in [tfm] + [m for m in (15, 60, 240) if m > tfm]:
        cs = _aggregate(fine, disp, anchor if disp == tfm else None)
        ie = max((i for i, c in enumerate(cs) if c[0] <= entry_at), default=0)
        start = max(0, ie - context)
        best = (TF_NAME.get(disp, tf_label), cs[start:])
        if len(cs) - start <= MAX_SHOWN:
            break
    name, cs = best
    cs = cs[-MAX_SHOWN:]
    return name, [(_iso(t), o, h, l, c) for t, o, h, l, c in cs]


def _h4_db(conn, instrument: str) -> list:
    from alerts.chart_image import candles_until
    try:
        return candles_until(conn, instrument, "H4", datetime.now(timezone.utc).isoformat())
    except Exception:
        return []


# ── The pictures ─────────────────────────────────────────────────────────────

_PAT = {"pcl": "PCL", "engulfing_sweep": "PCL", "sweep": "PCL", "octgd": "OCTGD", "cisd": "CISD",
        "engulfing": "Engulfing", "sweep_break": "Sweep and Break"}
_EVENT = {"open": "trade opened", "be": "breakeven point", "tp": "TP hit", "sl": "SL hit · re-entry watch",
          "left": "re-entry watch ended", "sl_tp": "TP reached after the stop", "expired": "follow ended"}


def trade_levels(level: Optional[float], entry: float, sl: float, tp: float, be: Optional[float],
                 tp_r=None, be_r=None) -> list[dict]:
    r = lambda v: f" (1:{float(v):g})" if v else ""
    out = []
    if level is not None:
        out.append({"y": level, "label": "Your level", "kind": "h4", "tf": "both"})
    out += [{"y": entry, "label": "Entry", "kind": "entry", "tf": "both"},
            {"y": sl, "label": "SL", "kind": "sl", "tf": "both"},
            {"y": tp, "label": "TP" + r(tp_r), "kind": "tp", "tf": "both"}]
    if be is not None:
        out.append({"y": be, "label": "Breakeven" + r(be_r), "kind": "be", "tf": "both"})
    return out


def follow_picture(conn, fo: dict, ev: str, bars: Optional[list], now: datetime) -> Optional[bytes]:
    """The chart for one follow message. bars: the lined-up 5-minute candles, or None when they can't be
    lined up with TradingView (then the TradingView H4 candles are drawn)."""
    from alerts.chart_image import render, WAT
    from alerts.trade_follow import level_of
    inst = fo["instrument"]
    tf_label = fo.get("tf") or "H1"
    tfm = TFM.get(tf_label, 60)
    from alerts.chart_image import parse_candles
    base = parse_candles(fo.get("candles"))
    entry_at = _dt(base[-1][0]) if base else _dt(fo["opened_at"]) - timedelta(minutes=tfm)
    if bars is not None:
        name, cs = build(fo.get("candles"), bars, tf_label, entry_at)
    else:
        name, cs = "H4", _h4_db(conn, inst)
    if len(cs) < 3:
        return None
    marks = [(_iso(entry_at), "entry")]
    when = {"sl": fo.get("sl_at"), "tp": fo.get("closed_at"), "sl_tp": fo.get("closed_at"), "left": fo.get("closed_at")}.get(ev)
    if fo.get("sl_at") and ev in ("sl_tp", "left"):
        marks.append((_iso(_dt(fo["sl_at"])), "SL"))
    if when:
        marks.append((_iso(_dt(when)), {"sl": "SL", "tp": "TP", "sl_tp": "TP", "left": "H4 close"}[ev]))
    side = "BUY" if fo["direction"] == "bullish" else "SELL"
    pat = _PAT.get(fo.get("pattern") or "", fo.get("pattern") or "")
    f = lambda v: fmt_price(inst, v)
    meta = {"tf_title": name, "side": f"{side} · {tf_label} {pat} · {_EVENT.get(ev, ev)}",
            "subtitle": f"Entry {f(fo['entry'])}  ·  SL {f(fo['sl'])}  ·  TP {f(fo['tp'])}",
            "fired_at": now.astimezone(WAT).strftime("%d %b %H:%M WAT"), "marks": marks}
    try:
        return render(inst, name, cs, trade_levels(level_of(fo), fo["entry"], fo["sl"], fo["tp"], fo.get("be"),
                                                    fo.get("tp_r"), fo.get("be_r")),
                      meta, fmt=f, full=True)
    except Exception:
        logger.exception("%s follow picture failed", inst)
        return None


def fallback_candles(instrument: str, tf_label: str, rows: list) -> list:
    """The entry alert's candles when TradingView sent none: the 5-minute feed (lined up) on the pattern's
    timeframe. Blocking (a Yahoo download): run it off the event loop."""
    from alerts.price_monitor import _fetch_prices
    bars = (_fetch_prices([instrument]).get(instrument) or {}).get("bars") or []
    off = standin_offset(instrument, bars, rows)
    if off is None or not bars:
        return []
    now = datetime.now(timezone.utc)
    _name, cs = build(None, shift(bars, off), tf_label, now, context=41)
    tfm = timedelta(minutes=TFM.get(tf_label, 60))
    # the last closed candle is the confirmation; drop the one still forming
    cs = [c for c in cs if _dt(c[0]) + tfm <= now + timedelta(minutes=1)]
    return cs[-40:]
