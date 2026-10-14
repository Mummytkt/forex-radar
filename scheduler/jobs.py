"""
APScheduler job definitions and the per-instrument processing pipeline.

Two job types:
  h4_candle_close_job   — fires at 01:05, 05:05, 09:05, 13:05, 17:05, 21:05 UTC
                          (5 min after each NY-session H4 candle closes at
                          01:00, 05:00, 09:00, 13:00, 17:00, 21:00 UTC in EDT)
                          H4 candles are built in-house from Twelve Data 1h data,
                          aligned to the NY session start (21:00 UTC in EDT,
                          22:00 UTC in EST from November), matching TradingView exactly.
  daily_candle_close_job — fires at 21:05 AND 22:05 UTC (covers DST shift)
                           The 21:05 H4 and Daily jobs overlap intentionally; the
                           Daily job deduplication prevents double-processing.

Both jobs iterate over all configured instruments, fetch the latest candles,
run the engine, persist state, and send any confirmed alerts.

Rate limiting is handled inside TwelveDataClient (token bucket).
Instruments are processed sequentially within each job to avoid bursting.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import Config, pip_size_for
from data.client import TwelveDataClient, TwelveDataError
from data.normalizer import normalize_candles, aggregate_h4_from_1h, symbol_to_instrument, instrument_to_symbol
from data.models import Timeframe
from analysis.engine import EngineInput, run_engine_cycle
from data.models import Direction
from alerts.formatter import format_alert
from alerts.telegram import send_alert
from state import repository as repo
from state.repository import InstrumentStateRow

logger = logging.getLogger(__name__)


def _ny_session_start_hour() -> int:
    """
    Return the UTC hour at which the NY trading session starts.
    21 during EDT (UTC-4, roughly March–November),
    22 during EST (UTC-5, roughly November–March).
    """
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime, timezone
        offset = datetime.now(ZoneInfo("America/New_York")).utcoffset().total_seconds() / 3600
        return 22 if offset == -5 else 21
    except Exception:
        return 21  # safe fallback


# Crypto pairs trade 24/7; all other instruments follow forex/metals market hours.
_CRYPTO_INSTRUMENTS = frozenset([
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "LTCUSD",
])


def _is_market_open(instrument: str) -> bool:
    """
    Returns False for forex/metals instruments when the market is closed:
    Saturday (all day UTC) and Sunday before 21:00 UTC.

    Crypto instruments are always open.
    """
    if instrument.replace("/", "").upper() in _CRYPTO_INSTRUMENTS:
        return True
    now = datetime.now(timezone.utc)
    wd = now.weekday()          # 0=Mon … 5=Sat, 6=Sun
    if wd == 5:                  # Saturday — always closed
        return False
    if wd == 6 and now.hour < 21:  # Sunday before NY open
        return False
    return True


# ── Candle-close job handlers ─────────────────────────────────────────────────

async def h4_candle_close_job(
    config: Config,
    conn: sqlite3.Connection,
    td_client: TwelveDataClient,
) -> None:
    logger.info("H4 candle close job triggered at %s UTC", datetime.now(timezone.utc).isoformat())
    for instrument in config.instruments:
        if not _is_market_open(instrument):
            logger.debug("Skipping %s — market closed (weekend)", instrument)
            continue
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
        if not _is_market_open(instrument):
            logger.debug("Skipping %s — market closed (weekend)", instrument)
            continue
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
    # H4 candles are built from 1h data aligned to the NY session start so that
    # candle boundaries match TradingView (closes at 01:00, 05:00, 09:00,
    # 13:00, 17:00, 21:00 UTC in EDT). 600 × 1h ≈ 150 H4 periods.
    try:
        raw_daily = td_client.fetch_candles(symbol, "1day", outputsize=200)
        raw_1h = td_client.fetch_candles(symbol, "1h", outputsize=600)
    except TwelveDataError as e:
        logger.warning("Skipping %s — API error: %s", instrument, e)
        return

    daily_candles = normalize_candles(raw_daily, instrument, Timeframe.DAILY)
    h1_candles = normalize_candles(raw_1h, instrument, Timeframe.H1)
    h4_candles = aggregate_h4_from_1h(h1_candles, _ny_session_start_hour())

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

    continuation_mode = state.continuation_mode if state else False
    last_alert_h4_ts = state.last_alert_h4_ts if state else None
    last_h4_breaker_level = state.last_h4_breaker_level if state else None
    retest_started_h4_ts = state.retest_started_h4_ts if state else None
    external_level = state.external_level if state else None
    external_level_direction: Direction | None = None
    if state and state.external_level_direction:
        try:
            external_level_direction = Direction(state.external_level_direction)
        except ValueError:
            pass

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
        continuation_mode=continuation_mode,
        last_alert_h4_ts=last_alert_h4_ts,
        last_h4_breaker_level=last_h4_breaker_level,
        retest_started_h4_ts=retest_started_h4_ts,
        external_level=external_level,
        external_level_direction=external_level_direction,
    )

    # ── Run engine ────────────────────────────────────────────────────────────
    out = run_engine_cycle(inp)

    # ── Persist state ─────────────────────────────────────────────────────────
    active_breakout_id: int | None = active_breakout.db_id if active_breakout else None
    active_src_id: int | None = None

    # Breakout invalidated: price returned through the broken level — go IDLE
    if out.invalidated and active_breakout_id:
        logger.info(
            "%s breakout invalidated (price returned through %.5f) — resetting to IDLE",
            instrument,
            active_breakout.broken_level if active_breakout else 0,
        )
        repo.deactivate_reaction_sources_for_breakout(conn, active_breakout_id)
        repo.deactivate_breakout(conn, active_breakout_id)
        active_breakout_id = None
        repo.upsert_instrument_state(
            conn,
            InstrumentStateRow(
                instrument=instrument,
                last_daily_candle_ts=latest_daily_ts,
                last_h4_candle_ts=latest_h4_ts,
                active_breakout_id=None,
                retest_in_progress=False,
                active_reaction_src_id=None,
                updated_at=datetime.utcnow(),
                continuation_mode=False,
                last_alert_h4_ts=None,
                last_h4_breaker_level=None,
                retest_started_h4_ts=None,
                external_level=None,
                external_level_direction=None,
            ),
        )
        return

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

        bo_id = active_breakout_id or (alert.daily_breakout.db_id)

        # Persist H4 formation if present (origin and continuation A-shape have one)
        h4_formation_id: int | None = None
        if alert.h4_event is not None:
            h4_formation = alert.h4_event.formation_broken
            h4_formation_id = repo.insert_formation(conn, h4_formation)
            h4_formation.db_id = h4_formation_id

        # Reaction source ID (None for continuation alerts)
        src_id: int | None = alert.reaction_source.db_id if alert.reaction_source else None

        if bo_id:
            repo.insert_alert(conn, alert, bo_id, src_id, h4_formation_id, alert_text)

        # Deactivate the consumed daily reaction source (origin only)
        if src_id:
            repo.deactivate_reaction_source(conn, src_id)

        # Send via Telegram (respecting the owner's alert-type preferences)
        if config.telegram_enabled:
            # Determine the H4 classification of this alert
            if alert.h4_event is not None:
                _cls = alert.h4_event.classification.value  # 'external' or 'internal'
            else:
                _cls = None  # OC continuation — not filtered by external/internal pref

            _send = True
            if _cls == "external":
                row = conn.execute("SELECT value FROM user_config WHERE key = 'pref_alert_external'").fetchone()
                if row and row[0] == "0":
                    _send = False
            elif _cls == "internal":
                row = conn.execute("SELECT value FROM user_config WHERE key = 'pref_alert_internal'").fetchone()
                if row and row[0] == "0":
                    _send = False

            if _send:
                # Deliver to every user who has a telegram_chat_id and watches this instrument.
                # watched_instruments is stored with slashes (e.g. "EUR/USD"); alert.instrument
                # uses no slashes internally (e.g. "EURUSD") — normalise for comparison.
                instr_no_slash = alert.instrument.replace("/", "").upper()
                recipients = conn.execute(
                    "SELECT telegram_chat_id, watched_instruments FROM users "
                    "WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != ''"
                ).fetchall()
                sent_any = False
                for rec in recipients:
                    raw_watched = rec["watched_instruments"]
                    if raw_watched:
                        watched = [w.replace("/", "").upper() for w in json.loads(raw_watched)]
                        if instr_no_slash not in watched:
                            continue
                    await send_alert(config.telegram_bot_token, rec["telegram_chat_id"], alert_text)
                    sent_any = True
                # Fallback: if no users have chat IDs set, use the global config chat ID
                if not sent_any and config.telegram_chat_id:
                    await send_alert(config.telegram_bot_token, config.telegram_chat_id, alert_text)
            else:
                logger.info("Alert suppressed by preference filter: %s %s breakout", alert.instrument, _cls)
        else:
            logger.info("ALERT (Telegram disabled):\n%s", alert_text)

    # Resolve active_src_id for state update
    if out.active_reaction_src is not None:
        active_src_id = out.active_reaction_src.db_id

    # Carry forward or update external level
    final_ext_level = out.new_external_level if out.new_external_level is not None else external_level
    final_ext_dir = (
        out.new_external_direction.value if out.new_external_direction is not None
        else (external_level_direction.value if external_level_direction is not None else None)
    )

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
            continuation_mode=out.continuation_mode,
            last_alert_h4_ts=out.last_alert_h4_ts,
            last_h4_breaker_level=out.last_h4_breaker_level,
            retest_started_h4_ts=out.retest_started_h4_ts,
            external_level=final_ext_level,
            external_level_direction=final_ext_dir,
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
            # Fetch 1h candles; free-tier max is 800 — multiply H4 lookback by 4
            # but cap at 800 for the free tier limit
            h1_outputsize = min(config.poll_lookback_h4 * 4, 800)
            raw_1h = td_client.fetch_candles(symbol, "1h", outputsize=h1_outputsize)
            daily_candles = normalize_candles(raw_daily, instrument, Timeframe.DAILY)
            h1_candles = normalize_candles(raw_1h, instrument, Timeframe.H1)
            h4_candles = aggregate_h4_from_1h(h1_candles, _ny_session_start_hour())
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

    H4 jobs fire at 01:05, 05:05, 09:05, 13:05, 17:05, 21:05 UTC — 5 min after
    each NY-session H4 candle closes (01:00, 05:00, 09:00, 13:00, 17:00, 21:00 UTC
    in EDT), matching TradingView exactly.
    Daily jobs fire at 21:05 and 22:05 UTC to cover both EST and EDT close times.
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # H4 close jobs — fire 5 min after each NY-session H4 candle closes
    # EDT closes: 01:00, 05:00, 09:00, 13:00, 17:00, 21:00 UTC (= TradingView times)
    for hour in [1, 5, 9, 13, 17, 21]:
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
