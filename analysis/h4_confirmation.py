"""
H4 breakout validation and internal/external classification.

The H4 confirmation logic mirrors the Daily breakout rule exactly:
  • Bearish H4 confirmation: an H4 candle closes BELOW the body level of an H4 V-shape.
  • Bullish H4 confirmation: an H4 candle closes ABOVE the body level of an H4 A-shape.

The body-close rule is strictly enforced — wick crosses never qualify.

Classification:
  EXTERNAL — the formation broken is the most recent V/A shape that existed
             BEFORE the daily reaction started (the in-place H4 structure that
             price broke through after reacting from the daily level).
  INTERNAL — a V/A shape that formed AFTER the daily reaction began (a new
             smaller structure created during the reaction itself).

The split between pre- and post-retest is defined by retest_started_ts, which
is the open timestamp of the H4 candle that first triggered the daily retest
detection. Without it, all candles are treated as pre-retest (external only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from data.models import (
    BreakoutClassification,
    Candle,
    Direction,
    Formation,
    H4BreakoutEvent,
)
from analysis.formations import detect_a_shape, detect_v_shape


def check_h4_breakout(
    candle: Candle,
    direction: Direction,
    h4_candles: list[Candle],
    retest_started_ts: Optional[datetime] = None,
) -> Optional[H4BreakoutEvent]:
    """
    Check whether the given H4 candle has broken and closed beyond the body
    level of a qualifying H4 formation.

    External confirmation (stronger): breaking the most recent H4 V-shape (for
    bearish) or A-shape (for bullish) that formed BEFORE the daily retest began.
    This is the existing H4 structure that was in place when price returned to
    the daily reaction source — the last structural boundary before the reaction.

    Internal confirmation: breaking an H4 V-shape / A-shape that formed AFTER
    the daily retest began — a smaller structure created during the reaction.

    Parameters
    ----------
    candle           : the just-closed H4 candle being evaluated
    direction        : Daily breakout direction (bearish → look for V-shapes to break)
    h4_candles       : post-breakout H4 history, NOT including `candle` itself
    retest_started_ts: open timestamp of the H4 candle that first triggered
                       retest_in_progress; splits pre- vs post-retest candles
    """
    if retest_started_ts is not None:
        pre_retest = [c for c in h4_candles if c.timestamp < retest_started_ts]
        post_retest = [c for c in h4_candles if c.timestamp >= retest_started_ts]
    else:
        pre_retest = h4_candles
        post_retest = []

    if direction == Direction.BEARISH:
        ext_candidates = detect_v_shape(pre_retest)
        int_candidates = detect_v_shape(post_retest)
    else:
        ext_candidates = detect_a_shape(pre_retest)
        int_candidates = detect_a_shape(post_retest)

    # External: the LAST (most recent) formation before the retest — the structural
    # boundary that was still in place when price came back to the daily level.
    outer = ext_candidates[-1] if ext_candidates else None

    # Build candidate list: external first (preferred), then internal oldest → newest
    candidates: list[tuple[Formation, BreakoutClassification]] = []
    if outer is not None:
        candidates.append((outer, BreakoutClassification.EXTERNAL))
    for f in int_candidates:
        candidates.append((f, BreakoutClassification.INTERNAL))

    for formation, classification in candidates:
        if _candle_breaks_formation(candle, direction, formation):
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
