"""Tests for analysis/reaction.py — reaction source identification."""

import pytest
from datetime import datetime

from data.models import Direction, FormationType, ReactionSourceType, Timeframe
from analysis.reaction import compute_reaction_sources, is_price_retesting_source
from analysis.breakout import check_daily_breakout
from analysis.formations import get_most_recent_a_shape, get_most_recent_v_shape
from tests.fixtures.candles import (
    full_bearish_cycle_daily,
    make_candle,
    INST,
    D,
    _ts,
)


TOLERANCE_PIPS = 5.0
PIP_SIZE = 0.0001


def _make_bearish_breakout(candles):
    history = candles[:-1]
    bk_candle = candles[-1]
    most_recent_a = get_most_recent_a_shape(history)
    most_recent_v = get_most_recent_v_shape(history)
    return check_daily_breakout(bk_candle, most_recent_a, most_recent_v)


class TestComputeReactionSources:
    def test_daily_breaker_always_present(self):
        candles = full_bearish_cycle_daily()[:5]
        breakout = _make_bearish_breakout(candles)
        assert breakout is not None
        sources = compute_reaction_sources(breakout, candles, TOLERANCE_PIPS, PIP_SIZE)
        breaker_sources = [s for s in sources if s.source_type == ReactionSourceType.DAILY_BREAKER]
        assert len(breaker_sources) == 1
        assert breaker_sources[0].level == pytest.approx(breakout.broken_level)

    def test_daily_breaker_level_equals_broken_level(self):
        candles = full_bearish_cycle_daily()[:5]
        breakout = _make_bearish_breakout(candles)
        sources = compute_reaction_sources(breakout, candles, TOLERANCE_PIPS, PIP_SIZE)
        breaker = next(s for s in sources if s.source_type == ReactionSourceType.DAILY_BREAKER)
        assert breaker.level == pytest.approx(1.1000)  # the V-shape body_low that was broken

    def test_tolerance_band_computed_correctly(self):
        candles = full_bearish_cycle_daily()[:5]
        breakout = _make_bearish_breakout(candles)
        sources = compute_reaction_sources(breakout, candles, 5.0, 0.0001)
        breaker = next(s for s in sources if s.source_type == ReactionSourceType.DAILY_BREAKER)
        expected_offset = 5.0 * 0.0001
        assert breaker.level_band_low == pytest.approx(breaker.level - expected_offset)
        assert breaker.level_band_high == pytest.approx(breaker.level + expected_offset)

    def test_post_breakout_oc_detected(self):
        """Two consecutive bearish Daily candles after the breakout → post-breakout OC."""
        candles = full_bearish_cycle_daily()
        # Candles 0-4 = pre/breakout. Candles 5-6 = post-breakout bearish run.
        breakout_candles = candles[:5]
        breakout = _make_bearish_breakout(breakout_candles)
        assert breakout is not None
        sources = compute_reaction_sources(breakout, candles, TOLERANCE_PIPS, PIP_SIZE)
        post_oc_sources = [s for s in sources if s.source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC]
        assert len(post_oc_sources) >= 1
        # Expected: (close[4] + close[5]) / 2 = (1.0990 + 1.0960) / 2 = 1.0975
        levels = [s.level for s in post_oc_sources]
        assert any(abs(lvl - 1.0975) < 1e-5 for lvl in levels)

    def test_sources_direction_matches_breakout(self):
        candles = full_bearish_cycle_daily()[:5]
        breakout = _make_bearish_breakout(candles)
        sources = compute_reaction_sources(breakout, candles, TOLERANCE_PIPS, PIP_SIZE)
        for src in sources:
            assert src.direction == Direction.BEARISH

    def test_all_source_instruments_match(self):
        candles = full_bearish_cycle_daily()[:5]
        breakout = _make_bearish_breakout(candles)
        sources = compute_reaction_sources(breakout, candles, TOLERANCE_PIPS, PIP_SIZE)
        for src in sources:
            assert src.instrument == INST


class TestRetestDetection:
    def test_candle_low_in_band_triggers_retest(self):
        from data.models import ReactionSource, ReactionSourceType, Direction
        src = ReactionSource(
            instrument=INST,
            source_type=ReactionSourceType.DAILY_BREAKER,
            direction=Direction.BEARISH,
            level=1.1000,
            level_band_low=1.0995,
            level_band_high=1.1005,
            daily_breakout_ts=_ts(5),
        )
        # Candle whose low touches the band
        candle = make_candle(INST, Timeframe.H4, _ts(7), 1.1020, 1.1025, 1.0998, 1.1010)
        assert is_price_retesting_source(candle, src) is True

    def test_candle_high_in_band_triggers_retest(self):
        from data.models import ReactionSource, ReactionSourceType, Direction
        src = ReactionSource(
            instrument=INST,
            source_type=ReactionSourceType.DAILY_BREAKER,
            direction=Direction.BULLISH,
            level=1.0900,
            level_band_low=1.0895,
            level_band_high=1.0905,
            daily_breakout_ts=_ts(5),
        )
        candle = make_candle(INST, Timeframe.H4, _ts(7), 1.0880, 1.0902, 1.0875, 1.0890)
        assert is_price_retesting_source(candle, src) is True

    def test_candle_entirely_outside_band(self):
        from data.models import ReactionSource, ReactionSourceType, Direction
        src = ReactionSource(
            instrument=INST,
            source_type=ReactionSourceType.DAILY_BREAKER,
            direction=Direction.BEARISH,
            level=1.1000,
            level_band_low=1.0995,
            level_band_high=1.1005,
            daily_breakout_ts=_ts(5),
        )
        candle = make_candle(INST, Timeframe.H4, _ts(7), 1.1050, 1.1070, 1.1020, 1.1060)
        assert is_price_retesting_source(candle, src) is False
