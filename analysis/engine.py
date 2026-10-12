"""
Bias confirmation engine — orchestrates the full Daily → H4 confirmation chain.

This module has NO I/O. It receives pre-fetched candles and pre-loaded state,
runs the analysis, and returns structured results. The caller (scheduler) is
responsible for persisting state and sending alerts.

The confirmation chain (all steps required for ORIGIN):
  1. Daily breakout: a Daily candle closes beyond the body level of a qualifying
     A or V formation. The most recent breakout supersedes all prior ones.
  2. Eligible Daily reaction: price returns to a valid reaction source (breaker,
     internal OC, internal A/V, or post-breakout OC).
  3. H4 breakout: the reaction produces a qualifying H4 A/V breakout that closes
     beyond its body level in the same direction as the most recent Daily breakout.
  4. ORIGIN alert: only then is directional bias confirmed and an alert fired.

After an ORIGIN alert, CONTINUATION alerts fire without needing a new Daily retest:
  • CONTINUATION_ASHAPE: any subsequent H4 A/V formation broken in the daily direction.
  • CONTINUATION_H4_OC: price reacts from a bullish/bearish H4 OC (two consecutive
    same-direction H4 candles), closing beyond the OC midpoint.

A new opposing Daily breakout resets everything and starts a fresh origin cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from data.models import (
    AlertClassification,
    AlertRecord,
    Candle,
    DailyBreakout,
    Direction,
    H4BreakoutEvent,
    ReactionSource,
    ReactionSourceType,
    Timeframe,
)
from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape, detect_a_shape, detect_v_shape
from analysis.breakout import check_daily_breakout
from analysis.reaction import (
    compute_reaction_sources,
    is_price_retesting_source,
    update_post_breakout_sources,
)
from analysis.h4_confirmation import check_h4_breakout
from analysis.h4_oc import detect_h4_oc_levels, is_h4_oc_triggered


@dataclass
class EngineInput:
    instrument: str
    daily_candles: list[Candle]            # oldest → newest, includes just-closed Daily candle
    h4_candles: list[Candle]              # oldest → newest, includes just-closed H4 candle
    active_breakout: Optional[DailyBreakout]
    active_reaction_srcs: list[ReactionSource]
    retest_in_progress: bool
    active_reaction_src: Optional[ReactionSource]  # the source currently being retested
    tolerance_pips: float
    pip_size: float
    continuation_mode: bool = False               # True after first Origin alert fired
    last_alert_h4_ts: Optional[datetime] = None   # timestamp of confirming H4 candle from last alert
    last_h4_breaker_level: Optional[float] = None # body level of the H4 formation broken in last alert
    retest_started_h4_ts: Optional[datetime] = None  # H4 candle timestamp when retest first detected


@dataclass
class EngineOutput:
    # Set if a new Daily breakout fired this cycle
    new_breakout: Optional[DailyBreakout] = None
    # Updated full reaction source list (replaces existing list if new_breakout fired,
    # otherwise may have new POST_BREAKOUT_DAILY_OC sources appended)
    updated_reaction_srcs: list[ReactionSource] = field(default_factory=list)
    # Set if H4 confirmation fired this cycle
    h4_event: Optional[H4BreakoutEvent] = None
    # Non-None means the caller should send an alert
    alert_to_send: Optional[AlertRecord] = None
    # Updated retest state
    retest_in_progress: bool = False
    active_reaction_src: Optional[ReactionSource] = None
    retest_started_h4_ts: Optional[datetime] = None  # cleared when retest ends
    # Continuation state (carried forward each cycle)
    continuation_mode: bool = False
    last_alert_h4_ts: Optional[datetime] = None
    last_h4_breaker_level: Optional[float] = None


def _h4_level_retested(candle: Candle, level: float, tolerance: float, direction: Direction) -> bool:
    """
    True when an H4 candle has wicked into a key level and CLOSED beyond it,
    confirming a directional continuation from that level.

    Bearish: wick reached up to the level (high ≥ level − tol) AND close is below it.
    Bullish: wick reached down to the level (low ≤ level + tol) AND close is above it.
    """
    if direction == Direction.BEARISH:
        return candle.high >= level - tolerance and candle.close < level
    else:
        return candle.low <= level + tolerance and candle.close > level


# Higher number = lower priority. AV levels take precedence over OC levels when
# multiple sources are touched; DAILY_BREAKER always wins; post-breakout OC is last.
_SOURCE_PRIORITY: dict[ReactionSourceType, int] = {
    ReactionSourceType.DAILY_BREAKER: 0,
    ReactionSourceType.AV_INSIDE_RANGE: 1,
    ReactionSourceType.OC_INSIDE_RANGE: 2,
    ReactionSourceType.POST_BREAKOUT_DAILY_OC: 3,
}


def _price_established_beyond_zone(h4_candles: list[Candle], source: ReactionSource) -> bool:
    """
    A genuine retest requires price to have first MOVED AWAY from the reaction
    zone on the breakout side before returning to touch it.

    For a bullish source (support): at least one prior H4 candle must have
    closed ABOVE the band high (price established above the zone).
    For a bearish source (resistance): at least one prior H4 candle must have
    closed BELOW the band low (price established below the zone).

    Without this check the engine would falsely detect a "retest" when price is
    still hovering right at the breakout level immediately after the daily close.
    """
    if source.direction == Direction.BULLISH:
        return any(c.close > source.level_band_high for c in h4_candles)
    else:
        return any(c.close < source.level_band_low for c in h4_candles)


def run_engine_cycle(inp: EngineInput) -> EngineOutput:
    """
    Full analysis cycle for one instrument at one candle-close event.

    Called at every H4 close and at every Daily close. The engine handles both
    because a Daily close is also a meaningful H4 close event.
    """
    out = EngineOutput()

    if not inp.daily_candles or not inp.h4_candles:
        return out

    latest_daily = inp.daily_candles[-1]
    latest_h4 = inp.h4_candles[-1]

    # History windows (exclude the just-closed candle so formation detection
    # reflects formations that existed BEFORE this candle closed)
    daily_history = inp.daily_candles[:-1]
    h4_history = inp.h4_candles[:-1]

    # ── STEP 1: Check for new Daily breakout ──────────────────────────────────
    most_recent_a = get_most_recent_a_shape(daily_history)
    most_recent_v = get_most_recent_v_shape(daily_history)

    new_breakout = check_daily_breakout(latest_daily, most_recent_a, most_recent_v)

    if new_breakout is not None:
        # New breakout supersedes everything. Recompute all reaction sources.
        out.new_breakout = new_breakout
        out.updated_reaction_srcs = compute_reaction_sources(
            new_breakout,
            inp.daily_candles,      # includes the breakout candle for post-breakout OC seed
            inp.tolerance_pips,
            inp.pip_size,
        )
        # Reset all state — the new breakout invalidates any in-progress retest and continuation
        out.retest_in_progress = False
        out.active_reaction_src = None
        out.retest_started_h4_ts = None
        out.continuation_mode = False
        out.last_alert_h4_ts = None
        out.last_h4_breaker_level = None
        return out

    # No new breakout this cycle — carry forward existing state
    active_breakout = inp.active_breakout

    if active_breakout is None:
        return out

    # ── STEP 1b: Update post-breakout OC sources after new Daily candle ───────
    updated_srcs = update_post_breakout_sources(
        inp.active_reaction_srcs,
        active_breakout,
        inp.daily_candles,
        inp.tolerance_pips,
        inp.pip_size,
    )
    out.updated_reaction_srcs = updated_srcs

    active_sources = [s for s in updated_srcs if s.is_active]

    # Narrow H4 history to candles that formed AFTER the active daily breakout.
    # Using the full multi-hundred-candle history would expose pre-breakout A/V
    # formations at wrong levels that are trivially "broken" by current price.
    breakout_ts = active_breakout.breakout_ts
    post_breakout_h4 = [c for c in h4_history if c.timestamp >= breakout_ts]

    # ── STEP 2: Check for retest ───────────────────────────────────────────────
    retest_in_progress = inp.retest_in_progress
    active_reaction_src = inp.active_reaction_src
    retest_started_h4_ts = inp.retest_started_h4_ts

    if not retest_in_progress:
        for src in active_sources:
            if (is_price_retesting_source(latest_h4, src)
                    and _price_established_beyond_zone(post_breakout_h4, src)):
                retest_in_progress = True
                active_reaction_src = src
                retest_started_h4_ts = latest_h4.timestamp
                break
    else:
        # Retest already in progress — allow upgrade to a higher-priority source if one
        # is touched now. This handles the case where a deep OC was touched first but the
        # actual reaction (closest to the H4 confirmation) came from a shallower AV level.
        for src in active_sources:
            if (src is not active_reaction_src
                    and is_price_retesting_source(latest_h4, src)
                    and _price_established_beyond_zone(post_breakout_h4, src)
                    and active_reaction_src is not None
                    and _SOURCE_PRIORITY.get(src.source_type, 99)
                        < _SOURCE_PRIORITY.get(active_reaction_src.source_type, 99)):
                active_reaction_src = src
                retest_started_h4_ts = latest_h4.timestamp  # reset window to this upgrade point
                break

    out.retest_in_progress = retest_in_progress
    out.active_reaction_src = active_reaction_src
    out.retest_started_h4_ts = retest_started_h4_ts

    # Carry forward continuation state (may be updated below)
    out.continuation_mode = inp.continuation_mode
    out.last_alert_h4_ts = inp.last_alert_h4_ts
    out.last_h4_breaker_level = inp.last_h4_breaker_level

    # ── STEP 3: Check for qualifying H4 breakout (ORIGIN) ─────────────────────
    if retest_in_progress and active_reaction_src is not None:
        # Narrow the H4 window to candles that formed AFTER the retest began.
        # Using the full post-breakout window (potentially months of candles) would
        # expose pre-retest H4 formations — old bounce levels that are trivially
        # "broken" by current price and have nothing to do with the current reaction.
        if retest_started_h4_ts is not None:
            confirmation_h4 = [c for c in post_breakout_h4 if c.timestamp >= retest_started_h4_ts]
        else:
            # Pre-migration fallback: limit to last 30 H4 candles (~5 days)
            confirmation_h4 = post_breakout_h4[-30:] if len(post_breakout_h4) > 30 else post_breakout_h4

        h4_event = check_h4_breakout(
            latest_h4,
            active_breakout.direction,
            confirmation_h4,
        )

        if h4_event is not None:
            out.h4_event = h4_event
            out.alert_to_send = AlertRecord(
                instrument=inp.instrument,
                direction=active_breakout.direction,
                daily_breakout=active_breakout,
                reaction_source=active_reaction_src,
                h4_event=h4_event,
                fired_at=latest_h4.timestamp,
                classification=AlertClassification.ORIGIN,
            )

            # Source consumed; clear retest state; enable continuation mode
            out.retest_in_progress = False
            out.active_reaction_src = None
            out.retest_started_h4_ts = None
            out.continuation_mode = True
            out.last_alert_h4_ts = latest_h4.timestamp
            out.last_h4_breaker_level = h4_event.formation_broken.level

            # Mark the used source as inactive in the updated list
            for src in out.updated_reaction_srcs:
                if src is active_reaction_src or (
                    src.source_type == active_reaction_src.source_type
                    and src.level == active_reaction_src.level
                ):
                    src.is_active = False
                    break

            return out

    # ── STEP 4: Check for CONTINUATION alerts ─────────────────────────────────
    # Only runs when: origin has previously confirmed (continuation_mode = True)
    #                 AND we are NOT currently retesting a Daily source.
    if inp.continuation_mode and not retest_in_progress:
        # Only consider H4 candles formed AFTER the last alert's confirming candle.
        # This prevents re-firing from the same formation that triggered the last alert.
        if inp.last_alert_h4_ts is not None:
            post_last_alert_h4 = [
                c for c in h4_history if c.timestamp > inp.last_alert_h4_ts
            ]
        else:
            post_last_alert_h4 = post_breakout_h4

        if post_last_alert_h4:
            tol = inp.tolerance_pips * inp.pip_size

            # ── 4a: H4 Breaker retest ──────────────────────────────────────────
            # Check the exact level from the last alert's broken H4 formation.
            # Also check H4 A-shapes (bearish) or V-shapes (bullish) that formed
            # inside the daily range during retracements — both use the same
            # wick-touch + close-beyond logic.
            breaker_fired = False
            breaker_level_hit: Optional[float] = None

            if inp.last_h4_breaker_level is not None:
                if _h4_level_retested(latest_h4, inp.last_h4_breaker_level, tol, active_breakout.direction):
                    breaker_fired = True
                    breaker_level_hit = inp.last_h4_breaker_level

            if not breaker_fired:
                # Scan for opposing H4 formations inside the range (A-shapes for bearish,
                # V-shapes for bullish) — they act as retracement resistance/support zones.
                if active_breakout.direction == Direction.BEARISH:
                    range_formations = detect_a_shape(post_last_alert_h4)
                else:
                    range_formations = detect_v_shape(post_last_alert_h4)
                for rf in range_formations:
                    if _h4_level_retested(latest_h4, rf.level, tol, active_breakout.direction):
                        breaker_fired = True
                        breaker_level_hit = rf.level
                        break

            if breaker_fired and breaker_level_hit is not None:
                out.alert_to_send = AlertRecord(
                    instrument=inp.instrument,
                    direction=active_breakout.direction,
                    daily_breakout=active_breakout,
                    reaction_source=None,
                    h4_event=None,
                    fired_at=latest_h4.timestamp,
                    classification=AlertClassification.CONTINUATION_H4_BREAKER,
                    h4_breaker_level=breaker_level_hit,
                )
                out.retest_in_progress = False
                out.active_reaction_src = None
                out.continuation_mode = True
                out.last_alert_h4_ts = latest_h4.timestamp
                # Breaker level stays the same — the same level was retested and confirmed
                return out

            # ── 4b: Continuation A/V formation break ──────────────────────────
            h4_event_cont = check_h4_breakout(
                latest_h4,
                active_breakout.direction,
                post_last_alert_h4,
            )
            if h4_event_cont is not None:
                out.h4_event = h4_event_cont
                out.alert_to_send = AlertRecord(
                    instrument=inp.instrument,
                    direction=active_breakout.direction,
                    daily_breakout=active_breakout,
                    reaction_source=None,
                    h4_event=h4_event_cont,
                    fired_at=latest_h4.timestamp,
                    classification=AlertClassification.CONTINUATION_ASHAPE,
                )
                out.retest_in_progress = False
                out.active_reaction_src = None
                out.continuation_mode = True
                out.last_alert_h4_ts = latest_h4.timestamp
                out.last_h4_breaker_level = h4_event_cont.formation_broken.level
                return out

            # ── 4c: Continuation H4 OC reaction ───────────────────────────────
            h4_oc_levels = detect_h4_oc_levels(post_last_alert_h4, active_breakout.direction)
            for oc_midpoint, _oc_ts in h4_oc_levels:
                if is_h4_oc_triggered(latest_h4, oc_midpoint, tol, active_breakout.direction):
                    out.alert_to_send = AlertRecord(
                        instrument=inp.instrument,
                        direction=active_breakout.direction,
                        daily_breakout=active_breakout,
                        reaction_source=None,
                        h4_event=None,
                        fired_at=latest_h4.timestamp,
                        classification=AlertClassification.CONTINUATION_H4_OC,
                        h4_oc_level=oc_midpoint,
                    )
                    out.retest_in_progress = False
                    out.active_reaction_src = None
                    out.continuation_mode = True
                    out.last_alert_h4_ts = latest_h4.timestamp
                    return out

    return out
