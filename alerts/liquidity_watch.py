"""
Liquidity alerts after a break (owner request, 2026-11-11; picture Documents/Liquidity_Kinds_After_Breakout.png).

Every H4 story alert (a break: continuation, pullback, back in alignment, ...) starts a watch on that
instrument. On each H4 candle close after it, the candles after the breaking candle are checked for:

  - SINGLE CANDLE liquidity: in the first SINGLE_N candles after the break, after a bullish break a
    bullish candle's low wick (price pulls back through it into the POI), after a bearish break a bearish
    candle's high wick. Sent once per break (the first one).
  - LOW / HIGH liquidity: a V-shape on closes after a bullish break (a close lower than the closes on
    either side; the level is the lowest wick of that candle and the next), an A-shape after a bearish
    break. Each new one is sent as it forms (it is known one candle later, when the next candle closes).

The next story alert on the instrument replaces the watch. A watch ends after MAX_CANDLES candles.
Delivered like the other alerts: to everyone watching the instrument whose Alert Filters have
"Liquidity after a break" switched on (off by default).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import fmt_price, tagged

logger = logging.getLogger(__name__)

SINGLE_N = 3        # single candle liquidity: only in the first N candles after the break
MAX_CANDLES = 40    # the watch ends after this many H4 candles

SCHEMA = """
CREATE TABLE IF NOT EXISTS liq_watch (
    instrument  TEXT PRIMARY KEY,
    direction   TEXT NOT NULL,           -- 'bullish' | 'bearish' (the break)
    title       TEXT NOT NULL,           -- the alert it follows, e.g. 'H4 bullish continuation after the Daily breakout'
    started_at  TEXT NOT NULL,           -- when that alert came (UTC)
    break_ts    TEXT,                    -- the breaking H4 candle's open time (found from the stored candles)
    sent_single INTEGER NOT NULL DEFAULT 0,
    sent_v      TEXT NOT NULL DEFAULT '' -- the candles whose V / A was sent, comma separated
)
"""


def ensure_table(conn) -> None:
    conn.execute(SCHEMA)


def start(conn, instrument: str, direction: str, title: str, now: Optional[datetime] = None) -> None:
    """A new H4 alert on the instrument: watch for the liquidity after it (replaces the old watch)."""
    ensure_table(conn)
    now = now or datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO liq_watch (instrument, direction, title, started_at, break_ts, sent_single, sent_v)
        VALUES (?, ?, ?, ?, NULL, 0, '')
        ON CONFLICT(instrument) DO UPDATE SET direction = excluded.direction, title = excluded.title,
            started_at = excluded.started_at, break_ts = NULL, sent_single = 0, sent_v = ''
    """, (instrument, direction, title, now.isoformat()))
    conn.commit()


def _parse(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def find(direction: str, candles: list[tuple], sent_single: bool, sent_v: set[str]) -> list[dict]:
    """
    candles: (ts, o, h, l, c) oldest first; candles[0] = the breaking candle, the rest closed after it.
    Returns the new liquidity, oldest first: {'kind': 'single'|'swing', 'level', 'ts', 'ts2'?}.
    """
    bull = direction == "bullish"
    d = 1 if bull else -1
    lo = (lambda k: candles[k][3]) if bull else (lambda k: -candles[k][2])    # flipped: buy-side lows
    cl = lambda k: d * candles[k][4]
    op = lambda k: d * candles[k][1]
    out = []
    n = len(candles)
    if not sent_single:
        for k in range(1, min(n, SINGLE_N + 1)):
            if cl(k) > op(k):            # bullish candle after a bullish break (bearish after a bearish one)
                out.append({"kind": "single", "level": d * lo(k), "ts": candles[k][0]})
                break
    for k in range(1, n - 1):           # a V on closes needs the candle after it closed
        if candles[k][0] in sent_v:
            continue
        if cl(k) < cl(k - 1) and cl(k) < cl(k + 1):
            out.append({"kind": "swing", "level": d * min(lo(k), lo(k + 1)), "ts": candles[k][0], "ts2": candles[k + 1][0]})
    out.sort(key=lambda x: x["ts"])
    return out


def _wat(ts: str) -> str:
    return (_parse(ts) + timedelta(hours=1)).strftime("%d %b %H:%M") + " WAT"


def text(instrument: str, direction: str, title: str, liq: dict) -> str:
    bull = direction == "bullish"
    if liq["kind"] == "single":
        name = "Single candle liquidity"
        what = (f"the low wick of the bullish candle of {_wat(liq['ts'])}" if bull
                else f"the high wick of the bearish candle of {_wat(liq['ts'])}")
    else:
        name = "Low liquidity" if bull else "High liquidity"
        what = (f"a V-shape on the closes ({_wat(liq['ts'])}): its low" if bull
                else f"an A-shape on the closes ({_wat(liq['ts'])}): its high")
    t = title if title.startswith(("H4", "Daily")) else title[0].lower() + title[1:]
    side = "below it" if bull else "above it"
    return (f"💧 {name} after the {t}\n\n"
            f"{tagged(instrument)}\n"
            f"Liquidity: {fmt_price(instrument, liq['level'])}, {what}.\n\n"
            f"The {'BUY' if bull else 'SELL'} POI is the fresh key level of the leg just {side}: price sweeping this liquidity "
            f"into it is the setup.")


def check(conn, instrument: str) -> list[str]:
    """After an H4 candle is stored: the liquidity that formed since the last check, as alert texts."""
    try:
        w = conn.execute("SELECT * FROM liq_watch WHERE instrument = ?", (instrument,)).fetchone()
    except Exception:
        return []
    if not w:
        return []
    w = dict(w)
    break_ts = w["break_ts"]
    if not break_ts:
        # the breaking candle: the last stored H4 candle that opened at least 3 h before the alert came
        cutoff = (_parse(w["started_at"]) - timedelta(hours=3)).isoformat()
        r = conn.execute("SELECT ts FROM candles WHERE instrument = ? AND tf = 'H4' AND ts <= ? ORDER BY ts DESC LIMIT 1",
                         (instrument, cutoff)).fetchone()
        if not r:
            return []
        break_ts = r[0]
        conn.execute("UPDATE liq_watch SET break_ts = ? WHERE instrument = ?", (break_ts, instrument))
    rows = conn.execute("SELECT ts, o, h, l, c FROM candles WHERE instrument = ? AND tf = 'H4' AND ts >= ? ORDER BY ts ASC",
                        (instrument, break_ts)).fetchall()
    candles = [tuple(r) for r in rows]
    if len(candles) > MAX_CANDLES + 1:
        conn.execute("DELETE FROM liq_watch WHERE instrument = ?", (instrument,))
        conn.commit()
        return []
    sent_v = {s for s in (w["sent_v"] or "").split(",") if s}
    new = find(w["direction"], candles, bool(w["sent_single"]), sent_v)
    if not new:
        conn.commit()
        return []
    for liq in new:
        if liq["kind"] == "single":
            w["sent_single"] = 1
        else:
            sent_v.add(liq["ts"])
    conn.execute("UPDATE liq_watch SET sent_single = ?, sent_v = ? WHERE instrument = ?",
                 (w["sent_single"], ",".join(sorted(sent_v)), instrument))
    conn.commit()
    return [text(instrument, w["direction"], w["title"], liq) for liq in new]
