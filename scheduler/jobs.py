"""
APScheduler job definitions and the per-instrument processing pipeline.

Two job types:
  h4_candle_close_job   — fires at 00:05, 04:05, 08:05, 12:05, 16:05, 20:05 UTC
  daily_candle_close_job — fires at 21:05 AND 22:05 UTC (covers DST shift)

Both jobs iterate over all configured instruments, fetch the latest candles,
run the engine, persist state, and send any confirmed alerts.

Rate limiting is handled inside TwelveDataClient (token bucket).
Instruments are processed sequentially within each job to avoid bursting.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import Config, pip_size_for
from data.client import TwelveDataClient, TwelveDataError
from data.normalizer import normalize_candles, symbol_to_instrument, instrument_to_symbol
from data.models import Timeframe
from analysis.engine import EngineInput, run_engine_cycle
from alerts.formatter import format_alert
from alerts.telegram import send_alert
from state import repository as repo
from state.repository import InstrumentStateRow

logger = logging.getLogger(__name__)


# ── Candle-close job handlers ─────────────────────────────────────────────────

async def h4_candle_close_job(
    config: Config,
    conn: sqlite3.Connection,
    td_client: TwelveDataClient,
) -> None:
    logger.info("H4 candle close job triggered at %s UTC", datetime.now(timezone.utc).isoformat())
    for instrument in config.instruments:
        try:
            await process_instrument_cycle(instrument, Timeframe.H4, config, conn, td_client)
        except Exception as e:
            logger.exception("Error processing %s in H4 job: %s", instrument, e)
        await asyncio.sleep(0.5)  # small pause between instruments


async def daily_candle_close_job(
    config: Config,
    conn: sqlite3.Connection,
    td_client: TwelveDataClient,
) -> None:
    logger.info("Daily candle close job triggered at %s UTC", datetime.now(timezone.utc).isoformat())
    for instrument in config.instruments:
        try:
            await process_instrument_cycle(instrument, Timeframe.DAILY, config, conn, td_client)
        except Exception as e:
            logger.exception("Error processing %s in Daily job: %s", instrument, e)
        await asyncio.sleep(0.5)


# ── Per-instrument processing pipeline ───────────────────────────────────────

async def process_instrument_cycle(
    instrument: str,
    triggered_timeframe: Timeframe,
    config: Config,
    conn: sqlite3.Connection,
    td_client: TwelveDataClient,
) -> None:
    """
    Full pipeline for one instrument at one candle-close event.

    Steps:
      1. Fetch latest Daily + H4 candles from Twelve Data
      2. Deduplicate (skip if we already processed these candles)
      3. Cache raw candles in DB
      4. Load instrument state from DB
      5. Run engine cycle
      6. Persist updated state to DB
      7. Send alert if confirmed
    """
    symbol = instrument_to_symbol(instrument)

    # ── Fetch candles ─────────────────────────────────────────────────────────
    try:
        raw_daily = td_client.fetch_candles(symbol, "1day", outputsize=200)
        raw_h4 = td_client.fetch_candles(symbol, "4h", outputsize=200)
    except TwelveDataError as e:
        logger.warning("Skipping %s — API error: %s", instrument, e)
        return

    daily_candles = normalize_candles(raw_daily, instrument, Timeframe.DAILY)
    h4_candles = normalize_candles(raw_h4, instrument, Timeframe.H4)

    if not daily_candles or not h4_candles:
        logger.warning("No candles for %s — skipping", instrument)
        return

    # ── Deduplicate ───────────────────────────────────────────────────────────
    state = repo.get_instrument_state(conn, instrument)
    latest_daily_ts = daily_candles[-1].timestamp
    latest_h4_ts = h4_candles[-1].timestamp

    if state is not None:
        if triggered_timeframe == Timeframe.DAILY and state.last_daily_candle_ts == latest_daily_ts:
            logger.debug("Daily candle for %s already processed — skipping", instrument)
            return
        if triggered_timeframe == Timeframe.H4 and state.last_h4_candle_ts == latest_h4_ts:
            logger.debug("H4 candle for %s already processed — skipping", instrument)
            return

    # ── Cache raw candles ─────────────────────────────────────────────────────
    repo.upsert_raw_candles(conn, daily_candles)
    repo.upsert_raw_candles(conn, h4_candles)

    # ── Load engine inputs ────────────────────────────────────────────────────
    active_breakout = repo.get_active_breakout(conn, instrument)
    active_sources = repo.get_active_reaction_sources(conn, instrument) if active_breakout else []

    retest_in_progress = state.retest_in_progress if state else False
    active_reaction_src = None
    if state and state.active_reaction_src_id:
        for src in active_sources:
            if src.db_id == state.active_reaction_src_id:
                active_reaction_src = src
                break

    pip_size = pip_size_for(instrument)

    inp = EngineInput(
        instrument=instrument,
        daily_candles=daily_candles,
        h4_candles=h4_candles,
        active_breakout=active_breakout,
        active_reaction_srcs=active_sources,
        retest_in_progress=retest_in_progress,
        active_reaction_src=active_reaction_src,
        tolerance_pips=config.level_tolerance_pips,
        pip_size=pip_size,
    )

    # ── Run engine ────────────────────────────────────────────────────────────
    out = run_engine_cycle(inp)

    # ── Persist state ─────────────────────────────────────────────────────────
    active_breakout_id: int | None = active_breakout.db_id if active_breakout else None
    active_src_id: int | None = None

    if out.new_breakout is not None:
        # Deactivate old breakout and its sources
        if active_breakout_id:
            repo.deactivate_reaction_sources_for_breakout(conn, active_breakout_id)
            repo.deactivate_breakout(conn, active_breakout_id)
        # Insert new breakout
        active_breakout_id = repo.insert_breakout(conn, out.new_breakout)
        out.new_breakout.db_id = active_breakout_id
        # Insert new reaction sources
        if out.updated_reaction_srcs:
            new_src_ids = repo.insert_reaction_sources(conn, out.updated_reaction_srcs, active_breakout_id)
            for src, sid in zip(out.updated_reaction_srcs, new_src_ids):
                src.db_id = sid

    elif out.updated_reaction_srcs:
        # Post-breakout OC sources may have been added — insert the new ones only
        existing_ids = {s.db_id for s in active_sources if s.db_id}
        new_srcs = [s for s in out.updated_reaction_srcs if s.db_id is None]
        if new_srcs and active_breakout_id:
            new_src_ids = repo.insert_reaction_sources(conn, new_srcs, active_breakout_id)
            for src, sid in zip(new_srcs, new_src_ids):
                src.db_id = sid

    # ── Handle alert ──────────────────────────────────────────────────────────
    if out.alert_to_send is not None:
        alert = out.alert_to_send
        alert_text = format_alert(alert)

        # Persist the H4 formation used for confirmation
        h4_formation = alert.h4_event.formation_broken
        h4_formation_id = repo.insert_formation(conn, h4_formation)
        h4_formation.db_id = h4_formation_id

        # Find IDs for the breakout and reaction source
        bo_id = active_breakout_id or (alert.daily_breakout.db_id)
        src_id = alert.reaction_source.db_id

        if bo_id and src_id:
            repo.insert_alert(conn, alert, bo_id, src_id, h4_formation_id, alert_text)

        # Deactivate the consumed reaction source
        if src_id:
            repo.deactivate_reaction_source(conn, src_id)

        # Send via Telegram
        if config.telegram_enabled:
            await send_alert(config.telegram_bot_token, config.telegram_chat_id, alert_text)
        else:
            logger.info("ALERT (Telegram disabled):\n%s", alert_text)

    # Resolve active_src_id for state update
    if out.active_reaction_src is not None:
        active_src_id = out.active_reaction_src.db_id

    # ── Update instrument state ───────────────────────────────────────────────
    repo.upsert_instrument_state(
        conn,
        InstrumentStateRow(
            instrument=instrument,
            last_daily_candle_ts=latest_daily_ts,
            last_h4_candle_ts=latest_h4_ts,
            active_breakout_id=active_breakout_id,
            retest_in_progress=out.retest_in_progress,
            active_reaction_src_id=active_src_id,
            updated_at=datetime.utcnow(),
        ),
    )


# ── Backfill ──────────────────────────────────────────────────────────────────

async def run_backfill(
    config: Config,
    conn: sqlite3.Connection,
    td_client: TwelveDataClient,
) -> None:
    """
    On first run (empty DB), fetch the full configured lookback for all
    instruments and cache in raw_candles. Seeds formation/breakout state.
    """
    logger.info("Starting backfill for %d instruments…", len(config.instruments))
    for instrument in config.instruments:
        # Skip if we already have a reasonable amount of cached data
        cached_daily = repo.get_cached_candles(conn, instrument, Timeframe.DAILY, limit=10)
        cached_h4 = repo.get_cached_candles(conn, instrument, Timeframe.H4, limit=10)
        if len(cached_daily) >= 10 and len(cached_h4) >= 10:
            logger.debug("Skipping backfill for %s — data already cached", instrument)
            continue

        symbol = instrument_to_symbol(instrument)
        logger.info("Backfilling %s…", instrument)
        try:
            raw_daily = td_client.fetch_candles(
                symbol, "1day", outputsize=config.poll_lookback_daily
            )
            raw_h4 = td_client.fetch_candles(
                symbol, "4h", outputsize=config.poll_lookback_h4
            )
            daily_candles = normalize_candles(raw_daily, instrument, Timeframe.DAILY)
            h4_candles = normalize_candles(raw_h4, instrument, Timeframe.H4)
            repo.upsert_raw_candles(conn, daily_candles)
            repo.upsert_raw_candles(conn, h4_candles)
        except TwelveDataError as e:
            logger.warning("Backfill failed for %s: %s", instrument, e)
        await asyncio.sleep(0.5)
    logger.info("Backfill complete.")


# ── Scheduler factory ─────────────────────────────────────────────────────────

def create_scheduler(
    config: Config,
    conn: sqlite3.Connection,
    td_client: TwelveDataClient,
) -> AsyncIOScheduler:
    """
    Build and return a configured AsyncIOScheduler (not yet started).

    H4 jobs fire at :05 past each 4-hour boundary (UTC).
    Daily jobs fire at 21:05 and 22:05 UTC to cover both EST and EDT close times.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # H4 close jobs
    for hour in [0, 4, 8, 12, 16, 20]:
        scheduler.add_job(
            h4_candle_close_job,
            trigger="cron",
            hour=hour,
            minute=5,
            kwargs={"config": config, "conn": conn, "td_client": td_client},
            id=f"h4_close_{hour:02d}",
            name=f"H4 close {hour:02d}:05 UTC",
            misfire_grace_time=120,
        )

    # Daily close jobs (21:05 UTC = NY close during EDT, 22:05 UTC = NY close during EST)
    for hour in [21, 22]:
        scheduler.add_job(
            daily_candle_close_job,
            trigger="cron",
            hour=hour,
            minute=5,
            kwargs={"config": config, "conn": conn, "td_client": td_client},
            id=f"daily_close_{hour}",
            name=f"Daily close {hour}:05 UTC",
            misfire_grace_time=300,
        )

    return scheduler
