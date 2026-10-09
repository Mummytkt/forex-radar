"""
Entry point for the Forex Radar analysis engine.

Usage:
  python main.py                     # Start live scheduler
  python main.py --backfill-only     # Fetch historical data then exit
  python main.py --dry-run           # Disable Telegram, log alerts to console
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from config import load_config
from data.client import TwelveDataClient
from state.db import get_connection, bootstrap_schema
from scheduler.jobs import create_scheduler, run_backfill


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def main(backfill_only: bool = False, dry_run: bool = False) -> None:
    config = load_config()
    if dry_run:
        config.telegram_enabled = False

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    conn = get_connection(config.db_path)
    bootstrap_schema(conn)

    td_client = TwelveDataClient(api_key=config.twelve_data_api_key)

    # Always run a backfill on startup to seed or refresh historical state
    await run_backfill(config, conn, td_client)

    if backfill_only:
        logger.info("--backfill-only flag set. Exiting after backfill.")
        conn.close()
        return

    scheduler = create_scheduler(config, conn, td_client)
    scheduler.start()
    logger.info(
        "Scheduler started. Monitoring %d instruments. Press Ctrl+C to stop.",
        len(config.instruments),
    )

    try:
        await asyncio.Event().wait()  # run forever
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down…")
    finally:
        scheduler.shutdown(wait=False)
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Radar — bias analysis engine")
    parser.add_argument("--backfill-only", action="store_true", help="Fetch history then exit")
    parser.add_argument("--dry-run", action="store_true", help="Disable Telegram delivery")
    args = parser.parse_args()

    asyncio.run(main(backfill_only=args.backfill_only, dry_run=args.dry_run))
