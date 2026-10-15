"""
Public track record of Origin bias confirmations.

Each Origin alert is measured against TradingView H4 closing prices recorded from
PRICE_UPDATE webhooks (the same data the signals come from):

  entry  = the H4 close nearest the alert time (within 45 minutes)
  24h    = the last H4 close at or before entry + 24 hours
  5 days = the last H4 close at or before entry + 5 days

Moves are in pips in the alert's direction (positive = price went the way the
bias said). An alert is shown only once it is fully evaluated (5 days old), so
live signals are never revealed. Percentages are withheld until MIN_SAMPLE
alerts are evaluated, so a tiny sample can't mislead either way.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from config import pip_size_for

EVAL = timedelta(days=5)
DAY = timedelta(hours=24)
ENTRY_WINDOW = timedelta(minutes=45)
MAX_GAP = timedelta(days=2, hours=8)
MIN_SAMPLE = 10
_FMT = "%Y-%m-%dT%H:%M:%S"


def _p(s: str) -> datetime:
    return datetime.strptime(s[:19], _FMT)


def _f(d: datetime) -> str:
    return d.strftime(_FMT)


def evaluate_alert(conn, instrument: str, direction: str, fired_at: str) -> Optional[dict]:
    """Outcome of one alert, or None when the price data doesn't cover it."""
    t0 = _p(fired_at)
    rows = conn.execute(
        "SELECT ts, price FROM price_ticks WHERE instrument = ? AND ts BETWEEN ? AND ? ORDER BY ts",
        (instrument, _f(t0 - ENTRY_WINDOW), _f(t0 + EVAL)),
    ).fetchall()
    if not rows:
        return None
    ticks = [(_p(r[0]), r[1]) for r in rows]

    near = [t for t in ticks if abs(t[0] - t0) <= ENTRY_WINDOW]
    if not near:
        return None
    entry_ts, entry = min(near, key=lambda t: abs(t[0] - t0))

    after = [t for t in ticks if t[0] > entry_ts]
    # Require a price reasonably close to each horizon. The slack covers a market
    # weekend (Fri close → Sun open); a longer gap means missing data, so skip.
    at24 = [t for t in after if t[0] <= entry_ts + DAY]
    at5 = after
    if not at24 or entry_ts + DAY - at24[-1][0] > MAX_GAP:
        return None
    if not at5 or entry_ts + EVAL - at5[-1][0] > MAX_GAP:
        return None

    sign = 1 if direction.lower() == "bullish" else -1
    pip = pip_size_for(instrument)
    moves = [sign * (p - entry) / pip for _, p in after]
    pct = lambda p: round(sign * (p - entry) / entry * 100, 2)
    return {
        "instrument": instrument,
        "direction": direction.lower(),
        "fired_at": fired_at,
        "unit": "pips" if _quoted_in_pips(instrument) else "%",
        "move_24h": round(sign * (at24[-1][1] - entry) / pip, 1),
        "move_5d": round(sign * (at5[-1][1] - entry) / pip, 1),
        "move_24h_pct": pct(at24[-1][1]),
        "move_5d_pct": pct(at5[-1][1]),
        "best": round(max(0.0, max(moves)), 1),
        "worst": round(min(0.0, min(moves)), 1),
    }


_FIAT = {"EUR", "USD", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"}


def _quoted_in_pips(instrument: str) -> bool:
    """Currency pairs and metals are read in pips; indices, energy and crypto in %."""
    s = instrument.replace("/", "").upper()
    return s in {"XAUUSD", "XAGUSD"} or (len(s) == 6 and s[:3] in _FIAT and s[3:] in _FIAT)


def compute_track_record(conn, now: Optional[datetime] = None) -> dict:
    now = now or datetime.utcnow()
    cutoff = _f(now - EVAL)
    since_row = conn.execute("SELECT MIN(ts) FROM price_ticks").fetchone()
    since = since_row[0] if since_row and since_row[0] else None

    evaluated = []
    if since:
        for inst, direction, fired_at in conn.execute(
            "SELECT instrument, direction, fired_at FROM alerts "
            "WHERE alert_classification = 'origin' AND fired_at >= ? AND fired_at <= ? ORDER BY fired_at DESC",
            (since, cutoff),
        ).fetchall():
            out = evaluate_alert(conn, inst, direction, fired_at)
            if out:
                evaluated.append(out)

    running = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE alert_classification = 'origin' AND fired_at > ?", (cutoff,)
    ).fetchone()[0]

    n = len(evaluated)
    enough = n >= MIN_SAMPLE
    rate = (lambda key: round(100 * sum(1 for e in evaluated if e[key] > 0) / n)) if enough else (lambda key: None)
    return {
        "tracking_since": since,
        "evaluated": n,
        "running": running,
        "min_sample": MIN_SAMPLE,
        "in_profit_24h_pct": rate("move_24h"),
        "in_profit_5d_pct": rate("move_5d"),
        "recent": evaluated[:12],
    }
