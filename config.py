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
    telegram_bot_token: str
    telegram_chat_id: str
    tv_webhook_secret: str           # shared secret validated on every Pine Script webhook
    telegram_webhook_secret: str = ""  # secret_token header validated on Telegram bot webhook
    paystack_secret_key: str = ""    # Paystack secret (server-side API + webhook signature)
    paystack_currency: str = "USD"   # charge currency; set NGN if USD isn't enabled on the account
    paystack_ngn_rate: float = 1600.0  # USD→NGN rate used when currency is NGN; update via PAYSTACK_NGN_RATE secret
    frontend_url: str = "https://frontend-fawn-nine-68.vercel.app"  # for Paystack callback_url
    db_path: str = "forex_radar.db"
    instruments: list[str] = field(default_factory=list)
    level_tolerance_pips: float = 5.0
    log_level: str = "INFO"
    telegram_enabled: bool = True    # set False for dry-run / testing
    backup_key: str = ""             # Fernet key; encrypts the daily off-site backup sent to the owner's Telegram


def load_config(env_path: str = ".env") -> Config:
    load_dotenv(dotenv_path=Path(env_path))

    instruments_raw = os.getenv("INSTRUMENTS", "")
    if instruments_raw.strip():
        instruments = [i.strip() for i in instruments_raw.split(",") if i.strip()]
    else:
        instruments = DEFAULT_INSTRUMENTS

    return Config(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        tv_webhook_secret=os.getenv("TV_WEBHOOK_SECRET", ""),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        paystack_secret_key=os.getenv("PAYSTACK_SECRET_KEY", ""),
        paystack_currency=os.getenv("PAYSTACK_CURRENCY", "USD"),
        paystack_ngn_rate=float(os.getenv("PAYSTACK_NGN_RATE", "1600")),
        frontend_url=os.getenv("FRONTEND_URL", "https://frontend-fawn-nine-68.vercel.app"),
        db_path=os.getenv("DB_PATH", "forex_radar.db"),
        instruments=instruments,
        level_tolerance_pips=float(os.getenv("LEVEL_TOLERANCE_PIPS", "5.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        telegram_enabled=os.getenv("TELEGRAM_ENABLED", "true").lower() != "false",
        backup_key=os.getenv("BACKUP_KEY", ""),
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
    # Energy
    if clean == "WTIUSD":
        return 0.05    # $0.25 tolerance band at 5 pips (~$75 oil)
    # Indices — pip = 1 point, tolerance = 5 × pip_size points
    if clean == "US30":
        return 10.0    # 50-point band (~42 000 Dow)
    if clean == "NAS100":
        return 5.0     # 25-point band (~20 000 NASDAQ 100)
    if clean == "SPX500":
        return 2.0     # 10-point band (~5 800 S&P 500)
    if clean == "UK100":
        return 3.0     # 15-point band (~8 200 FTSE 100)
    if clean == "GER40":
        return 5.0     # 25-point band (~19 000 DAX)
    if clean == "JPN225":
        return 10.0    # 50-point band (~40 000 Nikkei 225)
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
    # Energy
    "WTI/USD",
    # Indices
    "US30", "NAS100", "SPX500", "UK100", "GER40", "JPN225",
    # Crypto (24/7)
    "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "ADA/USD", "DOGE/USD", "LTC/USD",
]
