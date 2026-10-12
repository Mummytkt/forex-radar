"""
Twelve Data raw API response → internal Candle objects.

All timestamps are normalised to naive UTC datetime objects.
The instrument name is stored without slashes (EUR/USD → EURUSD) for
internal consistency; the API symbol (with slash) is handled by the caller.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from data.models import Candle, Timeframe

logger = logging.getLogger(__name__)

# Twelve Data returns datetime strings in two formats depending on timeframe:
#   H4  → "2026-10-10 00:00:00"  (datetime with time)
#   Daily → "2026-10-10"          (date only)
_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def symbol_to_instrument(symbol: str) -> str:
    """'EUR/USD' → 'EURUSD', 'XAU/USD' → 'XAUUSD'"""
    return symbol.replace("/", "").upper()


# Instruments whose internal name must not be split at position 3 — they are
# indices or commodities with non-standard naming (e.g. "NAS100" would become
# "NAS/100" which Twelve Data does not recognise).
_SYMBOL_OVERRIDES: dict[str, str] = {
    "US30":    "US30",
    "NAS100":  "NAS100",
    "SPX500":  "SPX500",
    "UK100":   "UK100",
    "GER40":   "GER40",
    "JPN225":  "JPN225",
}


def instrument_to_symbol(instrument: str) -> str:
    """
    Convert an internal instrument name to a Twelve Data API symbol.

    'EUR/USD' → 'EUR/USD'   (already correct — returned as-is)
    'EURUSD'  → 'EUR/USD'   (6-char no-slash → split at 3)
    'NAS100'  → 'NAS100'    (index override — no split)
    """
    key = instrument.upper().replace("/", "")
    if key in _SYMBOL_OVERRIDES:
        return _SYMBOL_OVERRIDES[key]
    up = instrument.upper()
    if "/" in up:
        return up  # already in BASE/QUOTE form
    if len(up) == 6:
        return f"{up[:3]}/{up[3:]}"  # EURUSD → EUR/USD
    return up


def normalize_candles(
    raw_values: list[dict],
    instrument: str,
    timeframe: Timeframe,
) -> list[Candle]:
    """
    Convert a list of raw Twelve Data OHLCV dicts to Candle objects.

    raw_values: newest → oldest (as returned by the API).
    Returns:    oldest → newest (chronological order, as expected by the engine).
    """
    candles: list[Candle] = []
    for item in raw_values:
        try:
            raw_dt = item["datetime"]
            ts = None
            for fmt in _DT_FORMATS:
                try:
                    ts = datetime.strptime(raw_dt, fmt)
                    break
                except ValueError:
                    continue
            if ts is None:
                raise ValueError(f"Unrecognised datetime format: {raw_dt!r}")
            candles.append(
                Candle(
                    instrument=instrument,
                    timeframe=timeframe,
                    timestamp=ts,
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item.get("volume") or 0.0),
                )
            )
        except (KeyError, ValueError) as e:
            logger.warning("Skipping malformed candle for %s: %s — %s", instrument, item, e)

    candles.reverse()  # oldest → newest
    return candles


def aggregate_h4_from_1h(
    candles_1h: list[Candle],
    session_start_utc_hour: int = 21,
) -> list[Candle]:
    """
    Aggregate 1h candles into NY-session-aligned 4h candles.

    With session_start_utc_hour=21 (EDT), H4 periods are:
      21:00→01:00, 01:00→05:00, 05:00→09:00, 09:00→13:00, 13:00→17:00, 17:00→21:00 UTC
    Close times match TradingView's H4 candles: 2am,6am,10am,2pm,6pm,10pm WAT.

    With session_start_utc_hour=22 (EST, from November), they shift by 1 hour.

    Periods with fewer than 4 hourly candles (incomplete — still forming) are excluded.
    """
    if not candles_1h:
        return []

    def _period_start(dt: datetime, session_hour: int) -> datetime:
        shifted = (dt.hour - session_hour) % 24
        block = shifted // 4
        start_hour = (session_hour + block * 4) % 24
        d = dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if start_hour > dt.hour:
            d -= timedelta(days=1)
        return d

    groups: dict[datetime, list[Candle]] = defaultdict(list)
    for c in candles_1h:
        groups[_period_start(c.timestamp, session_start_utc_hour)].append(c)

    h4_candles: list[Candle] = []
    for pstart in sorted(groups.keys()):
        group = sorted(groups[pstart], key=lambda c: c.timestamp)
        if len(group) < 4:
            continue  # incomplete period — still forming, skip
        h4_candles.append(Candle(
            instrument=group[0].instrument,
            timeframe=Timeframe.H4,
            timestamp=pstart,
            open=group[0].open,
            high=max(c.high for c in group),
            low=min(c.low for c in group),
            close=group[-1].close,
            volume=sum(c.volume for c in group),
        ))

    return h4_candles
