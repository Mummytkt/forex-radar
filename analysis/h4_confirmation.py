"""
H4 breakout validation and internal/external classification.

The H4 confirmation logic mirrors the Daily breakout rule exactly:
  • Bearish H4 confirmation: an H4 candle closes BELOW the body level of an H4 V-shape.
  • Bullish H4 confirmation: an H4 candle closes ABOVE the body level of an H4 A-shape.

The body-close rule is strictly enforced — wick crosses never qualify.

Classification:
  EXTERNAL — the formation broken is the most recent outer structural boundary
             (the H4 A-shape for bullish or V-shape for bearish) seen before the
             confirmation candle. This is the swing-defining formation.
  INTERNAL — the formation broken is a smaller one that formed inside the current
             structural leg (i.e., it established after the outer formation).
"""

from __future__ import annotations

from typing import Optional

from data.models import (
    BreakoutClassification,
    Candle,
    Direction,
    Formation,
    FormationType,
    H4BreakoutEvent,
    Timeframe,
)
from analysis.formations import detect_a_shape, detect_v_shape


def find_outer_h4_formation(
    h4_candles: list[Candle],
    direction: Direction,
) -> Optional[Formation]:
    """
    Return the most recently established H4 formation that defines the current
    swing boundary for the expected confirmation direction.

    For BEARISH confirmation (price should break downward):
      Look for H4 V-shapes — the most recent V-shape is the outer boundary
      that a bearish candle must close below.

    For BULLISH confirmation (price should break upward):
      Look for H4 A-shapes — the most recent A-shape is the outer boundary
      that a bullish candle must close above.
    """
    if direction == Direction.BEARISH:
        formations = detect_v_shape(h4_candles)
    else:
        formations = detect_a_shape(h4_candles)

    # The FIRST (oldest) formation defines the outer structural boundary.
    # Formations established after it are internal to the current leg.
    return formations[0] if formations else None


def find_inner_h4_formations(
    h4_candles: list[Candle],
    direction: Direction,
    outer_formation: Formation,
) -> list[Formation]:
    """
    Return all same-type H4 formations that established AFTER the outer
    formation (i.e., they are internal to the current structural leg).
    """
    if direction == Direction.BEARISH:
        all_f = detect_v_shape(h4_candles)
    else:
        all_f = detect_a_shape(h4_candles)

    return [f for f in all_f if f.established_at > outer_formation.established_at]


def check_h4_breakout(
    candle: Candle,
    direction: Direction,
    h4_candles: list[Candle],
) -> Optional[H4BreakoutEvent]:
    """
    Check whether the given H4 candle has broken and closed beyond the body
    level of any qualifying H4 formation.

    Steps:
      1. Find the outer H4 formation (swing boundary).
      2. Find all inner formations that formed after the outer one.
      3. For the given candle, check if its close crosses any formation's level
         in the expected direction (body-close rule strictly enforced).
      4. The first qualifying break found (outer checked before inner) determines
         the classification.

    Returns H4BreakoutEvent if confirmed, None otherwise.

    Note: h4_candles should NOT include the confirmation candle itself —
    it is passed separately as `candle`. This ensures formations are evaluated
    against the candle history BEFORE the current candle closes.
    """
    outer = find_outer_h4_formation(h4_candles, direction)
    if outer is None:
        return None

    inner_formations = find_inner_h4_formations(h4_candles, direction, outer)

    # Collect candidate formations: outer first (preferred for EXTERNAL), then inner
    candidates = [outer] + inner_formations

    for formation in candidates:
        if _candle_breaks_formation(candle, direction, formation):
            classification = (
                BreakoutClassification.EXTERNAL
                if formation is outer
                else BreakoutClassification.INTERNAL
            )
            return H4BreakoutEvent(
                instrument=candle.instrument,
                direction=direction,
                classification=classification,
                formation_broken=formation,
                confirmation_ts=candle.timestamp,
            )

    return None


def _candle_breaks_formation(
    candle: Candle,
    direction: Direction,
    formation: Formation,
) -> bool:
    """
    Returns True if the candle's CLOSE (not wick) has crossed the formation's
    body level in the expected direction.

    Bearish: candle.close < formation.level  (close strictly below V-shape body_low)
    Bullish: candle.close > formation.level  (close strictly above A-shape body_high)
    """
    if direction == Direction.BEARISH:
        return candle.close < formation.level
    else:
        return candle.close > formation.level
