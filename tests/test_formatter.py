"""Tests for alerts/formatter.py — alert message composition."""

import pytest
from datetime import datetime

from data.models import (
    AlertRecord,
    BreakoutClassification,
    DailyBreakout,
    Direction,
    Formation,
    FormationType,
    H4BreakoutEvent,
    ReactionSource,
    ReactionSourceType,
    Timeframe,
)
from alerts.formatter import format_alert


INST = "EURUSD"
H4 = Timeframe.H4
D = Timeframe.DAILY


def _make_alert(
    direction: Direction = Direction.BEARISH,
    source_type: ReactionSourceType = ReactionSourceType.POST_BREAKOUT_DAILY_OC,
    classification: BreakoutClassification = BreakoutClassification.EXTERNAL,
) -> AlertRecord:
    ts = datetime(2024, 1, 7, 20, 0, 0)

    daily_breakout = DailyBreakout(
        instrument=INST,
        direction=direction,
        broken_level=1.1000,
        broken_type=FormationType.V_SHAPE if direction == Direction.BEARISH else FormationType.A_SHAPE,
        breakout_ts=datetime(2024, 1, 5),
    )
    reaction_source = ReactionSource(
        instrument=INST,
        source_type=source_type,
        direction=direction,
        level=1.0975,
        level_band_low=1.0970,
        level_band_high=1.0980,
        daily_breakout_ts=datetime(2024, 1, 5),
    )
    h4_formation = Formation(
        instrument=INST,
        timeframe=H4,
        formation_type=FormationType.V_SHAPE,
        direction=Direction.BULLISH,
        level=1.0960,
        established_at=datetime(2024, 1, 7, 16),
        candle_1_ts=datetime(2024, 1, 7, 12),
        candle_2_ts=datetime(2024, 1, 7, 16),
    )
    h4_event = H4BreakoutEvent(
        instrument=INST,
        direction=direction,
        classification=classification,
        formation_broken=h4_formation,
        confirmation_ts=ts,
    )
    return AlertRecord(
        instrument=INST,
        direction=direction,
        daily_breakout=daily_breakout,
        reaction_source=reaction_source,
        h4_event=h4_event,
        fired_at=ts,
    )


class TestFormatAlert:
    def test_sell_bias_header_present(self):
        alert = _make_alert(Direction.BEARISH)
        text = format_alert(alert)
        assert "SELL BIAS CONFIRMED" in text
        assert INST in text

    def test_buy_bias_header_present(self):
        alert = _make_alert(Direction.BULLISH, source_type=ReactionSourceType.DAILY_BREAKER)
        text = format_alert(alert)
        assert "BUY BIAS CONFIRMED" in text

    def test_daily_h4_aligned_line(self):
        alert = _make_alert()
        text = format_alert(alert)
        assert "Daily → H4 aligned" in text

    def test_breakout_direction_label(self):
        alert = _make_alert(Direction.BEARISH)
        text = format_alert(alert)
        assert "Daily breakout: Bearish" in text

    def test_h4_classification_external(self):
        alert = _make_alert(classification=BreakoutClassification.EXTERNAL)
        text = format_alert(alert)
        assert "External" in text

    def test_h4_classification_internal(self):
        alert = _make_alert(classification=BreakoutClassification.INTERNAL)
        text = format_alert(alert)
        assert "Internal" in text

    def test_disclaimer_present(self):
        text = format_alert(_make_alert())
        assert "not an entry signal" in text

    def test_all_four_source_types_render(self):
        for source_type in ReactionSourceType:
            alert = _make_alert(source_type=source_type)
            text = format_alert(alert)
            assert "Daily reaction source:" in text
            assert len(text) > 200  # substantive alert text

    def test_post_breakout_oc_includes_direction(self):
        alert = _make_alert(
            direction=Direction.BEARISH,
            source_type=ReactionSourceType.POST_BREAKOUT_DAILY_OC,
        )
        text = format_alert(alert)
        assert "Post-breakout" in text
        # direction label should appear in source name
        assert "Bearish" in text or "bearish" in text

    def test_daily_breaker_source_description(self):
        alert = _make_alert(source_type=ReactionSourceType.DAILY_BREAKER)
        text = format_alert(alert)
        assert "Daily Breaker" in text

    def test_oc_inside_range_description(self):
        alert = _make_alert(source_type=ReactionSourceType.OC_INSIDE_RANGE)
        text = format_alert(alert)
        assert "OC inside Daily range" in text

    def test_av_inside_range_description(self):
        alert = _make_alert(source_type=ReactionSourceType.AV_INSIDE_RANGE)
        text = format_alert(alert)
        assert "A/V" in text

    def test_reason_line_present(self):
        text = format_alert(_make_alert())
        assert "Reason:" in text
