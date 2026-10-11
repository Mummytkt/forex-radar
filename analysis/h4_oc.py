"""
H4 OC level detection and continuation trigger checking.

A bullish H4 OC is formed by two consecutive bullish H4 candles.
A bearish H4 OC is formed by two consecutive bearish H4 candles.
Midpoint = (close_1 + close_2) / 2

Trigger (bullish): candle.low ≤ midpoint + tolerance AND candle.close > midpoint
Trigger (bearish): candle.high ≥ midpoint - tolerance AND candle.close < midpoint
"""

from __future__ import annotations

from datetime import datetime

from data.models import Candle, Direction


def detect_h4_oc_levels(
    h4_candles: list[Candle],
    direction: Direction,
) -> list[tuple[float, datetime]]:
    """
    Return (midpoint, established_at) for each consecutive same-direction H4 pair.

    established_at is the timestamp of the second candle in the pair.
    Results are ordered oldest → newest.
    """
    results: list[tuple[float, datetime]] = []
    for i in range(len(h4_candles) - 1):
        c1, c2 = h4_candles[i], h4_candles[i + 1]
        if direction == Direction.BULLISH and c1.is_bullish and c2.is_bullish:
            results.append(((c1.close + c2.close) / 2, c2.timestamp))
        elif direction == Direction.BEARISH and c1.is_bearish and c2.is_bearish:
            results.append(((c1.close + c2.close) / 2, c2.timestamp))
    return results


def is_h4_oc_triggered(
    candle: Candle,
    midpoint: float,
    tolerance: float,
    direction: Direction,
) -> bool:
    """
    Check whether a candle has reacted from an H4 OC level.

    Bullish: candle wicks into or below the zone (low ≤ midpoint + tolerance)
             AND closes above the midpoint (rejection confirmed).
    Bearish: candle wicks into or above the zone (high ≥ midpoint - tolerance)
             AND closes below the midpoint (rejection confirmed).
    """
    if direction == Direction.BULLISH:
        return candle.low <= midpoint + tolerance and candle.close > midpoint
    else:
        return candle.high >= midpoint - tolerance and candle.close < midpoint
