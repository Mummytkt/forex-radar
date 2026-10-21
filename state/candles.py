"""
Candles as the Bias Pointer saw them on TradingView, for chart pictures.

PRICE_UPDATE carries the H4 candle that just closed and the last completed
Daily candle; a new alert first sends 40 Daily and 40 H4 candles (HISTORY).
Stored per instrument and timeframe ('D' / 'H4'), keyed by the candle's open
time (ISO 8601 UTC). About 400 candles per timeframe are kept.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

KEEP = 400


def ensure_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            instrument TEXT NOT NULL,
            tf         TEXT NOT NULL,     -- 'D' or 'H4'
            ts         TEXT NOT NULL,     -- candle open time, ISO 8601 UTC
            o REAL NOT NULL, h REAL NOT NULL, l REAL NOT NULL, c REAL NOT NULL,
            PRIMARY KEY (instrument, tf, ts)
        )""")


def tf_name(tf: Optional[str]) -> Optional[str]:
    t = (tf or "").upper()
    return "D" if t in ("D", "1D") else "H4" if t in ("240", "H4", "4H") else None


def upsert(conn, instrument: str, tf: str, bars: Iterable) -> int:
    """bars: [time_ms, open, high, low, close] each; bad rows are skipped."""
    ensure_table(conn)
    n = 0
    for b in bars or []:
        try:
            t, o, h, l, c = b
            ts = datetime.fromtimestamp(int(t) / 1000, tz=timezone.utc).isoformat()
            vals = [float(o), float(h), float(l), float(c)]
        except Exception:
            continue
        conn.execute(
            "INSERT INTO candles (instrument, tf, ts, o, h, l, c) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(instrument, tf, ts) DO UPDATE SET o = excluded.o, h = excluded.h, l = excluded.l, c = excluded.c",
            (instrument, tf, ts, *vals))
        n += 1
    if n:
        conn.execute(
            "DELETE FROM candles WHERE instrument = ? AND tf = ? AND ts NOT IN "
            "(SELECT ts FROM candles WHERE instrument = ? AND tf = ? ORDER BY ts DESC LIMIT ?)",
            (instrument, tf, instrument, tf, KEEP))
        conn.commit()
    return n


def recent(conn, instrument: str, tf: str, n: int = 60) -> list[tuple]:
    """The last n candles, oldest first: (ts, o, h, l, c)."""
    ensure_table(conn)
    rows = conn.execute(
        "SELECT ts, o, h, l, c FROM candles WHERE instrument = ? AND tf = ? ORDER BY ts DESC LIMIT ?",
        (instrument, tf, n)).fetchall()
    return [tuple(r) for r in reversed(rows)]
