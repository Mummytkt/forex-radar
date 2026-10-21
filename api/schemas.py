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
    alert_classification: str = "origin"
    alert_text: str
    fired_at: str


class AlertsPage(BaseModel):
    items: list[AlertItem]
    total: int


class AlertPreferences(BaseModel):
    alertExternal: bool
    alertInternal: bool
    newsAlerts: bool = True


class AlertPreferencesUpdate(BaseModel):
    alertExternal: bool | None = None
    alertInternal: bool | None = None
    newsAlerts: bool | None = None


class VideoEntry(BaseModel):
    title: str
    url: str


class VideoAdd(BaseModel):
    title: str
    url: str


class InstrumentDetail(BaseModel):
    overview: InstrumentOverview
    active_sources: list[dict]
    recent_alerts: list[AlertItem]


class InstrumentsUpdate(BaseModel):
    instruments: list[str]


class JournalEntryCreate(BaseModel):
    trade_date: str
    instrument: str
    direction: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    pips: Optional[float] = None
    rr_ratio: Optional[float] = None
    amount_risked: Optional[float] = None
    amount_aimed: Optional[float] = None
    result: str = "open"
    setup_type: str = "other"
    setup_type_notes: Optional[str] = None
    trade_type: str = "live"
    h4_break_type: Optional[str] = None
    entry_date: Optional[str] = None
    exit_date: Optional[str] = None
    trigger_time: Optional[str] = None
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    session: Optional[str] = None
    notes: Optional[str] = None


class JournalEntry(JournalEntryCreate):
    id: int
    created_at: str


class JournalEntryUpdate(BaseModel):
    trade_date: Optional[str] = None
    instrument: Optional[str] = None
    direction: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    pips: Optional[float] = None
    rr_ratio: Optional[float] = None
    amount_risked: Optional[float] = None
    amount_aimed: Optional[float] = None
    result: Optional[str] = None
    setup_type: Optional[str] = None
    setup_type_notes: Optional[str] = None
    trade_type: Optional[str] = None
    h4_break_type: Optional[str] = None
    entry_date: Optional[str] = None
    exit_date: Optional[str] = None
    trigger_time: Optional[str] = None
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    session: Optional[str] = None
    notes: Optional[str] = None
