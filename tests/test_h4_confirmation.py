"""Tests for analysis/h4_confirmation.py — H4 breakout validation."""

import pytest
from datetime import datetime

from data.models import BreakoutClassification, Direction, FormationType, Timeframe
from analysis.h4_confirmation import (
    check_h4_breakout,
    find_outer_h4_formation,
    find_inner_h4_formations,
)
from tests.fixtures.candles import (
    full_bearish_cycle_h4,
    make_candle,
    INST,
    H4,
    _ts,
)


class TestFindOuterH4Formation:
    def test_finds_outer_v_shape_for_bearish(self):
        candles = full_bearish_cycle_h4()
        # V-shape established on candle[4] (bullish) + candle[4] wait —
        # candle[3]=bullish, candle[4]=bearish → V-shape at candle[3].body_low
        history = candles[:-1]  # exclude confirmation candle
        outer = find_outer_h4_formation(history, Direction.BEARISH)
        assert outer is not None
        assert outer.formation_type == FormationType.V_SHAPE

    def test_finds_outer_a_shape_for_bullish(self):
        """Two H4 candles: bullish → bearish. Most recent A-shape is the outer boundary."""
        candles = [
            make_candle(INST, H4, _ts(1, 0), 1.1000, 1.1050, 1.0990, 1.1040),  # bullish
            make_candle(INST, H4, _ts(1, 4), 1.1040, 1.1050, 1.1010, 1.1020),  # bearish → A-shape
        ]
        outer = find_outer_h4_formation(candles, Direction.BULLISH)
        assert outer is not None
        assert outer.formation_type == FormationType.A_SHAPE
        assert outer.level == pytest.approx(1.1040)

    def test_returns_none_when_no_formation(self):
        candles = [
            make_candle(INST, H4, _ts(1, 0), 1.1000, 1.1050, 1.0990, 1.1040),  # bullish only
        ]
        assert find_outer_h4_formation(candles, Direction.BEARISH) is None


class TestFindInnerH4Formations:
    def test_inner_formations_after_outer(self):
        """Formations established after the outer are classified as inner."""
        candles = [
            make_candle(INST, H4, _ts(1, 0), 1.1050, 1.1060, 1.0970, 1.1000),  # bearish
            make_candle(INST, H4, _ts(1, 4), 1.1000, 1.1020, 1.0990, 1.1010),  # bullish → outer V-shape
            make_candle(INST, H4, _ts(1, 8), 1.1010, 1.1020, 1.0990, 1.0995),  # bearish
            make_candle(INST, H4, _ts(1, 12), 1.0995, 1.1010, 1.0985, 1.1000), # bullish → inner V-shape
        ]
        outer = find_outer_h4_formation(candles[:2], Direction.BEARISH)
        assert outer is not None
        inner = find_inner_h4_formations(candles, Direction.BEARISH, outer)
        assert len(inner) == 1
        assert inner[0].established_at > outer.established_at


class TestCheckH4Breakout:
    def test_external_bearish_breakout(self):
        candles = full_bearish_cycle_h4()
        history = candles[:-1]   # formation window
        confirmation = candles[-1]  # the candle that closes below V-shape
        result = check_h4_breakout(confirmation, Direction.BEARISH, history)
        assert result is not None
        assert result.direction == Direction.BEARISH
        assert result.classification == BreakoutClassification.EXTERNAL
        assert result.confirmation_ts == confirmation.timestamp

    def test_body_close_rule_enforced(self):
        """Wick goes below V-shape level but close stays above — no confirmation."""
        candles = full_bearish_cycle_h4()
        history = candles[:-1]
        # Replace confirmation candle with a wick-only candle
        wick_candle = make_candle(
            INST, H4, _ts(7, 20),
            open_=1.0960, high=1.0965, low=1.0930, close=1.0965  # close ABOVE V-level
        )
        result = check_h4_breakout(wick_candle, Direction.BEARISH, history)
        assert result is None

    def test_direction_alignment_required(self):
        """Bullish H4 candle does not confirm bearish Daily direction."""
        candles = full_bearish_cycle_h4()
        history = candles[:-1]
        bullish_candle = make_candle(INST, H4, _ts(7, 20), 1.0960, 1.1000, 1.0950, 1.0990)
        result = check_h4_breakout(bullish_candle, Direction.BEARISH, history)
        assert result is None

    def test_no_confirmation_without_formation(self):
        """If there are no H4 formations in the history, no breakout can be confirmed."""
        single_candle_history = [
            make_candle(INST, H4, _ts(1, 0), 1.1000, 1.1050, 1.0990, 1.0980),  # bearish only
        ]
        # Only one bearish candle — no V-shape (need bear→bull pair)
        confirmation = make_candle(INST, H4, _ts(1, 4), 1.0980, 1.0985, 1.0950, 1.0960)
        result = check_h4_breakout(confirmation, Direction.BEARISH, single_candle_history)
        assert result is None

    def test_internal_classification_for_later_formation(self):
        """If a smaller inner V-shape forms after the outer, breaking it is INTERNAL."""
        # Build: outer V at time 4, inner V at time 12, confirmation at time 16
        candles = [
            make_candle(INST, H4, _ts(1, 0), 1.1000, 1.1010, 1.0970, 1.0980),  # bearish
            make_candle(INST, H4, _ts(1, 4), 1.0980, 1.1000, 1.0975, 1.0990),  # bullish → outer V at 1.0980
            make_candle(INST, H4, _ts(1, 8), 1.0990, 1.0995, 1.0978, 1.0982),  # bearish
            make_candle(INST, H4, _ts(1, 12), 1.0982, 1.0990, 1.0978, 1.0985), # bullish → inner V at 1.0982
        ]
        # Confirmation: close below inner V (1.0982) but above outer V (1.0980)
        # In our logic, outer is checked first. close < outer.level? 1.0981 < 1.0980? No.
        # So outer not triggered. Inner: 1.0981 < 1.0982? Yes → INTERNAL.
        confirmation = make_candle(INST, H4, _ts(1, 16), 1.0985, 1.0988, 1.0975, 1.0981)
        result = check_h4_breakout(confirmation, Direction.BEARISH, candles)
        assert result is not None
        assert result.classification == BreakoutClassification.INTERNAL
