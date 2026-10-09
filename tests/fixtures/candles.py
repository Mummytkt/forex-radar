"""
Hand-crafted OHLCV candle sequences for unit tests.

All prices are exact by design so test assertions can be precise.
All timestamps are naive UTC. Volume is irrelevant to the strategy — set to 0.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from data.models import Candle, Timeframe


def _ts(day: int, hour: int = 0) -> datetime:
    return datetime(2024, 1, day, hour, 0, 0)


def make_candle(
    instrument: str,
    timeframe: Timeframe,
    ts: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        instrument=instrument,
        timeframe=timeframe,
        timestamp=ts,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=0.0,
    )


INST = "EURUSD"
D = Timeframe.DAILY
H4 = Timeframe.H4


# ── A-shape sequences ─────────────────────────────────────────────────────────

def a_shape_basic() -> list[Candle]:
    """
    Two candles: bullish (1.0900 → 1.1000) then bearish (1.1000 → 1.0950).
    Expected A-shape level = 1.1000 (body_high of bullish candle).
    """
    return [
        make_candle(INST, D, _ts(1), 1.0900, 1.1050, 1.0880, 1.1000),  # bullish
        make_candle(INST, D, _ts(2), 1.1000, 1.1010, 1.0930, 1.0950),  # bearish
    ]


def a_shape_with_tall_wick() -> list[Candle]:
    """
    Bullish candle with a high wick. The level should be body_high (1.1000),
    NOT the wick high (1.1080).
    """
    return [
        make_candle(INST, D, _ts(1), 1.0900, 1.1080, 1.0880, 1.1000),  # bullish, wick to 1.1080
        make_candle(INST, D, _ts(2), 1.1000, 1.1010, 1.0930, 1.0950),  # bearish
    ]


# ── V-shape sequences ─────────────────────────────────────────────────────────

def v_shape_basic() -> list[Candle]:
    """
    Two candles: bearish (1.1050 → 1.1000) then bullish (1.1000 → 1.1030).
    Expected V-shape level = 1.1000 (body_low of bearish candle).
    """
    return [
        make_candle(INST, D, _ts(1), 1.1050, 1.1060, 1.0970, 1.1000),  # bearish
        make_candle(INST, D, _ts(2), 1.1000, 1.1040, 1.0990, 1.1030),  # bullish
    ]


def v_shape_with_low_wick() -> list[Candle]:
    """
    Bearish candle with a low wick. The level should be body_low (1.1000),
    NOT the wick low (1.0930).
    """
    return [
        make_candle(INST, D, _ts(1), 1.1050, 1.1060, 1.0930, 1.1000),  # bearish, wick to 1.0930
        make_candle(INST, D, _ts(2), 1.1000, 1.1040, 1.0990, 1.1030),  # bullish
    ]


# ── OC sequences ──────────────────────────────────────────────────────────────

def oc_bullish_two_candles() -> list[Candle]:
    """
    Two bullish candles: closes at 1.1010 and 1.1030.
    Expected OC level = (1.1010 + 1.1030) / 2 = 1.1020.
    """
    return [
        make_candle(INST, D, _ts(1), 1.1000, 1.1020, 1.0990, 1.1010),  # bullish
        make_candle(INST, D, _ts(2), 1.1010, 1.1040, 1.1000, 1.1030),  # bullish
    ]


def oc_run_of_three() -> list[Candle]:
    """
    Three consecutive bullish candles: closes at 1.1010, 1.1030, 1.1050.
    Expected: two OC levels:
      OC1 = (1.1010 + 1.1030) / 2 = 1.1020  (established at candle[1])
      OC2 = (1.1030 + 1.1050) / 2 = 1.1040  (established at candle[2])
    """
    return [
        make_candle(INST, D, _ts(1), 1.1000, 1.1020, 1.0990, 1.1010),
        make_candle(INST, D, _ts(2), 1.1010, 1.1040, 1.1000, 1.1030),
        make_candle(INST, D, _ts(3), 1.1030, 1.1060, 1.1020, 1.1050),
    ]


def oc_bearish_two_candles() -> list[Candle]:
    """
    Two bearish candles: closes at 1.1020 and 1.1000.
    Expected OC level = (1.1020 + 1.1000) / 2 = 1.1010.
    """
    return [
        make_candle(INST, D, _ts(1), 1.1040, 1.1050, 1.1010, 1.1020),  # bearish
        make_candle(INST, D, _ts(2), 1.1020, 1.1030, 1.0990, 1.1000),  # bearish
    ]


# ── Daily breakout sequences ──────────────────────────────────────────────────

def bearish_breakout_sequence() -> list[Candle]:
    """
    Candles leading to a bearish Daily breakout.

    Candle 1 (bullish) + Candle 2 (bearish) → V-shape at 1.1000.
    Then bullish bounce: Candle 3, Candle 4.
    Candle 5: bearish close BELOW 1.1000 → bearish breakout.
    Candle 6: bearish (wick only goes below 1.1000 but close stays above — no break).
    """
    return [
        # V-shape formation
        make_candle(INST, D, _ts(1), 1.1050, 1.1060, 1.0970, 1.1000),  # bearish, body_low=1.1000
        make_candle(INST, D, _ts(2), 1.1000, 1.1040, 1.0990, 1.1030),  # bullish → V-shape at 1.1000
        # Bounce up
        make_candle(INST, D, _ts(3), 1.1030, 1.1080, 1.1010, 1.1060),  # bullish
        make_candle(INST, D, _ts(4), 1.1060, 1.1100, 1.1020, 1.1040),  # bearish → A-shape at 1.1060
        # Bearish breakout candle
        make_candle(INST, D, _ts(5), 1.1040, 1.1050, 1.0980, 1.0990),  # bearish, close < 1.1000 ✓
    ]


def wick_no_breakout_sequence() -> list[Candle]:
    """
    Wick penetrates below V-shape level but candle CLOSES above it — no breakout.
    """
    return [
        make_candle(INST, D, _ts(1), 1.1050, 1.1060, 1.0970, 1.1000),  # bearish V-shape
        make_candle(INST, D, _ts(2), 1.1000, 1.1040, 1.0990, 1.1030),  # bullish
        # Wick below 1.1000 but close above — NOT a breakout
        make_candle(INST, D, _ts(3), 1.1030, 1.1040, 1.0950, 1.1010),  # bearish wick, close > 1.1000
    ]


# ── Full confirmation cycle ───────────────────────────────────────────────────

def full_bearish_cycle_daily() -> list[Candle]:
    """
    Complete Daily candle sequence ending with a bearish breakout.
    V-shape established at 1.1000; bearish breakout on candle 5.
    Post-breakout bearish OC forms on candles 5+6.
    """
    return [
        make_candle(INST, D, _ts(1), 1.1050, 1.1060, 1.0970, 1.1000),  # bearish, body_low=1.1000
        make_candle(INST, D, _ts(2), 1.1000, 1.1040, 1.0990, 1.1030),  # bullish → V-shape at 1.1000
        make_candle(INST, D, _ts(3), 1.1030, 1.1080, 1.1010, 1.1060),  # bullish
        make_candle(INST, D, _ts(4), 1.1060, 1.1100, 1.1020, 1.1040),  # bearish → A-shape at 1.1060
        make_candle(INST, D, _ts(5), 1.1040, 1.1050, 1.0980, 1.0990),  # bearish BREAKOUT (close < 1.1000)
        make_candle(INST, D, _ts(6), 1.0990, 1.1000, 1.0940, 1.0960),  # bearish (post-breakout run)
        # OC from candles 5 & 6: (1.0990 + 1.0960) / 2 = 1.0975
        make_candle(INST, D, _ts(7), 1.0960, 1.1010, 1.0950, 1.1000),  # bullish retracement → near breaker
    ]


def full_bearish_cycle_h4() -> list[Candle]:
    """
    H4 candles: price reacts from a level zone, forms a V-shape, then breaks below it.

    H4 candle 1-3: bearish leg down.
    H4 candle 4 (bullish) + H4 candle 5 (bearish) → V-shape at 1.0960.
    H4 candle 6: close below 1.0960 → H4 bearish breakout (EXTERNAL).
    """
    return [
        make_candle(INST, H4, _ts(7, 0),  1.1000, 1.1010, 1.0980, 1.0990),  # bearish
        make_candle(INST, H4, _ts(7, 4),  1.0990, 1.0995, 1.0965, 1.0970),  # bearish
        make_candle(INST, H4, _ts(7, 8),  1.0970, 1.0980, 1.0950, 1.0965),  # bearish
        make_candle(INST, H4, _ts(7, 12), 1.0965, 1.0985, 1.0955, 1.0980),  # bullish
        make_candle(INST, H4, _ts(7, 16), 1.0980, 1.0985, 1.0955, 1.0960),  # bearish → V-shape at 1.0960
        make_candle(INST, H4, _ts(7, 20), 1.0960, 1.0965, 1.0930, 1.0940),  # bearish CLOSE < 1.0960 ✓
    ]
