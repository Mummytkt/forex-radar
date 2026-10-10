from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class InstrumentOverview(BaseModel):
    instrument: str
    state: str  # IDLE | BREAKOUT_ACTIVE | RETEST_IN_PROGRESS
    direction: Optional[str] = None        # Daily breakout direction (setup, not confirmed)
    last_alert_direction: Optional[str] = None  # Confirmed bias — only set when alert has fired
    breakout_level: Optional[float] = None
    breakout_ts: Optional[str] = None
    last_alert_at: Optional[str] = None
    active_sources_count: int = 0
    last_updated: Optional[str] = None
    category: str


class Stats(BaseModel):
    total_instruments: int
    active_breakouts: int
    retests_in_progress: int
    alerts_today: int
    total_alerts: int


class AlertItem(BaseModel):
    id: int
    instrument: str
    direction: str
    source_type: str
    h4_classification: str
    alert_text: str
    fired_at: str


class AlertsPage(BaseModel):
    items: list[AlertItem]
    total: int


class InstrumentDetail(BaseModel):
    overview: InstrumentOverview
    active_sources: list[dict]
    recent_alerts: list[AlertItem]


class InstrumentsUpdate(BaseModel):
    instruments: list[str]
