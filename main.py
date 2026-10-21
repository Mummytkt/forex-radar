"""
Entry point for the Forex Radar backend.

Analysis data now comes from TradingView Pine Script webhooks (POST /api/tv-webhook)
instead of the Twelve Data API polling scheduler.

Usage:
  python main.py            # Start API server (normal mode)
  python main.py --dry-run  # Disable Telegram, log alerts to console only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import load_config
from state.db import get_connection, bootstrap_schema
from api.app import app as fastapi_app
from alerts.price_monitor import run_price_check
from alerts.billing_cycle import run_billing_cycle
from alerts.backup import run_backup
from alerts.feed_monitor import run_feed_check
from alerts.reminders import run_reminders
from alerts.news import refresh_calendar, run_news_summary, run_news_reminders


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # httpx logs every request URL at INFO, and Telegram URLs contain the bot
    # token — keep it out of the logs (warnings/errors still show).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def main(dry_run: bool = False) -> None:
    config = load_config()
    if dry_run:
        config.telegram_enabled = False

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    conn = get_connection(config.db_path)
    bootstrap_schema(conn)

    # Instrument list from the DB (owner-editable), plus instruments added since
    # it was saved and the Deriv synthetics that have reported.
    from state.instruments import load_instruments
    load_instruments(conn, config)
    logger.info("Loaded %d instruments from DB config.", len(config.instruments))

    # Load JWT secret — create a random one if missing, so tokens are never
    # signed with a guessable fallback.
    jwt_row = conn.execute("SELECT value FROM user_config WHERE key = 'jwt_secret'").fetchone()
    if jwt_row and jwt_row[0]:
        fastapi_app.state.jwt_secret = jwt_row[0]
    else:
        import secrets as _secrets
        new_secret = _secrets.token_hex(32)
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('jwt_secret', ?, datetime('now'))",
            (new_secret,),
        )
        conn.commit()
        fastapi_app.state.jwt_secret = new_secret
        logger.warning("No JWT secret found — generated a new one (existing sessions must sign in again).")

    # Auth check
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    fastapi_app.state.auth_enabled = user_count > 0

    # Seed owner's telegram_chat_id from env var so the per-user alert filter applies to them.
    # Runs every startup — idempotent (only writes when the column is still NULL).
    if config.telegram_chat_id:
        conn.execute(
            "UPDATE users SET telegram_chat_id = ? WHERE role = 'OWNER' AND (telegram_chat_id IS NULL OR telegram_chat_id = '')",
            (config.telegram_chat_id,),
        )
        conn.commit()

    # Attach shared state to the API
    fastapi_app.state.conn = conn
    fastapi_app.state.config = config

    logger.info("Forex Radar started — listening for TradingView webhooks on /api/tv-webhook")

    # Price alert monitor — runs every 5 minutes, independent of bias alert system
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_price_check,
        "interval",
        minutes=5,
        kwargs={"db_path": config.db_path, "config": config},
        id="price_monitor",
        name="Price level alert monitor",
        misfire_grace_time=60,
    )
    scheduler.add_job(
        run_billing_cycle,
        "interval",
        hours=6,
        kwargs={"db_path": config.db_path, "config": config},
        id="billing_cycle",
        name="Subscription renewal + trial charge + commission release",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        run_backup,
        "cron",
        hour=2, minute=30,  # 02:30 UTC daily — between H4 closes, quiet time
        kwargs={"db_path": config.db_path, "config": config},
        id="daily_backup",
        name="Daily database backup (local + encrypted off-site to owner Telegram)",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_feed_check,
        "interval",
        minutes=30,
        kwargs={"db_path": config.db_path, "config": config},
        id="feed_monitor",
        name="TradingView feed health (warns owner when a pair goes silent)",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        run_reminders,
        "interval",
        hours=6,
        kwargs={"db_path": config.db_path, "config": config},
        id="subscription_reminders",
        name="Renewal / trial-ending / access-ended reminders to subscribers' Telegram",
        misfire_grace_time=1800,
    )
    scheduler.add_job(
        refresh_calendar,
        "interval",
        hours=3,
        next_run_time=datetime.now(timezone.utc),   # also once at startup
        kwargs={"db_path": config.db_path, "config": config},
        id="news_calendar",
        name="High-impact news calendar refresh",
        misfire_grace_time=1800,
    )
    scheduler.add_job(
        run_news_summary,
        "cron",
        hour=6, minute=2,   # 07:02 WAT, after the 06:00 refresh window, away from H4 closes
        kwargs={"db_path": config.db_path, "config": config},
        id="news_summary",
        name="Morning high-impact news summary to subscribers",
        misfire_grace_time=3 * 3600,
    )
    scheduler.add_job(
        run_news_reminders,
        "interval",
        minutes=5,
        kwargs={"db_path": config.db_path, "config": config},
        id="news_reminders",
        name="30-minutes-before high-impact news reminders",
        misfire_grace_time=240,
    )
    scheduler.start()
    logger.info("Price monitor + billing cycle + daily backup + feed monitor + reminders + news started")

    server = uvicorn.Server(
        uvicorn.Config(
            fastapi_app, host="0.0.0.0", port=8080,
            log_level="warning", loop="asyncio",
            timeout_keep_alive=300,
        )
    )
    try:
        await server.serve()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down…")
    finally:
        scheduler.shutdown(wait=False)
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Radar — TradingView webhook backend")
    parser.add_argument("--dry-run", action="store_true", help="Disable Telegram alerts")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
