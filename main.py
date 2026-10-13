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

import uvicorn

from config import load_config
from state.db import get_connection, bootstrap_schema
from api.app import app as fastapi_app


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def main(dry_run: bool = False) -> None:
    config = load_config()
    if dry_run:
        config.telegram_enabled = False

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    conn = get_connection(config.db_path)
    bootstrap_schema(conn)

    # Load instrument list from DB override (allows UI edits without restart)
    row = conn.execute("SELECT value FROM user_config WHERE key = 'instruments'").fetchone()
    if row:
        config.instruments = json.loads(row[0])
        logger.info("Loaded %d instruments from DB config.", len(config.instruments))
    else:
        conn.execute(
            "INSERT INTO user_config (key, value) VALUES ('instruments', ?)",
            (json.dumps(config.instruments),),
        )
        conn.commit()
        logger.info("Wrote default instrument list (%d) to DB config.", len(config.instruments))

    # Load JWT secret
    jwt_row = conn.execute("SELECT value FROM user_config WHERE key = 'jwt_secret'").fetchone()
    if jwt_row:
        fastapi_app.state.jwt_secret = jwt_row[0]

    # Auth check
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    fastapi_app.state.auth_enabled = user_count > 0

    # Attach shared state to the API
    fastapi_app.state.conn = conn
    fastapi_app.state.config = config

    logger.info("Forex Radar started — listening for TradingView webhooks on /api/tv-webhook")

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
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forex Radar — TradingView webhook backend")
    parser.add_argument("--dry-run", action="store_true", help="Disable Telegram alerts")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
