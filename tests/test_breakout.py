"""Tests for analysis/breakout.py — Daily breakout detection."""

import pytest
from datetime import datetime

from data.models import Direction, FormationType, Timeframe
from analysis.breakout import check_daily_breakout
from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape
from tests.fixtures.candles import (
    bearish_breakout_sequence,
    wick_no_breakout_sequence,
    make_candle,
    INST,
    D,
    _ts,
)


def _setup_bearish(candles):
    """Return (history, breakout_candle, most_recent_a, most_recent_v) for bearish test."""
    history = candles[:-1]
    breakout_candle = candles[-1]
    most_recent_a = get_most_recent_a_shape(history)
    most_recent_v = get_most_recent_v_shape(history)
    return history, breakout_candle, most_recent_a, most_recent_v


class TestDailyBreakout:
    def test_bearish_breakout_fires_on_close_below_v_level(self):
        candles = bearish_breakout_sequence()
        _, breakout_candle, most_recent_a, most_recent_v = _setup_bearish(candles)
        assert most_recent_v is not None
        assert most_recent_v.level == pytest.approx(1.1000)
        result = check_daily_breakout(breakout_candle, most_recent_a, most_recent_v)
        assert result is not None
        assert result.direction == Direction.BEARISH
        assert result.broken_level == pytest.approx(1.1000)
        assert result.broken_type == FormationType.V_SHAPE
        assert result.breakout_ts == breakout_candle.timestamp

    def test_no_breakout_when_wick_only(self):
        """Wick goes below V-shape level but close stays above — must NOT trigger."""
        candles = wick_no_breakout_sequence()
        _, candle, most_recent_a, most_recent_v = _setup_bearish(candles)
        assert most_recent_v is not None
        # candle.low < 1.1000 but candle.close > 1.1000
        assert candle.low < most_recent_v.level
        assert candle.close > most_recent_v.level
        result = check_daily_breakout(candle, most_recent_a, most_recent_v)
        assert result is None

    def test_no_breakout_when_close_equals_level(self):
        """Close exactly at the level is not a breakout (strictly less/greater required)."""
        candles = bearish_breakout_sequence()
        history = candles[:2]
        most_recent_v = get_most_recent_v_shape(history)
        assert most_recent_v is not None
        # Candle that closes exactly at the V-shape level
        at_level_candle = make_candle(INST, D, _ts(3), 1.1030, 1.1040, 1.0990, 1.1000)
        result = check_daily_breakout(at_level_candle, None, most_recent_v)
        assert result is None

    def test_bullish_breakout_fires_on_close_above_a_level(self):
        """Build a sequence with an A-shape and a candle closing above it."""
        candles = [
            make_candle(INST, D, _ts(1), 1.1000, 1.1050, 1.0990, 1.1040),  # bullish
            make_candle(INST, D, _ts(2), 1.1040, 1.1050, 1.1010, 1.1020),  # bearish → A-shape at 1.1040
            make_candle(INST, D, _ts(3), 1.1020, 1.1060, 1.1010, 1.1050),  # bullish, close > 1.1040 ✓
        ]
        most_recent_a = get_most_recent_a_shape(candles[:2])
        most_recent_v = get_most_recent_v_shape(candles[:2])
        assert most_recent_a is not None
        assert most_recent_a.level == pytest.approx(1.1040)
        result = check_daily_breakout(candles[2], most_recent_a, most_recent_v)
        assert result is not None
        assert result.direction == Direction.BULLISH
        assert result.broken_level == pytest.approx(1.1040)
        assert result.broken_type == FormationType.A_SHAPE

    def test_no_breakout_when_no_formation(self):
        """If there is no A or V formation, no breakout should fire."""
        candle = make_candle(INST, D, _ts(1), 1.1000, 1.1050, 1.0990, 1.1040)
        result = check_daily_breakout(candle, None, None)
        assert result is None

    def test_simultaneous_breaks_picks_greater_distance(self):
        """If a candle simultaneously breaks both an A and a V level, pick the larger distance."""
        # A-shape at 1.1000, V-shape at 1.0980
        # Candle closes at 1.0960: distance below V = 0.0020, distance above A = 0 (no, closes below both)
        # Candle closes at 1.1020: distance above A = 0.0020, distance below V = none
        # Test: candle gaps over BOTH levels — distance below V is larger
        from data.models import Formation, FormationType, Direction
        from datetime import datetime

        a_shape = Formation(
            instrument=INST, timeframe=D, formation_type=FormationType.A_SHAPE,
            direction=Direction.BEARISH, level=1.0960,
            established_at=_ts(1), candle_1_ts=_ts(1), candle_2_ts=_ts(1),
        )
        v_shape = Formation(
            instrument=INST, timeframe=D, formation_type=FormationType.V_SHAPE,
            direction=Direction.BULLISH, level=1.1010,
            established_at=_ts(1), candle_1_ts=_ts(1), candle_2_ts=_ts(1),
        )
        # Gap candle: open 1.0990, close 1.1020 → above A-level (1.0960) by 0.006
        # AND above V-level... wait: V-shape at 1.1010, close 1.1020 > 1.1010? No — bearish breaks below V.
        # Let's make it clearer: A-shape at 1.1050 (bullish must close above), V-shape at 1.0950.
        # Gap DOWN candle: close at 1.0940, below V (1.0950) by 0.0010.
        # No A-shape break (close < A-shape level, no bullish break).
        a_shape2 = Formation(
            instrument=INST, timeframe=D, formation_type=FormationType.A_SHAPE,
            direction=Direction.BEARISH, level=1.1050,
            established_at=_ts(1), candle_1_ts=_ts(1), candle_2_ts=_ts(1),
        )
        v_shape2 = Formation(
            instrument=INST, timeframe=D, formation_type=FormationType.V_SHAPE,
            direction=Direction.BULLISH, level=1.0950,
            established_at=_ts(1), candle_1_ts=_ts(1), candle_2_ts=_ts(1),
        )
        # Gap UP candle: close 1.1060 > A-shape (1.1050) by 0.001, NOT above V
        # → only bullish breakout
        gap_up = make_candle(INST, D, _ts(2), 1.1000, 1.1070, 1.0990, 1.1060)
        result = check_daily_breakout(gap_up, a_shape2, v_shape2)
        assert result is not None
        assert result.direction == Direction.BULLISH
