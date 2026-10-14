"""
H4 OC level detection and continuation trigger checking.

A bullish H4 OC is formed by two consecutive bullish H4 candles.
A bearish H4 OC is formed by two consecutive bearish H4 candles.
OC level = c1.close (the junction price where c1 closed = c2 opened).

Trigger (bullish): candle.low ≤ level + tolerance AND candle.close > level
Trigger (bearish): candle.high ≥ level - tolerance AND candle.close < level

The trigger candle must be a DIFFERENT candle from the one that completed
the OC pair — i.e., the OC's established_at must be < trigger candle's timestamp.
"""

from __future__ import annotations

from datetime import datetime

from data.models import Candle, Direction


def detect_h4_oc_levels(
    h4_candles: list[Candle],
    direction: Direction,
) -> list[tuple[float, datetime]]:
    """
    Return (level, established_at) for each consecutive same-direction H4 pair.

    level = c1.close (junction price; equals c2.open in gapless forex markets).
    established_at is the timestamp of the second candle in the pair.
    Results are ordered oldest → newest.
    """
    results: list[tuple[float, datetime]] = []
    for i in range(len(h4_candles) - 1):
        c1, c2 = h4_candles[i], h4_candles[i + 1]
        if direction == Direction.BULLISH and c1.is_bullish and c2.is_bullish:
            results.append((c1.close, c2.timestamp))
        elif direction == Direction.BEARISH and c1.is_bearish and c2.is_bearish:
            results.append((c1.close, c2.timestamp))
    return results


def is_h4_oc_triggered(
    candle: Candle,
    level: float,
    tolerance: float,
    direction: Direction,
) -> bool:
    """
    Check whether a closed H4 candle has reacted from an H4 OC level (c1.close).

    Bullish: wick touched at or below the level (low ≤ level + tolerance)
             AND closed above it (close > level) — reaction confirmed.
    Bearish: wick touched at or above the level (high ≥ level - tolerance)
             AND closed below it (close < level) — reaction confirmed.
    """
    if direction == Direction.BULLISH:
        return candle.low <= level + tolerance and candle.close > level
    else:
        return candle.high >= level - tolerance and candle.close < level
