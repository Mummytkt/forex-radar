from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"

    def opposite(self) -> Direction:
        return Direction.BEARISH if self == Direction.BULLISH else Direction.BULLISH


class Timeframe(str, Enum):
    DAILY = "1day"
    H4 = "4h"
    H1 = "1h"    # intermediate — used when building NY-session H4 from 1h candles


class FormationType(str, Enum):
    A_SHAPE = "A_shape"
    V_SHAPE = "V_shape"
    OC = "OC"


class BreakoutClassification(str, Enum):
    EXTERNAL = "external"
    INTERNAL = "internal"


class AlertClassification(str, Enum):
    ORIGIN = "origin"
    CONTINUATION_ASHAPE = "continuation_ashape"
    CONTINUATION_H4_OC = "continuation_h4oc"
    CONTINUATION_H4_BREAKER = "continuation_h4breaker"
    H4_BREAKER_ORIGIN = "h4_breaker_origin"
    H4_BREAKOUT_CONT = "h4_breakout_cont"
    H4_BREAKER_CONT = "h4_breaker_cont"
    H4_OC_CONT = "h4_oc_cont"
    H4_ENGULFING_CONT = "h4_engulfing_cont"


class ReactionSourceType(str, Enum):
    DAILY_BREAKER = "daily_breaker"
    OC_INSIDE_RANGE = "oc_inside_range"
    AV_INSIDE_RANGE = "av_inside_range"
    POST_BREAKOUT_DAILY_OC = "post_breakout_daily_oc"


@dataclass
class Candle:
    instrument: str
    timeframe: Timeframe
    timestamp: datetime  # naive UTC, candle open time
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def is_bullish(self) -> bool:
        # doji (open == close) treated as bullish
        return self.close >= self.open

    @property
    def is_bearish(self) -> bool:
        return not self.is_bullish

    @property
    def body_high(self) -> float:
        return max(self.open, self.close)

    @property
    def body_low(self) -> float:
        return min(self.open, self.close)

    @property
    def body_size(self) -> float:
        return self.body_high - self.body_low


@dataclass
class Formation:
    """A detected A-shape, V-shape, or OC level on a given timeframe."""
    instrument: str
    timeframe: Timeframe
    formation_type: FormationType
    # A-shape → BEARISH (resistance that bulls must break upward)
    # V-shape → BULLISH (support that bears must break downward)
    # OC      → matches the run direction
    direction: Direction
    level: float               # H4: body high (A) / body low (V); Daily: wick; OC: first candle's close
    established_at: datetime   # timestamp of the completing candle
    candle_1_ts: datetime
    candle_2_ts: datetime
    is_active: bool = True
    db_id: Optional[int] = field(default=None, repr=False)


@dataclass
class DailyBreakout:
    instrument: str
    direction: Direction
    broken_level: float        # the A/V body level that was crossed
    broken_type: FormationType  # A_SHAPE or V_SHAPE (OC levels are not broken for Daily bias)
    breakout_ts: datetime      # open timestamp of the candle that closed beyond the level
    is_active: bool = True
    db_id: Optional[int] = field(default=None, repr=False)


@dataclass
class ReactionSource:
    instrument: str
    source_type: ReactionSourceType
    direction: Direction        # expected reaction direction (= Daily breakout direction)
    level: float
    level_band_low: float
    level_band_high: float
    daily_breakout_ts: datetime  # links back to which breakout this was computed for
    is_active: bool = True
    db_id: Optional[int] = field(default=None, repr=False)


@dataclass
class H4BreakoutEvent:
    instrument: str
    direction: Direction
    classification: BreakoutClassification
    formation_broken: Formation  # the specific H4 A/V formation whose level was crossed
    confirmation_ts: datetime    # open timestamp of the H4 candle that confirmed


@dataclass
class AlertRecord:
    instrument: str
    direction: Direction
    daily_breakout: DailyBreakout
    reaction_source: Optional[ReactionSource]   # None for continuation alerts
    h4_event: Optional[H4BreakoutEvent]         # None for H4 OC continuation
    fired_at: datetime
    classification: AlertClassification = AlertClassification.ORIGIN
    h4_oc_level: Optional[float] = None         # set for CONTINUATION_H4_OC
    h4_breaker_level: Optional[float] = None    # set for CONTINUATION_H4_BREAKER
    daily_level_context: str = "internal"       # "external" or "internal" Daily level
    weekly: Optional[dict] = None               # Weekly storyline (wk_rel, wk_dir, wk_level, wk_src, wk_src_level, wk_cls)
