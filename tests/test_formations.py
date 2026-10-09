"""Tests for analysis/formations.py — pure formation detection logic."""

import pytest
from datetime import datetime

from data.models import Direction, FormationType, Timeframe
from analysis.formations import (
    detect_a_shape,
    detect_v_shape,
    detect_oc_levels,
    detect_all_formations,
    get_most_recent_a_shape,
    get_most_recent_v_shape,
)
from tests.fixtures.candles import (
    a_shape_basic,
    a_shape_with_tall_wick,
    v_shape_basic,
    v_shape_with_low_wick,
    oc_bullish_two_candles,
    oc_run_of_three,
    oc_bearish_two_candles,
    INST,
)


class TestAShape:
    def test_basic_detection(self):
        candles = a_shape_basic()
        result = detect_a_shape(candles)
        assert len(result) == 1
        f = result[0]
        assert f.formation_type == FormationType.A_SHAPE
        assert f.direction == Direction.BEARISH
        assert f.level == pytest.approx(1.1000)  # body_high of bullish candle
        assert f.established_at == candles[1].timestamp
        assert f.candle_1_ts == candles[0].timestamp
        assert f.candle_2_ts == candles[1].timestamp

    def test_level_is_body_high_not_wick(self):
        """Level must be max(open, close), NOT the wick high."""
        candles = a_shape_with_tall_wick()
        result = detect_a_shape(candles)
        assert len(result) == 1
        assert result[0].level == pytest.approx(1.1000)  # body_high, not 1.1080 (wick)

    def test_no_false_positive_on_two_bullish(self):
        candles = a_shape_basic()
        candles[1] = candles[1].__class__(
            instrument=candles[1].instrument,
            timeframe=candles[1].timeframe,
            timestamp=candles[1].timestamp,
            open=candles[1].open,
            high=candles[1].high,
            low=candles[1].low,
            close=candles[1].open + 0.0020,  # make it bullish
            volume=0.0,
        )
        result = detect_a_shape(candles)
        assert len(result) == 0

    def test_multiple_a_shapes_in_window(self):
        from tests.fixtures.candles import bearish_breakout_sequence
        candles = bearish_breakout_sequence()
        # Candles 0(bear)→1(bull) is NOT an A-shape (bear→bull = V-shape)
        # Candles 2(bull)→3(bear) = A-shape at body_high of candle 2
        result = detect_a_shape(candles)
        assert len(result) == 1
        assert result[0].level == pytest.approx(candles[2].body_high)

    def test_get_most_recent_a_shape(self):
        from tests.fixtures.candles import bearish_breakout_sequence
        candles = bearish_breakout_sequence()
        result = get_most_recent_a_shape(candles)
        assert result is not None
        assert result.level == pytest.approx(candles[2].body_high)

    def test_empty_list(self):
        assert detect_a_shape([]) == []

    def test_single_candle(self):
        candles = a_shape_basic()[:1]
        assert detect_a_shape(candles) == []


class TestVShape:
    def test_basic_detection(self):
        candles = v_shape_basic()
        result = detect_v_shape(candles)
        assert len(result) == 1
        f = result[0]
        assert f.formation_type == FormationType.V_SHAPE
        assert f.direction == Direction.BULLISH
        assert f.level == pytest.approx(1.1000)  # body_low of bearish candle
        assert f.established_at == candles[1].timestamp

    def test_level_is_body_low_not_wick(self):
        """Level must be min(open, close), NOT the wick low."""
        candles = v_shape_with_low_wick()
        result = detect_v_shape(candles)
        assert len(result) == 1
        assert result[0].level == pytest.approx(1.1000)  # body_low, not 1.0930 (wick)

    def test_get_most_recent_v_shape(self):
        candles = v_shape_basic()
        result = get_most_recent_v_shape(candles)
        assert result is not None
        assert result.level == pytest.approx(1.1000)


class TestOCLevels:
    def test_bullish_two_candles(self):
        candles = oc_bullish_two_candles()
        result = detect_oc_levels(candles)
        assert len(result) == 1
        oc = result[0]
        assert oc.formation_type == FormationType.OC
        assert oc.direction == Direction.BULLISH
        assert oc.level == pytest.approx((1.1010 + 1.1030) / 2)  # 1.1020
        assert oc.established_at == candles[1].timestamp

    def test_bearish_two_candles(self):
        candles = oc_bearish_two_candles()
        result = detect_oc_levels(candles)
        assert len(result) == 1
        oc = result[0]
        assert oc.direction == Direction.BEARISH
        assert oc.level == pytest.approx((1.1020 + 1.1000) / 2)  # 1.1010

    def test_run_of_three_produces_two_levels(self):
        """A run of 3 same-direction candles must produce exactly 2 OC levels."""
        candles = oc_run_of_three()
        result = detect_oc_levels(candles)
        assert len(result) == 2
        # First OC: candles 0 and 1
        assert result[0].level == pytest.approx((1.1010 + 1.1030) / 2)  # 1.1020
        assert result[0].established_at == candles[1].timestamp
        # Second OC: candles 1 and 2
        assert result[1].level == pytest.approx((1.1030 + 1.1050) / 2)  # 1.1040
        assert result[1].established_at == candles[2].timestamp

    def test_direction_break_resets_run(self):
        """A direction change breaks the run; no OC spans the gap."""
        candles = a_shape_basic()  # bull → bear: two separate runs of length 1
        result = detect_oc_levels(candles)
        assert len(result) == 0  # each run has only 1 candle → no pairs

    def test_empty_list(self):
        assert detect_oc_levels([]) == []

    def test_single_candle(self):
        candles = a_shape_basic()[:1]
        assert detect_oc_levels(candles) == []


class TestDetectAll:
    def test_returns_sorted_by_established_at(self):
        from tests.fixtures.candles import bearish_breakout_sequence
        candles = bearish_breakout_sequence()
        result = detect_all_formations(candles)
        timestamps = [f.established_at for f in result]
        assert timestamps == sorted(timestamps)

    def test_detects_mixed_types(self):
        from tests.fixtures.candles import bearish_breakout_sequence
        candles = bearish_breakout_sequence()
        result = detect_all_formations(candles)
        types = {f.formation_type for f in result}
        assert FormationType.V_SHAPE in types
        assert FormationType.A_SHAPE in types
