"""
Daily breakout detection.

A breakout requires a Daily candle to CLOSE beyond the body level of the
most recently established A-shape (bullish breakout) or V-shape (bearish
breakout). Wick-only moves never qualify.

The most recent breakout supersedes all prior breakouts, regardless of
whether the direction has flipped.
"""

from __future__ import annotations

from typing import Optional

from data.models import (
    Candle,
    DailyBreakout,
    Direction,
    Formation,
    FormationType,
)


def check_daily_breakout(
    candle: Candle,
    most_recent_a_shape: Optional[Formation],
    most_recent_v_shape: Optional[Formation],
) -> Optional[DailyBreakout]:
    """
    Evaluate one just-closed Daily candle for a breakout.

    Bullish: candle.close > most_recent_a_shape.level  (strictly greater)
    Bearish: candle.close < most_recent_v_shape.level  (strictly less)

    If both conditions are met simultaneously (e.g., a gap candle that
    skips over both levels), the one with the greater body distance wins.

    Returns a new DailyBreakout if one fired, otherwise None.
    The caller is responsible for deactivating the previous breakout in DB.
    """
    bullish_candidate: Optional[tuple[DailyBreakout, float]] = None
    bearish_candidate: Optional[tuple[DailyBreakout, float]] = None

    if most_recent_a_shape is not None and candle.close > most_recent_a_shape.level:
        distance = candle.close - most_recent_a_shape.level
        breakout = DailyBreakout(
            instrument=candle.instrument,
            direction=Direction.BULLISH,
            broken_level=most_recent_a_shape.level,
            broken_type=FormationType.A_SHAPE,
            breakout_ts=candle.timestamp,
        )
        bullish_candidate = (breakout, distance)

    if most_recent_v_shape is not None and candle.close < most_recent_v_shape.level:
        distance = most_recent_v_shape.level - candle.close
        breakout = DailyBreakout(
            instrument=candle.instrument,
            direction=Direction.BEARISH,
            broken_level=most_recent_v_shape.level,
            broken_type=FormationType.V_SHAPE,
            breakout_ts=candle.timestamp,
        )
        bearish_candidate = (breakout, distance)

    if bullish_candidate and bearish_candidate:
        # Simultaneous breaks: pick the one with greater distance from the level
        return (
            bullish_candidate[0]
            if bullish_candidate[1] >= bearish_candidate[1]
            else bearish_candidate[0]
        )

    if bullish_candidate:
        return bullish_candidate[0]
    if bearish_candidate:
        return bearish_candidate[0]
    return None


def is_new_breakout_superseding(
    new_candle: Candle,
    active_breakout: DailyBreakout,
    most_recent_a_shape: Optional[Formation],
    most_recent_v_shape: Optional[Formation],
) -> bool:
    """
    Returns True if the new candle creates a breakout that would supersede
    the currently active one. Used by the engine to detect direction flips.

    Note: a new breakout in the SAME direction also supersedes (resets the
    breakout anchor to the new level), so we check for any breakout.
    """
    return check_daily_breakout(new_candle, most_recent_a_shape, most_recent_v_shape) is not None
