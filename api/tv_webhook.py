"""
TradingView Pine Script webhook receiver.

Pine Script fires JSON payloads to POST /api/tv-webhook when formations,
breakouts, retests, and H4 confirmations are detected. This replaces the
Twelve Data polling scheduler with TradingView's own chart data.

Event types received from Pine:
  BREAKOUT        — Daily candle closed beyond A/V formation level (+ tol pips)
  RETEST          — H4 wick touched the Daily Breaker band
  RETEST_CANCELLED — H4 moved away from the band without H4 confirmation
  CONFIRMED       — H4 closed beyond an H4 A/V level → fires Telegram alert
  INVALIDATED     — Daily close returned through broken level → reset to IDLE
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from alerts.formatter import format_alert
from alerts.telegram import send_alert
from config import pip_size_for
from data.models import (
    AlertClassification,
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
from state.repository import (
    InstrumentStateRow,
    deactivate_all_breakouts,
    deactivate_reaction_sources_for_breakout,
    get_active_breakout,
    get_active_reaction_sources,
    get_instrument_state,
    insert_alert,
    insert_breakout,
    insert_formation,
    insert_reaction_sources,
    upsert_instrument_state,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic model for incoming Pine payloads ─────────────────────────────────

class TVWebhookPayload(BaseModel):
    secret: str
    type: str                           # BREAKOUT | RETEST | RETEST_CANCELLED | CONFIRMED | INVALIDATED
    instrument: str                     # e.g. "USDCHF" or "USD/CHF"
    direction: Optional[str] = None     # "bullish" | "bearish"
    level: Optional[float] = None       # daily broken level (BREAKOUT)
    source: Optional[str] = None        # "daily_breaker" | "inside_range" | "post_breakout_oc"
    h4_class: Optional[str] = None      # "external" | "internal" (CONFIRMED)
    breakout_level: Optional[float] = None   # daily broken level
    source_level: Optional[float] = None     # reaction source level (OC midpoint, or bo_level for others)
    h4_level: Optional[float] = None    # H4 formation level (CONFIRMED)


def _source_type_from_str(source: Optional[str]) -> ReactionSourceType:
    if source == "post_breakout_oc":
        return ReactionSourceType.POST_BREAKOUT_DAILY_OC
    if source == "inside_range":
        return ReactionSourceType.AV_INSIDE_RANGE
    return ReactionSourceType.DAILY_BREAKER


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/tv-webhook")
async def tv_webhook(payload: TVWebhookPayload, request: Request) -> dict:
    config = request.app.state.config
    conn   = request.app.state.conn

    # Verify shared secret
    if payload.secret != config.tv_webhook_secret:
        logger.warning("TV webhook rejected: bad secret (instrument=%s)", payload.instrument)
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Normalise instrument name: "USD/CHF" → "USDCHF"
    instrument = payload.instrument.replace("/", "").upper()
    event_type = payload.type.upper()

    logger.info("TV webhook: %s %s", event_type, instrument)

    if event_type == "BREAKOUT":
        await _handle_breakout(conn, config, instrument, payload)
    elif event_type == "RETEST":
        _handle_retest(conn, instrument, payload)
    elif event_type == "RETEST_CANCELLED":
        _handle_retest_cancelled(conn, instrument)
    elif event_type == "CONFIRMED":
        await _handle_confirmed(conn, config, instrument, payload)
    elif event_type == "INVALIDATED":
        _handle_invalidated(conn, instrument)
    else:
        logger.warning("Unknown TV webhook type: %s", event_type)

    return {"status": "ok"}


# ── Event handlers ────────────────────────────────────────────────────────────

async def _handle_breakout(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    direction = Direction(payload.direction)
    broken_type = FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE

    # Deactivate any prior breakout and its reaction sources
    old_state = get_instrument_state(conn, instrument)
    if old_state and old_state.active_breakout_id:
        deactivate_reaction_sources_for_breakout(conn, old_state.active_breakout_id)
    deactivate_all_breakouts(conn, instrument)

    # Create new breakout record
    breakout = DailyBreakout(
        instrument=instrument,
        direction=direction,
        broken_level=payload.level,
        broken_type=broken_type,
        breakout_ts=datetime.utcnow(),
    )
    breakout_id = insert_breakout(conn, breakout)
    breakout.db_id = breakout_id

    # Create Daily Breaker reaction source (the broken A/V level ± tolerance band)
    pip_size = pip_size_for(instrument)
    tol = config.level_tolerance_pips * pip_size
    source = ReactionSource(
        instrument=instrument,
        source_type=ReactionSourceType.DAILY_BREAKER,
        direction=direction,
        level=payload.level,
        level_band_low=payload.level - tol,
        level_band_high=payload.level + tol,
        daily_breakout_ts=datetime.utcnow(),
    )
    src_ids = insert_reaction_sources(conn, [source], breakout_id)

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=None,
        last_h4_candle_ts=None,
        active_breakout_id=breakout_id,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=datetime.utcnow(),
        continuation_mode=False,
        last_alert_h4_ts=None,
        last_h4_breaker_level=None,
        retest_started_h4_ts=None,
    ))

    logger.info("%s BREAKOUT %s @ %.5f (breakout_id=%d)", instrument, payload.direction, payload.level, breakout_id)


def _handle_retest(conn, instrument: str, payload: TVWebhookPayload) -> None:
    state = get_instrument_state(conn, instrument)

    # Auto-create breakout record if missing (alert set up after the breakout fired)
    if state is None or state.active_breakout_id is None:
        if payload.breakout_level is None or payload.direction is None:
            logger.warning("%s RETEST received but no active breakout and no breakout_level — ignored", instrument)
            return
        direction = Direction(payload.direction)
        broken_type = FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE
        deactivate_all_breakouts(conn, instrument)
        breakout = DailyBreakout(
            instrument=instrument,
            direction=direction,
            broken_level=payload.breakout_level,
            broken_type=broken_type,
            breakout_ts=datetime.utcnow(),
        )
        breakout_id = insert_breakout(conn, breakout)
        logger.info("%s auto-created breakout record from RETEST payload", instrument)
        state = get_instrument_state(conn, instrument)
        active_breakout_id = breakout_id
    else:
        active_breakout_id = state.active_breakout_id

    # Look up existing reaction source for the active breakout direction
    sources = get_active_reaction_sources(conn, instrument)
    src_type = _source_type_from_str(payload.source)
    matched = next((s for s in sources if s.source_type == src_type), None)

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts if state else None,
        last_h4_candle_ts=state.last_h4_candle_ts if state else None,
        active_breakout_id=active_breakout_id,
        retest_in_progress=True,
        active_reaction_src_id=matched.db_id if matched else None,
        updated_at=datetime.utcnow(),
        continuation_mode=state.continuation_mode if state else False,
        last_alert_h4_ts=state.last_alert_h4_ts if state else None,
        last_h4_breaker_level=state.last_h4_breaker_level if state else None,
        retest_started_h4_ts=datetime.utcnow(),
    ))
    logger.info("%s RETEST started (source=%s)", instrument, payload.source)


def _handle_retest_cancelled(conn, instrument: str) -> None:
    state = get_instrument_state(conn, instrument)
    if state is None:
        return

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts,
        last_h4_candle_ts=state.last_h4_candle_ts,
        active_breakout_id=state.active_breakout_id,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=datetime.utcnow(),
        continuation_mode=state.continuation_mode,
        last_alert_h4_ts=state.last_alert_h4_ts,
        last_h4_breaker_level=state.last_h4_breaker_level,
        retest_started_h4_ts=None,
    ))
    logger.info("%s RETEST cancelled — price left the band", instrument)


async def _handle_confirmed(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    direction = Direction(payload.direction)

    # Get the active breakout from DB — if missing (e.g. alert was set up after
    # the breakout happened), auto-create it from the CONFIRMED payload so the
    # alert still fires correctly.
    breakout = get_active_breakout(conn, instrument)
    if breakout is None:
        bl = payload.breakout_level or payload.h4_level or 0.0
        broken_type = FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE
        deactivate_all_breakouts(conn, instrument)
        breakout = DailyBreakout(
            instrument=instrument,
            direction=direction,
            broken_level=bl,
            broken_type=broken_type,
            breakout_ts=datetime.utcnow(),
        )
        breakout_id = insert_breakout(conn, breakout)
        breakout.db_id = breakout_id
        logger.info("%s auto-created breakout record from CONFIRMED payload", instrument)

    # Ensure the matching reaction source exists in DB
    src_type = _source_type_from_str(payload.source)
    sources = get_active_reaction_sources(conn, instrument)
    source = next((s for s in sources if s.source_type == src_type), None)
    if source is None:
        pip_size = pip_size_for(instrument)
        tol_val = config.level_tolerance_pips * pip_size
        src_lvl = payload.source_level or payload.breakout_level or breakout.broken_level
        source = ReactionSource(
            instrument=instrument,
            source_type=src_type,
            direction=direction,
            level=src_lvl,
            level_band_low=src_lvl - tol_val,
            level_band_high=src_lvl + tol_val,
            daily_breakout_ts=breakout.breakout_ts,
        )
        src_ids = insert_reaction_sources(conn, [source], breakout.db_id)
        source.db_id = src_ids[0]

    now = datetime.utcnow()

    # Build a synthetic H4 Formation from the webhook payload
    # Bullish confirmation → A-shape (bullish candle + bearish candle = resistance)
    # Bearish confirmation → V-shape (bearish candle + bullish candle = support)
    h4_form_type = FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE
    h4_form_dir  = Direction.BEARISH    if direction == Direction.BULLISH else Direction.BULLISH
    h4_level     = payload.h4_level or (payload.breakout_level or breakout.broken_level)

    h4_formation = Formation(
        instrument=instrument,
        timeframe=Timeframe.H4,
        formation_type=h4_form_type,
        direction=h4_form_dir,
        level=h4_level,
        established_at=now,
        candle_1_ts=now,
        candle_2_ts=now,
    )
    h4_formation_id = insert_formation(conn, h4_formation)
    h4_formation.db_id = h4_formation_id

    # Build the H4 breakout event
    h4_cls = (
        BreakoutClassification.EXTERNAL
        if payload.h4_class == "external"
        else BreakoutClassification.INTERNAL
    )
    h4_event = H4BreakoutEvent(
        instrument=instrument,
        direction=direction,
        classification=h4_cls,
        formation_broken=h4_formation,
        confirmation_ts=now,
    )

    # Assemble the full AlertRecord
    alert_record = AlertRecord(
        instrument=instrument,
        direction=direction,
        daily_breakout=breakout,
        reaction_source=source,
        h4_event=h4_event,
        fired_at=now,
        classification=AlertClassification.ORIGIN,
    )

    alert_text = format_alert(alert_record)
    insert_alert(conn, alert_record, breakout.db_id, source.db_id, h4_formation_id, alert_text)

    # Update state: clear retest, keep breakout active, enter continuation mode
    state = get_instrument_state(conn, instrument)
    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts if state else None,
        last_h4_candle_ts=state.last_h4_candle_ts if state else None,
        active_breakout_id=breakout.db_id,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=now,
        continuation_mode=True,
        last_alert_h4_ts=now,
        last_h4_breaker_level=h4_level,
        retest_started_h4_ts=None,
    ))

    logger.info("%s CONFIRMED %s (h4_class=%s) — alert stored", instrument, direction.value, payload.h4_class)

    if config.telegram_enabled:
        await send_alert(config.telegram_bot_token, config.telegram_chat_id, alert_text)


def _handle_invalidated(conn, instrument: str) -> None:
    state = get_instrument_state(conn, instrument)

    if state and state.active_breakout_id:
        deactivate_reaction_sources_for_breakout(conn, state.active_breakout_id)
        from state.repository import deactivate_breakout
        deactivate_breakout(conn, state.active_breakout_id)

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts if state else None,
        last_h4_candle_ts=state.last_h4_candle_ts if state else None,
        active_breakout_id=None,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=datetime.utcnow(),
        continuation_mode=False,
        last_alert_h4_ts=state.last_alert_h4_ts if state else None,
        last_h4_breaker_level=None,
        retest_started_h4_ts=None,
    ))
    logger.info("%s INVALIDATED — reset to IDLE", instrument)
