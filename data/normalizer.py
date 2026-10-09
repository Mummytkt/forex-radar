"""
Twelve Data raw API response → internal Candle objects.

All timestamps are normalised to naive UTC datetime objects.
The instrument name is stored without slashes (EUR/USD → EURUSD) for
internal consistency; the API symbol (with slash) is handled by the caller.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from data.models import Candle, Timeframe

logger = logging.getLogger(__name__)

# Twelve Data returns datetime strings in two formats depending on timeframe:
#   H4  → "2026-10-10 00:00:00"  (datetime with time)
#   Daily → "2026-10-10"          (date only)
_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def symbol_to_instrument(symbol: str) -> str:
    """'EUR/USD' → 'EURUSD', 'XAU/USD' → 'XAUUSD'"""
    return symbol.replace("/", "").upper()


def instrument_to_symbol(instrument: str) -> str:
    """
    'EURUSD' → 'EUR/USD'.
    Handles standard 6-char forex pairs and 6-char metals (XAUUSD, XAGUSD).
    For non-standard lengths, inserts slash at position 3.
    """
    clean = instrument.upper()
    if len(clean) == 6:
        return f"{clean[:3]}/{clean[3:]}"
    return clean


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
