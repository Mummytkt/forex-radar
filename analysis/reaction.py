"""
Reaction source identification and retest detection.

Given an active Daily breakout, this module computes all eligible reaction
sources and detects when price has retested one of them.

Four source types:
  1. DAILY_BREAKER        — the original broken A/V level (role-reversed)
  2. OC_INSIDE_RANGE      — OC levels inside the pre-breakout range
  3. AV_INSIDE_RANGE      — A/V key levels inside the pre-breakout range
  4. POST_BREAKOUT_DAILY_OC — OC levels that formed after the breakout, in its direction
"""

from __future__ import annotations

from typing import Optional

from data.models import (
    Candle,
    DailyBreakout,
    Direction,
    Formation,
    FormationType,
    ReactionSource,
    ReactionSourceType,
    Timeframe,
)
from analysis.formations import detect_a_shape, detect_oc_levels, detect_v_shape


def _tolerance_band(level: float, tolerance_pips: float, pip_size: float) -> tuple[float, float]:
    offset = tolerance_pips * pip_size
    return (level - offset, level + offset)


def compute_reaction_sources(
    active_breakout: DailyBreakout,
    daily_candles: list[Candle],
    tolerance_pips: float,
    pip_size: float,
) -> list[ReactionSource]:
    """
    Compute all valid reaction sources for the given active Daily breakout.

    daily_candles should include candles up to and including the breakout candle
    plus any candles that have since formed (for POST_BREAKOUT_DAILY_OC).
    Ordered oldest → newest.
    """
    sources: list[ReactionSource] = []
    instrument = active_breakout.instrument
    direction = active_breakout.direction
    breakout_ts = active_breakout.breakout_ts

    # Split candles into pre-breakout and post-breakout (by timestamp)
    pre_candles = [c for c in daily_candles if c.timestamp < breakout_ts]
    post_candles = [c for c in daily_candles if c.timestamp >= breakout_ts]

    # ── 1. DAILY_BREAKER ──────────────────────────────────────────────────────
    # The original broken level. After a bearish breakout it becomes resistance;
    # after a bullish breakout it becomes support.
    band = _tolerance_band(active_breakout.broken_level, tolerance_pips, pip_size)
    sources.append(
        ReactionSource(
            instrument=instrument,
            source_type=ReactionSourceType.DAILY_BREAKER,
            direction=direction,
            level=active_breakout.broken_level,
            level_band_low=band[0],
            level_band_high=band[1],
            daily_breakout_ts=breakout_ts,
        )
    )

    if not pre_candles:
        # No pre-breakout history available — skip internal levels
        _add_post_breakout_oc(sources, instrument, direction, breakout_ts, post_candles, tolerance_pips, pip_size)
        return sources

    # Determine the "range" that contains the pre-breakout price action.
    # The range is bounded on one side by the broken level. The other boundary
    # is the swing extreme on the opposite side of the broken level within the
    # pre-breakout candles.
    broken_level = active_breakout.broken_level

    if direction == Direction.BEARISH:
        # Bearish breakout broke below the V-shape body_low.
        # The range is above the broken level. Swing high = max body_high of pre-candles.
        range_low = broken_level
        range_high = max(c.body_high for c in pre_candles)
    else:
        # Bullish breakout broke above the A-shape body_high.
        # The range is below the broken level. Swing low = min body_low of pre-candles.
        range_high = broken_level
        range_low = min(c.body_low for c in pre_candles)

    # Minimum clearance: exclude inside-range sources whose level is within the
    # broken_level's tolerance band — they are indistinguishable from the
    # DAILY_BREAKER and would trigger false retests on any post-breakout wick.
    _tol = tolerance_pips * pip_size

    # ── 2. AV_INSIDE_RANGE ───────────────────────────────────────────────────
    # Checked BEFORE OC so that when both are touched simultaneously the
    # explicitly drawn A/V level takes precedence over the derived OC level.
    # After BEARISH breakout: A-shapes inside the range are valid (resistance).
    # After BULLISH breakout: V-shapes inside the range are valid (support).
    if direction == Direction.BEARISH:
        av_formations = detect_a_shape(pre_candles)
    else:
        av_formations = detect_v_shape(pre_candles)

    for f in av_formations:
        if range_low <= f.level <= range_high and abs(f.level - broken_level) > _tol:
            band = _tolerance_band(f.level, tolerance_pips, pip_size)
            sources.append(
                ReactionSource(
                    instrument=instrument,
                    source_type=ReactionSourceType.AV_INSIDE_RANGE,
                    direction=direction,
                    level=f.level,
                    level_band_low=band[0],
                    level_band_high=band[1],
                    daily_breakout_ts=breakout_ts,
                )
            )

    # ── 3. OC_INSIDE_RANGE ───────────────────────────────────────────────────
    oc_levels = detect_oc_levels(pre_candles)
    for oc in oc_levels:
        if oc.direction == direction and range_low <= oc.level <= range_high and abs(oc.level - broken_level) > _tol:
            band = _tolerance_band(oc.level, tolerance_pips, pip_size)
            sources.append(
                ReactionSource(
                    instrument=instrument,
                    source_type=ReactionSourceType.OC_INSIDE_RANGE,
                    direction=direction,
                    level=oc.level,
                    level_band_low=band[0],
                    level_band_high=band[1],
                    daily_breakout_ts=breakout_ts,
                )
            )

    # ── 4. POST_BREAKOUT_DAILY_OC ─────────────────────────────────────────────
    # Only keep the 3 most recent post-breakout OC levels. Keeping every OC
    # since the breakout creates dozens of sources spread across the price range,
    # guaranteeing a false "Retesting" detection wherever price happens to trade.
    _add_post_breakout_oc(sources, instrument, direction, breakout_ts, post_candles, tolerance_pips, pip_size, max_oc=3)

    return sources


def _add_post_breakout_oc(
    sources: list[ReactionSource],
    instrument: str,
    direction: Direction,
    breakout_ts,
    post_candles: list[Candle],
    tolerance_pips: float,
    pip_size: float,
    max_oc: int = 3,
) -> None:
    """
    Append POST_BREAKOUT_DAILY_OC sources — at most `max_oc` most recent.

    Two consecutive same-direction daily candles after the breakout form an OC.
    Only the `max_oc` most recent are kept. Older OC levels are no longer
    relevant as reaction zones, and accumulating all of them creates dozens of
    false sources spread across the price range.
    """
    oc_levels = detect_oc_levels(post_candles)
    # Filter to matching direction, then take the most recent N
    matching = [oc for oc in oc_levels if oc.direction == direction]
    for oc in matching[-max_oc:]:
        band = _tolerance_band(oc.level, tolerance_pips, pip_size)
        sources.append(
            ReactionSource(
                instrument=instrument,
                source_type=ReactionSourceType.POST_BREAKOUT_DAILY_OC,
                direction=direction,
                level=oc.level,
                level_band_low=band[0],
                level_band_high=band[1],
                daily_breakout_ts=breakout_ts,
            )
        )


def is_price_retesting_source(candle: Candle, source: ReactionSource) -> bool:
    """
    Returns True if the H4 candle's price range (wick) overlaps the source band.

    Wick-based (high/low) rather than close-based: a genuine retest of a bearish
    level (resistance) produces H4 candles that wick INTO the band from below and
    close BELOW it (rejection). Requiring a close within the band would miss every
    real retest. False-positive accumulation is prevented instead by capping
    POST_BREAKOUT_DAILY_OC sources at 3 — with only ~5-8 sources per instrument,
    all clustered around the key level, a wick touch is meaningful again.
    """
    return candle.low <= source.level_band_high and candle.high >= source.level_band_low


_MAX_POST_BREAKOUT_OC = 3  # keep only the N most recent post-breakout OC levels


def update_post_breakout_sources(
    existing_sources: list[ReactionSource],
    active_breakout: DailyBreakout,
    new_daily_candles: list[Candle],
    tolerance_pips: float,
    pip_size: float,
) -> list[ReactionSource]:
    """
    Called after a new Daily candle closes (but no new breakout occurred).
    Recomputes POST_BREAKOUT_DAILY_OC sources from scratch, keeping at most
    _MAX_POST_BREAKOUT_OC most recent levels.

    Recomputing (rather than appending) ensures stale OC levels formed weeks
    ago are replaced by the current most-relevant ones.
    """
    instrument = active_breakout.instrument
    direction = active_breakout.direction
    breakout_ts = active_breakout.breakout_ts

    post_candles = [c for c in new_daily_candles if c.timestamp >= breakout_ts]
    oc_levels = detect_oc_levels(post_candles)
    matching = [oc for oc in oc_levels if oc.direction == direction]
    fresh_oc_levels = matching[-_MAX_POST_BREAKOUT_OC:]
    fresh_levels = {oc.level for oc in fresh_oc_levels}

    # Keep all non-POST_BREAKOUT sources unchanged; replace post-breakout OC set
    non_oc = [s for s in existing_sources if s.source_type != ReactionSourceType.POST_BREAKOUT_DAILY_OC]
    existing_oc_levels = {
        s.level for s in existing_sources
        if s.source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC
    }

    new_sources = list(non_oc)
    # Re-add existing OC sources that are still in the fresh set (preserves db_id)
    for s in existing_sources:
        if s.source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC and s.level in fresh_levels:
            new_sources.append(s)
    # Add genuinely new OC levels
    for oc in fresh_oc_levels:
        if oc.level not in existing_oc_levels:
            band = _tolerance_band(oc.level, tolerance_pips, pip_size)
            new_sources.append(
                ReactionSource(
                    instrument=instrument,
                    source_type=ReactionSourceType.POST_BREAKOUT_DAILY_OC,
                    direction=direction,
                    level=oc.level,
                    level_band_low=band[0],
                    level_band_high=band[1],
                    daily_breakout_ts=breakout_ts,
                )
            )

    return new_sources
