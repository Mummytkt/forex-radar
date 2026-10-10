"""
Application configuration loaded from a .env file.

All settings are typed. Import `load_config()` once at startup and pass the
resulting Config object to the modules that need it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    twelve_data_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    db_path: str = "forex_radar.db"
    instruments: list[str] = field(default_factory=list)
    poll_lookback_daily: int = 200   # candles fetched on backfill for Daily
    poll_lookback_h4: int = 500      # candles fetched on backfill for H4
    level_tolerance_pips: float = 5.0
    log_level: str = "INFO"
    telegram_enabled: bool = True    # set False for dry-run / testing


def load_config(env_path: str = ".env") -> Config:
    load_dotenv(dotenv_path=Path(env_path))

    instruments_raw = os.getenv("INSTRUMENTS", "")
    if instruments_raw.strip():
        instruments = [i.strip() for i in instruments_raw.split(",") if i.strip()]
    else:
        instruments = DEFAULT_INSTRUMENTS

    return Config(
        twelve_data_api_key=_require("TWELVE_DATA_API_KEY"),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        db_path=os.getenv("DB_PATH", "forex_radar.db"),
        instruments=instruments,
        poll_lookback_daily=int(os.getenv("POLL_LOOKBACK_DAILY", "200")),
        poll_lookback_h4=int(os.getenv("POLL_LOOKBACK_H4", "500")),
        level_tolerance_pips=float(os.getenv("LEVEL_TOLERANCE_PIPS", "5.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        telegram_enabled=os.getenv("TELEGRAM_ENABLED", "true").lower() != "false",
    )


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set.")
    return value


def pip_size_for(instrument: str) -> float:
    """Return the pip size for price-level tolerance calculations."""
    clean = instrument.replace("/", "").upper()
    if clean.endswith("JPY"):
        return 0.01
    if clean in {"XAUUSD"}:
        return 0.10
    if clean in {"XAGUSD"}:
        return 0.01
    # Crypto pairs
    if clean == "BTCUSD":
        return 10.0    # $50 tolerance band at 5 pips
    if clean == "ETHUSD":
        return 1.0     # $5 tolerance band
    if clean == "SOLUSD":
        return 0.05    # $0.25 tolerance band
    if clean == "BNBUSD":
        return 0.10    # $0.50 tolerance band
    if clean == "XRPUSD":
        return 0.0002  # $0.001 tolerance band
    if clean == "ADAUSD":
        return 0.00005 # $0.00025 tolerance band
    if clean == "DOGEUSD":
        return 0.00002 # $0.0001 tolerance band
    if clean == "LTCUSD":
        return 0.02    # $0.10 tolerance band
    return 0.0001


# ── Default instrument list ───────────────────────────────────────────────────
# Twelve Data expects slash format for forex: EUR/USD
# The normalizer stores internally without slash: EURUSD

DEFAULT_INSTRUMENTS: list[str] = [
    # Majors
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "USD/CAD", "AUD/USD", "NZD/USD",
    # EUR crosses
    "EUR/JPY", "EUR/GBP", "EUR/AUD", "EUR/CAD", "EUR/NZD", "EUR/CHF",
    # GBP crosses
    "GBP/JPY", "GBP/AUD", "GBP/CAD", "GBP/NZD", "GBP/CHF",
    # AUD / NZD crosses
    "AUD/JPY", "AUD/CAD", "AUD/NZD", "AUD/CHF",
    "NZD/JPY", "NZD/CAD", "NZD/CHF",
    # CAD / CHF crosses
    "CAD/JPY", "CAD/CHF", "CHF/JPY",
    # Metals
    "XAU/USD",
    # Crypto (24/7)
    "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "ADA/USD", "DOGE/USD", "LTC/USD",
]
