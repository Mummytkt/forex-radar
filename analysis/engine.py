"""
Bias confirmation engine — orchestrates the full Daily → H4 confirmation chain.

This module has NO I/O. It receives pre-fetched candles and pre-loaded state,
runs the analysis, and returns structured results. The caller (scheduler) is
responsible for persisting state and sending alerts.

The confirmation chain (all 4 steps required):
  1. Daily breakout: a Daily candle closes beyond the body level of a qualifying
     A or V formation. The most recent breakout supersedes all prior ones.
  2. Eligible Daily reaction: price returns to a valid reaction source (breaker,
     internal OC, internal A/V, or post-breakout OC).
  3. H4 breakout: the reaction produces a qualifying H4 A/V breakout that closes
     beyond its body level in the same direction as the most recent Daily breakout.
  4. Alert: only then is directional bias confirmed and an alert fired.

Timing rule: retest_in_progress persists until either the H4 confirms or a new
Daily breakout supersedes. There is no candle-count timeout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from data.models import (
    AlertRecord,
    Candle,
    DailyBreakout,
    Direction,
    H4BreakoutEvent,
    ReactionSource,
    Timeframe,
)
from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape
from analysis.breakout import check_daily_breakout
from analysis.reaction import (
    compute_reaction_sources,
    is_price_retesting_source,
    update_post_breakout_sources,
)
from analysis.h4_confirmation import check_h4_breakout


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
        # Reset retest state — the new breakout invalidates any in-progress retest
        out.retest_in_progress = False
        out.active_reaction_src = None
        return out

    # No new breakout this cycle — carry forward existing state
    active_breakout = inp.active_breakout

    if active_breakout is None:
        # No active breakout, nothing to monitor
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

    # ── STEP 2: Check for retest ───────────────────────────────────────────────
    retest_in_progress = inp.retest_in_progress
    active_reaction_src = inp.active_reaction_src

    if not retest_in_progress:
        # Check if the latest H4 candle is touching any reaction source zone
        for src in active_sources:
            if is_price_retesting_source(latest_h4, src):
                retest_in_progress = True
                active_reaction_src = src
                break

    out.retest_in_progress = retest_in_progress
    out.active_reaction_src = active_reaction_src

    if not retest_in_progress or active_reaction_src is None:
        return out

    # ── STEP 3: Check for qualifying H4 breakout ──────────────────────────────
    # Pass h4_history (candles before the confirmation candle) so formation
    # detection reflects what existed before this candle closed.
    h4_event = check_h4_breakout(
        latest_h4,
        active_breakout.direction,
        h4_history,
    )

    if h4_event is None:
        # Retest in progress but no H4 confirmation yet — keep watching
        return out

    # ── STEP 4: Bias confirmed — build alert ──────────────────────────────────
    out.h4_event = h4_event
    out.alert_to_send = AlertRecord(
        instrument=inp.instrument,
        direction=active_breakout.direction,
        daily_breakout=active_breakout,
        reaction_source=active_reaction_src,
        h4_event=h4_event,
        fired_at=latest_h4.timestamp,
    )

    # The source is consumed; clear retest state.
    # The breakout stays active — other sources remain valid for further confirmations.
    out.retest_in_progress = False
    out.active_reaction_src = None

    # Mark the used source as inactive in the updated list
    for src in out.updated_reaction_srcs:
        if src is active_reaction_src or (
            src.source_type == active_reaction_src.source_type
            and src.level == active_reaction_src.level
        ):
            src.is_active = False
            break

    return out
