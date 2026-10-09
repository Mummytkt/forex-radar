"""
Formation detection — pure functions only. No I/O, no DB access.

All functions accept a list of Candle objects (oldest → newest) and return
Formation objects. The body-level rule is strictly enforced throughout:
breakout thresholds are always body_high / body_low, never wick high / wick low.
"""

from __future__ import annotations

from typing import Optional

from data.models import (
    Candle,
    Direction,
    Formation,
    FormationType,
    Timeframe,
)


def detect_a_shape(candles: list[Candle]) -> list[Formation]:
    """
    Scan consecutive pairs for A-shape (resistance) formations.

    Pattern: candle[i] is bullish → candle[i+1] is bearish.
    Level   : candle[i].body_high  (max of open/close — never the wick)
    Direction: BEARISH  (this is a resistance level that a bullish move must break)
    Established: when the bearish candle (candle[i+1]) closes.
    """
    results: list[Formation] = []
    for i in range(len(candles) - 1):
        c1, c2 = candles[i], candles[i + 1]
        if c1.is_bullish and c2.is_bearish:
            results.append(
                Formation(
                    instrument=c1.instrument,
                    timeframe=c1.timeframe,
                    formation_type=FormationType.A_SHAPE,
                    direction=Direction.BEARISH,
                    level=c1.body_high,
                    established_at=c2.timestamp,
                    candle_1_ts=c1.timestamp,
                    candle_2_ts=c2.timestamp,
                )
            )
    return results


def detect_v_shape(candles: list[Candle]) -> list[Formation]:
    """
    Scan consecutive pairs for V-shape (support) formations.

    Pattern: candle[i] is bearish → candle[i+1] is bullish.
    Level   : candle[i].body_low  (min of open/close — never the wick)
    Direction: BULLISH  (this is a support level that a bearish move must break)
    Established: when the bullish candle (candle[i+1]) closes.
    """
    results: list[Formation] = []
    for i in range(len(candles) - 1):
        c1, c2 = candles[i], candles[i + 1]
        if c1.is_bearish and c2.is_bullish:
            results.append(
                Formation(
                    instrument=c1.instrument,
                    timeframe=c1.timeframe,
                    formation_type=FormationType.V_SHAPE,
                    direction=Direction.BULLISH,
                    level=c1.body_low,
                    established_at=c2.timestamp,
                    candle_1_ts=c1.timestamp,
                    candle_2_ts=c2.timestamp,
                )
            )
    return results


def detect_oc_levels(candles: list[Candle]) -> list[Formation]:
    """
    Scan for OC (Open-Close) levels from consecutive same-direction runs.

    For a run of N same-direction candles, produces N-1 OC levels:
      OC[k] level = (candles[k].close + candles[k+1].close) / 2
      OC[k] direction = run direction
      OC[k] established_at = candles[k+1].timestamp

    A run of 3 bullish candles [A, B, C] yields:
      OC(A,B) at B.timestamp
      OC(B,C) at C.timestamp
    """
    results: list[Formation] = []
    if not candles:
        return results

    run_start = 0
    for i in range(1, len(candles) + 1):
        # end of run: either end of list or direction changed
        if i == len(candles) or (candles[i].is_bullish != candles[run_start].is_bullish):
            run = candles[run_start:i]
            direction = Direction.BULLISH if run[0].is_bullish else Direction.BEARISH
            for k in range(len(run) - 1):
                c1, c2 = run[k], run[k + 1]
                level = (c1.close + c2.close) / 2.0
                results.append(
                    Formation(
                        instrument=c1.instrument,
                        timeframe=c1.timeframe,
                        formation_type=FormationType.OC,
                        direction=direction,
                        level=level,
                        established_at=c2.timestamp,
                        candle_1_ts=c1.timestamp,
                        candle_2_ts=c2.timestamp,
                    )
                )
            run_start = i

    return results


def detect_all_formations(candles: list[Candle]) -> list[Formation]:
    """Run all three detectors and return a combined list sorted by established_at."""
    all_f = detect_a_shape(candles) + detect_v_shape(candles) + detect_oc_levels(candles)
    all_f.sort(key=lambda f: f.established_at)
    return all_f


def get_most_recent_a_shape(candles: list[Candle]) -> Optional[Formation]:
    """Return the most recently established A-shape in the candle window."""
    shapes = detect_a_shape(candles)
    return shapes[-1] if shapes else None


def get_most_recent_v_shape(candles: list[Candle]) -> Optional[Formation]:
    """Return the most recently established V-shape in the candle window."""
    shapes = detect_v_shape(candles)
    return shapes[-1] if shapes else None
