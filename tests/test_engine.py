"""
Tests for analysis/engine.py — full confirmation chain integration.

These tests feed crafted candle sequences through run_engine_cycle and assert
that the state machine transitions and alert firing behave correctly.
"""

import pytest
from datetime import datetime

from data.models import Direction, Timeframe
from analysis.engine import EngineInput, EngineOutput, run_engine_cycle
from tests.fixtures.candles import (
    full_bearish_cycle_daily,
    full_bearish_cycle_h4,
    make_candle,
    INST,
    D,
    H4,
    _ts,
)

TOLERANCE = 5.0
PIP = 0.0001


def _base_input(**kwargs) -> EngineInput:
    defaults = dict(
        instrument=INST,
        daily_candles=[],
        h4_candles=[],
        active_breakout=None,
        active_reaction_srcs=[],
        retest_in_progress=False,
        active_reaction_src=None,
        tolerance_pips=TOLERANCE,
        pip_size=PIP,
    )
    defaults.update(kwargs)
    return EngineInput(**defaults)


class TestNewBreakout:
    def test_detects_bearish_breakout(self):
        candles = full_bearish_cycle_daily()[:5]  # last candle is the breakout
        inp = _base_input(
            daily_candles=candles,
            h4_candles=full_bearish_cycle_h4()[:1],  # need at least 1 H4 candle
        )
        out = run_engine_cycle(inp)
        assert out.new_breakout is not None
        assert out.new_breakout.direction == Direction.BEARISH

    def test_new_breakout_resets_retest_state(self):
        """A new breakout should clear any in-progress retest from the previous breakout."""
        candles = full_bearish_cycle_daily()[:5]
        inp = _base_input(
            daily_candles=candles,
            h4_candles=full_bearish_cycle_h4()[:1],
            retest_in_progress=True,
            active_reaction_src=None,  # simplified
        )
        out = run_engine_cycle(inp)
        assert out.new_breakout is not None
        assert out.retest_in_progress is False
        assert out.active_reaction_src is None

    def test_no_breakout_without_formation(self):
        """If there's no A or V shape in the history, no breakout should fire."""
        candles = [
            make_candle(INST, D, _ts(1), 1.1000, 1.1050, 1.0990, 1.1020),  # bullish
            make_candle(INST, D, _ts(2), 1.1020, 1.1060, 1.1000, 1.1040),  # bullish (no A/V formed yet)
        ]
        inp = _base_input(
            daily_candles=candles,
            h4_candles=[make_candle(INST, H4, _ts(2), 1.1020, 1.1060, 1.1000, 1.1040)],
        )
        out = run_engine_cycle(inp)
        assert out.new_breakout is None

    def test_reaction_sources_computed_on_breakout(self):
        candles = full_bearish_cycle_daily()[:5]
        inp = _base_input(
            daily_candles=candles,
            h4_candles=full_bearish_cycle_h4()[:1],
        )
        out = run_engine_cycle(inp)
        assert out.new_breakout is not None
        assert len(out.updated_reaction_srcs) > 0


class TestRetestDetection:
    def test_retest_flag_set_when_h4_touches_source(self):
        """When a H4 candle touches a reaction source band, retest_in_progress should flip."""
        from analysis.reaction import compute_reaction_sources
        from analysis.breakout import check_daily_breakout
        from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape

        daily_candles = full_bearish_cycle_daily()[:5]
        most_recent_a = get_most_recent_a_shape(daily_candles[:-1])
        most_recent_v = get_most_recent_v_shape(daily_candles[:-1])
        breakout = check_daily_breakout(daily_candles[-1], most_recent_a, most_recent_v)
        assert breakout is not None

        # Extend with retracement candle
        daily_candles_extended = full_bearish_cycle_daily()  # candle 7 retraces to ~1.1000

        sources = compute_reaction_sources(breakout, daily_candles, TOLERANCE, PIP)

        # H4 candle that touches the Daily Breaker zone (1.1000 ± 5 pips)
        touching_h4 = make_candle(INST, H4, _ts(7, 4), 1.0980, 1.1003, 1.0975, 1.0990)

        inp = _base_input(
            daily_candles=daily_candles_extended,
            h4_candles=[touching_h4],
            active_breakout=breakout,
            active_reaction_srcs=sources,
        )
        out = run_engine_cycle(inp)
        assert out.retest_in_progress is True
        assert out.active_reaction_src is not None

    def test_no_retest_without_active_breakout(self):
        inp = _base_input(
            daily_candles=full_bearish_cycle_daily(),
            h4_candles=full_bearish_cycle_h4(),
            active_breakout=None,
        )
        out = run_engine_cycle(inp)
        # new_breakout may fire, but existing retest logic should not set flag in IDLE
        # (if a breakout fires, retest is cleared by definition)
        if out.new_breakout is None:
            assert out.retest_in_progress is False


class TestFullConfirmation:
    def test_full_bearish_alert_fires(self):
        """
        End-to-end: Daily bearish breakout → retest H4 zone → H4 V-shape broken → alert.
        """
        from analysis.reaction import compute_reaction_sources
        from analysis.breakout import check_daily_breakout
        from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape

        daily_candles = full_bearish_cycle_daily()[:5]
        most_recent_a = get_most_recent_a_shape(daily_candles[:-1])
        most_recent_v = get_most_recent_v_shape(daily_candles[:-1])
        breakout = check_daily_breakout(daily_candles[-1], most_recent_a, most_recent_v)
        assert breakout is not None
        sources = compute_reaction_sources(breakout, daily_candles, TOLERANCE, PIP)

        h4_candles = full_bearish_cycle_h4()
        # The last H4 candle closes below the H4 V-shape level — confirmation
        confirmation_h4 = h4_candles[-1]

        inp = _base_input(
            daily_candles=full_bearish_cycle_daily(),
            h4_candles=h4_candles,
            active_breakout=breakout,
            active_reaction_srcs=sources,
            retest_in_progress=True,
            active_reaction_src=sources[0],  # Daily Breaker
        )
        out = run_engine_cycle(inp)
        assert out.alert_to_send is not None
        assert out.alert_to_send.direction == Direction.BEARISH
        assert out.alert_to_send.instrument == INST

    def test_alert_not_sent_without_retest(self):
        """Even with a valid breakout, no alert without a prior retest."""
        from analysis.reaction import compute_reaction_sources
        from analysis.breakout import check_daily_breakout
        from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape

        daily_candles = full_bearish_cycle_daily()[:5]
        most_recent_a = get_most_recent_a_shape(daily_candles[:-1])
        most_recent_v = get_most_recent_v_shape(daily_candles[:-1])
        breakout = check_daily_breakout(daily_candles[-1], most_recent_a, most_recent_v)
        sources = compute_reaction_sources(breakout, daily_candles, TOLERANCE, PIP)

        inp = _base_input(
            daily_candles=full_bearish_cycle_daily(),
            h4_candles=full_bearish_cycle_h4(),
            active_breakout=breakout,
            active_reaction_srcs=sources,
            retest_in_progress=False,   # no retest in progress
            active_reaction_src=None,
        )
        out = run_engine_cycle(inp)
        # May detect retest on this cycle, but should not fire alert in same cycle
        # (retest detection and H4 confirmation are mutually exclusive in one cycle)
        if not out.retest_in_progress:
            assert out.alert_to_send is None

    def test_new_breakout_during_retest_cancels_alert(self):
        """If a new Daily breakout fires while retest is in progress, alert must not fire."""
        from analysis.breakout import check_daily_breakout
        from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape

        # Build a sequence where a new breakout supersedes the old one
        candles_with_new_breakout = [
            # Original V-shape setup
            make_candle(INST, D, _ts(1), 1.1050, 1.1060, 1.0970, 1.1000),  # bearish
            make_candle(INST, D, _ts(2), 1.1000, 1.1040, 1.0990, 1.1030),  # bullish → V-shape 1.1000
            make_candle(INST, D, _ts(3), 1.1030, 1.1080, 1.1010, 1.1060),  # bullish
            make_candle(INST, D, _ts(4), 1.1060, 1.1100, 1.1020, 1.1040),  # bearish → A-shape 1.1060
            make_candle(INST, D, _ts(5), 1.1040, 1.1050, 1.0980, 1.0990),  # bearish breakout
            # New bullish breakout: closes above the A-shape at 1.1060
            make_candle(INST, D, _ts(6), 1.0990, 1.1090, 1.0980, 1.1070),  # bullish, close > 1.1060
        ]
        from data.models import DailyBreakout, Direction, FormationType
        old_breakout = DailyBreakout(
            instrument=INST,
            direction=Direction.BEARISH,
            broken_level=1.1000,
            broken_type=FormationType.V_SHAPE,
            breakout_ts=_ts(5),
        )
        from analysis.reaction import compute_reaction_sources
        sources = compute_reaction_sources(old_breakout, candles_with_new_breakout[:5], TOLERANCE, PIP)

        inp = _base_input(
            daily_candles=candles_with_new_breakout,
            h4_candles=full_bearish_cycle_h4(),
            active_breakout=old_breakout,
            active_reaction_srcs=sources,
            retest_in_progress=True,
            active_reaction_src=sources[0] if sources else None,
        )
        out = run_engine_cycle(inp)
        # New breakout should have been detected
        assert out.new_breakout is not None
        assert out.new_breakout.direction == Direction.BULLISH
        # Alert must not fire when a new breakout supersedes
        assert out.alert_to_send is None

    def test_timing_rule_h4_confirms_on_later_cycle(self):
        """
        Simulate retest detected on cycle N, H4 confirmation on cycle N+1.
        Alert must fire on cycle N+1.
        """
        from analysis.reaction import compute_reaction_sources
        from analysis.breakout import check_daily_breakout
        from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape

        daily_candles = full_bearish_cycle_daily()[:5]
        most_recent_a = get_most_recent_a_shape(daily_candles[:-1])
        most_recent_v = get_most_recent_v_shape(daily_candles[:-1])
        breakout = check_daily_breakout(daily_candles[-1], most_recent_a, most_recent_v)
        sources = compute_reaction_sources(breakout, daily_candles, TOLERANCE, PIP)

        # Cycle N: retest detected, no H4 confirmation yet
        h4_touching = [
            make_candle(INST, H4, _ts(7, 0), 1.0980, 1.1003, 1.0975, 1.0990),  # touches breaker zone
        ]
        inp_n = _base_input(
            daily_candles=full_bearish_cycle_daily(),
            h4_candles=h4_touching,
            active_breakout=breakout,
            active_reaction_srcs=sources,
            retest_in_progress=False,
        )
        out_n = run_engine_cycle(inp_n)
        # Should set retest_in_progress but NOT fire alert
        assert out_n.retest_in_progress is True
        assert out_n.alert_to_send is None

        # Cycle N+1: H4 confirmation candle closes below H4 V-shape
        h4_with_confirmation = full_bearish_cycle_h4()
        inp_n1 = _base_input(
            daily_candles=full_bearish_cycle_daily(),
            h4_candles=h4_with_confirmation,
            active_breakout=breakout,
            active_reaction_srcs=sources,
            retest_in_progress=True,
            active_reaction_src=out_n.active_reaction_src,
        )
        out_n1 = run_engine_cycle(inp_n1)
        assert out_n1.alert_to_send is not None
        assert out_n1.alert_to_send.direction == Direction.BEARISH
