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
    same-direction H4 candles), closing beyond the OC level (c1.close junction price).
    The reacting candle must be distinct from the candle that completed the OC pair.

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
    external_level: Optional[float] = None        # most extreme A/V level bounding the current trend
    external_level_direction: Optional[Direction] = None  # direction of the external level


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
    # True when the active breakout was invalidated (price returned through the
    # broken level). Caller should deactivate the breakout and go IDLE.
    invalidated: bool = False
    # Updated external level (set when a new breakout fires or level is reset)
    new_external_level: Optional[float] = None
    new_external_direction: Optional[Direction] = None


def _compute_external_level(daily_candles: list[Candle], direction: Direction) -> Optional[float]:
    """
    Derive the external bounding level for the current trend direction.
    BEARISH trend → external HIGH = highest A-shape body_high in history.
    BULLISH trend → external LOW  = lowest  V-shape body_low  in history.
    Returns None if no qualifying formation exists.
    """
    from analysis.formations import detect_a_shape, detect_v_shape
    if direction == Direction.BEARISH:
        shapes = detect_a_shape(daily_candles)
        return max((f.level for f in shapes), default=None)
    else:
        shapes = detect_v_shape(daily_candles)
        return min((f.level for f in shapes), default=None)


def _classify_daily_level(
    daily_candles: list[Candle],
    external_level: Optional[float],
    external_direction: Optional[Direction],
    alert_direction: Direction,
    tolerance: float,
) -> str:
    """
    Return "external" if recent Daily candles show price tested the external level
    before this alert triggered, "internal" otherwise.

    Checks the last 5 Daily candles' body_high (bearish) or body_low (bullish)
    against the external level within tolerance.
    """
    if external_level is None or external_direction != alert_direction:
        return "internal"
    recent = daily_candles[-5:]
    if alert_direction == Direction.BEARISH:
        return "external" if any(c.body_high >= external_level - tolerance for c in recent) else "internal"
    else:
        return "external" if any(c.body_low <= external_level + tolerance for c in recent) else "internal"


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

    # Guard against spurious opposing-direction supersession during a retest.
    #
    # Scenario (bug): bearish breakout active at level X. Price retests (rallies
    # back toward X). During the rally a small A-shape forms at level Y < X.  A
    # daily candle closes above Y → engine fires a BULLISH breakout and discards
    # the correct BEARISH setup.  But closing above Y (still below X) means price
    # is still inside the bearish range — it has not reversed.
    #
    # Rule: an opposing breakout is only valid when its formation level is on the
    # FAR side of the active broken level — i.e., price has genuinely reversed:
    #   • BEARISH active at X: new BULLISH requires A-shape level ≥ X
    #   • BULLISH active at X: new BEARISH requires V-shape level ≤ X
    #
    # Same-direction supersession (new bearish while bearish active, or new
    # bullish while bullish active) is never filtered — the most recent
    # formation in the same direction always applies.
    check_a = most_recent_a
    check_v = most_recent_v
    if inp.active_breakout is not None:
        if (inp.active_breakout.direction == Direction.BEARISH
                and check_a is not None
                and check_a.level < inp.active_breakout.broken_level):
            # A-shape inside the bearish range — suppress as reversal candidate
            check_a = None
        elif (inp.active_breakout.direction == Direction.BULLISH
                and check_v is not None
                and check_v.level > inp.active_breakout.broken_level):
            # V-shape inside the bullish range — suppress as reversal candidate
            check_v = None

    min_distance = inp.tolerance_pips * inp.pip_size
    new_breakout = check_daily_breakout(latest_daily, check_a, check_v, min_distance)

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
        # Compute or reset external level for the new trend direction
        ext = _compute_external_level(inp.daily_candles, new_breakout.direction)
        if ext is not None:
            out.new_external_level = ext
            out.new_external_direction = new_breakout.direction
        return out

    # No new breakout this cycle — carry forward existing state
    active_breakout = inp.active_breakout

    if active_breakout is None:
        return out

    # ── Breakout invalidation: if price has returned through the broken level
    # by more than tolerance_pips, the breakout is stale and the instrument
    # should go IDLE rather than wait indefinitely for H4 confirmation.
    # This prevents the engine getting stuck on a bullish setup while price
    # trends bearishly far below the breakout level (and vice versa).
    invalidation_margin = min_distance  # reuse the same tolerance
    if active_breakout.direction == Direction.BULLISH:
        # Bullish breakout invalidated: daily close back below broken_level by >tolerance
        if latest_daily.close < active_breakout.broken_level - invalidation_margin:
            out.invalidated = True
            return out
    else:
        # Bearish breakout invalidated: daily close back above broken_level by >tolerance
        if latest_daily.close > active_breakout.broken_level + invalidation_margin:
            out.invalidated = True
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

    # Include the latest H4 candle in the "established beyond zone" check.
    # post_breakout_h4 excludes the latest candle (it uses h4_history), so on
    # the very first H4 cycle after a daily breakout post_breakout_h4 is empty
    # and _price_established_beyond_zone always returns False. Using the full
    # list here means the first post-breakout H4 candle can itself satisfy both
    # "established beyond" and "retest wicking into band" simultaneously.
    all_post_breakout_h4 = [c for c in inp.h4_candles if c.timestamp >= breakout_ts]

    # ── STEP 2: Check for retest ───────────────────────────────────────────────
    retest_in_progress = inp.retest_in_progress
    active_reaction_src = inp.active_reaction_src
    retest_started_h4_ts = inp.retest_started_h4_ts

    if not retest_in_progress:
        for src in active_sources:
            if (is_price_retesting_source(latest_h4, src)
                    and _price_established_beyond_zone(all_post_breakout_h4, src)):
                retest_in_progress = True
                active_reaction_src = src
                retest_started_h4_ts = latest_h4.timestamp
                break
    else:
        # Retest already in progress — two cases for updating the active source:
        #
        # Case A — current source no longer touched (price moved away):
        #   Switch to whichever other source IS currently being touched. This handles
        #   the common scenario where price wicks the breaker (no H4 confirm), moves
        #   deeper into the range, then reacts from an OC or AV level. The alert must
        #   attribute to the level that actually caused the H4 confirmation.
        #
        # Case B — current source still touched, but a higher-priority source is also
        #   touched simultaneously: upgrade to the higher-priority one.
        #
        # Case C — price has left ALL source bands entirely:
        #   Cancel the retest. Without this, once retest_in_progress is set it
        #   persists until H4 confirms, meaning H4 formations forming far from the
        #   daily reaction level (e.g. 150+ pips away after a blow-through) can
        #   trigger spurious alerts. A fresh wick back to any source re-arms it.
        current_still_touched = (
            active_reaction_src is not None
            and is_price_retesting_source(latest_h4, active_reaction_src)
        )
        found_new_source = False
        for src in active_sources:
            if src is active_reaction_src:
                continue
            if not (is_price_retesting_source(latest_h4, src)
                    and _price_established_beyond_zone(all_post_breakout_h4, src)):
                continue
            if not current_still_touched:
                # Case A: current source gone — switch regardless of priority
                active_reaction_src = src
                retest_started_h4_ts = latest_h4.timestamp
                found_new_source = True
                break
            elif (active_reaction_src is not None
                    and _SOURCE_PRIORITY.get(src.source_type, 99)
                        < _SOURCE_PRIORITY.get(active_reaction_src.source_type, 99)):
                # Case B: both touched simultaneously — upgrade to higher priority
                active_reaction_src = src
                retest_started_h4_ts = latest_h4.timestamp
                found_new_source = True
                break

        # Case C: price is no longer touching any source — cancel retest.
        # A future H4 candle that wicks back to a source will re-arm it.
        if not current_still_touched and not found_new_source:
            retest_in_progress = False
            active_reaction_src = None
            retest_started_h4_ts = None

    out.retest_in_progress = retest_in_progress
    out.active_reaction_src = active_reaction_src
    out.retest_started_h4_ts = retest_started_h4_ts

    # Carry forward continuation state (may be updated below)
    out.continuation_mode = inp.continuation_mode
    out.last_alert_h4_ts = inp.last_alert_h4_ts
    out.last_h4_breaker_level = inp.last_h4_breaker_level

    # ── STEP 3: Check for qualifying H4 breakout (ORIGIN) ─────────────────────
    if retest_in_progress and active_reaction_src is not None:
        # Pass all post-breakout H4 candles together with the retest timestamp.
        # check_h4_breakout splits them internally:
        #   External = last V/A shape formed BEFORE retest_started_h4_ts
        #             (the H4 structure in place when price returned to the daily level)
        #   Internal = V/A shapes formed AFTER retest_started_h4_ts
        #             (new structure created during the reaction itself)
        h4_event = check_h4_breakout(
            latest_h4,
            active_breakout.direction,
            post_breakout_h4,
            retest_started_ts=retest_started_h4_ts,
        )

        if h4_event is not None:
            out.h4_event = h4_event
            _tol = inp.tolerance_pips * inp.pip_size
            _ctx = _classify_daily_level(
                inp.daily_candles, inp.external_level, inp.external_level_direction,
                active_breakout.direction, _tol,
            )
            out.alert_to_send = AlertRecord(
                instrument=inp.instrument,
                direction=active_breakout.direction,
                daily_breakout=active_breakout,
                reaction_source=active_reaction_src,
                h4_event=h4_event,
                fired_at=latest_h4.timestamp,
                classification=AlertClassification.ORIGIN,
                daily_level_context=_ctx,
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
                _ctx_br = _classify_daily_level(
                    inp.daily_candles, inp.external_level, inp.external_level_direction,
                    active_breakout.direction, tol,
                )
                out.alert_to_send = AlertRecord(
                    instrument=inp.instrument,
                    direction=active_breakout.direction,
                    daily_breakout=active_breakout,
                    reaction_source=None,
                    h4_event=None,
                    fired_at=latest_h4.timestamp,
                    classification=AlertClassification.CONTINUATION_H4_BREAKER,
                    h4_breaker_level=breaker_level_hit,
                    daily_level_context=_ctx_br,
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
                _ctx_cont = _classify_daily_level(
                    inp.daily_candles, inp.external_level, inp.external_level_direction,
                    active_breakout.direction, tol,
                )
                out.alert_to_send = AlertRecord(
                    instrument=inp.instrument,
                    direction=active_breakout.direction,
                    daily_breakout=active_breakout,
                    reaction_source=None,
                    h4_event=h4_event_cont,
                    fired_at=latest_h4.timestamp,
                    classification=AlertClassification.CONTINUATION_ASHAPE,
                    daily_level_context=_ctx_cont,
                )
                out.retest_in_progress = False
                out.active_reaction_src = None
                out.continuation_mode = True
                out.last_alert_h4_ts = latest_h4.timestamp
                out.last_h4_breaker_level = h4_event_cont.formation_broken.level
                return out

            # ── 4c: Continuation H4 OC reaction ───────────────────────────────
            h4_oc_levels = detect_h4_oc_levels(post_last_alert_h4, active_breakout.direction)
            for oc_level, oc_ts in h4_oc_levels:
                # The OC must have been established by a PRIOR candle — skip any
                # OC whose completing candle IS latest_h4, otherwise the alert
                # fires the instant the OC forms without a separate reaction.
                if oc_ts >= latest_h4.timestamp:
                    continue
                if is_h4_oc_triggered(latest_h4, oc_level, tol, active_breakout.direction):
                    _ctx_oc = _classify_daily_level(
                        inp.daily_candles, inp.external_level, inp.external_level_direction,
                        active_breakout.direction, tol,
                    )
                    out.alert_to_send = AlertRecord(
                        instrument=inp.instrument,
                        direction=active_breakout.direction,
                        daily_breakout=active_breakout,
                        reaction_source=None,
                        h4_event=None,
                        fired_at=latest_h4.timestamp,
                        classification=AlertClassification.CONTINUATION_H4_OC,
                        h4_oc_level=oc_level,
                        daily_level_context=_ctx_oc,
                    )
                    out.retest_in_progress = False
                    out.active_reaction_src = None
                    out.continuation_mode = True
                    out.last_alert_h4_ts = latest_h4.timestamp
                    return out

    return out
