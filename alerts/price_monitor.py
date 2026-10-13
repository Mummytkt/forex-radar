"""
Background price monitor for dashboard price-level alerts.

Polls Yahoo Finance every 5 minutes for current prices of all instruments
that have active price alerts. Checks crossing conditions and fires
Telegram notifications to subscribers when their price levels are hit.

Completely independent of the bias alert system (Pine Script / tv-webhook).
The tv-webhook PRICE_UPDATE still runs as a secondary price update at H4 closes;
this job is the primary feed for intrabar / multi-timeframe monitoring.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Instrument → Yahoo Finance symbol mapping ─────────────────────────────────

_CRYPTO_BASES = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "LTC"}

_EXACT_MAP: dict[str, str] = {
    # Metals
    "XAUUSD": "GC=F",
    "XAGUSD": "SI=F",
    # Energy
    "WTIUSD": "CL=F",
    "USOIL":  "CL=F",
    # Indices
    "US30":   "^DJI",
    "NAS100": "^NDX",
    "SPX500": "^GSPC",
    "UK100":  "^FTSE",
    "GER40":  "^GDAXI",
    "JPN225": "^N225",
}


def _to_yf_ticker(instrument: str) -> Optional[str]:
    """Map internal instrument name (e.g. 'EURUSD') to a yfinance symbol."""
    inst = instrument.upper()
    if inst in _EXACT_MAP:
        return _EXACT_MAP[inst]
    # Crypto: BTCUSD or BTC → "BTC-USD"
    base = inst[:-3] if inst.endswith("USD") else inst
    if base in _CRYPTO_BASES:
        return f"{base}-USD"
    # Standard 6-char forex pair: EURUSD → "EURUSD=X"
    if len(inst) == 6 and inst.isalpha():
        return f"{inst}=X"
    return None


def _fetch_prices(instruments: list[str]) -> dict[str, float]:
    """
    Fetch current prices for a list of instruments via Yahoo Finance.
    Returns {instrument: price}. Missing instruments are silently omitted.
    """
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        logger.error("yfinance/pandas not installed — run: pip install yfinance pandas")
        return {}

    # Build instrument → yf_symbol map
    sym_map: dict[str, str] = {}
    for inst in instruments:
        sym = _to_yf_ticker(inst)
        if sym:
            sym_map[inst] = sym

    if not sym_map:
        return {}

    # Deduplicate symbols (two instruments might share one yf ticker)
    unique_syms = list(dict.fromkeys(sym_map.values()))
    prices: dict[str, float] = {}

    try:
        # Download 1 day of 5-minute bars; take the latest close
        tickers_arg = unique_syms if len(unique_syms) > 1 else unique_syms[0]
        raw = yf.download(
            tickers_arg,
            period="1d",
            interval="5m",
            progress=False,
            auto_adjust=True,
        )

        if raw.empty:
            logger.debug("yfinance returned empty DataFrame for %s", unique_syms)
            return {}

        close_data = raw["Close"]

        for inst, sym in sym_map.items():
            try:
                if isinstance(close_data, pd.DataFrame):
                    col = close_data[sym].dropna()
                else:
                    # Single ticker — close_data is a Series
                    col = close_data.dropna()
                if not col.empty:
                    val = float(col.iloc[-1])
                    if val == val:  # NaN check
                        prices[inst] = val
            except Exception as exc:
                logger.debug("Could not extract price for %s (%s): %s", inst, sym, exc)

    except Exception as exc:
        logger.warning("yfinance batch download failed: %s", exc)

    return prices


# ── Main check cycle ─────────────────────────────────────────────────────────

async def run_price_check(db_path: str, config) -> None:
    """
    Main price check cycle — called every 5 minutes by APScheduler.

    Opens its own DB connection (safe for SQLite WAL mode concurrent access).
    Steps:
      1. Find all instruments with active non-expired price alerts.
      2. Fetch current prices via Yahoo Finance.
      3. Upsert into instrument_prices table.
      4. Evaluate crossing conditions for every active alert.
      5. Fire Telegram and mark alert as triggered when hit.
    """
    from alerts.telegram import send_alert

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Which instruments need checking?
        rows = conn.execute("""
            SELECT DISTINCT instrument FROM price_alerts
            WHERE is_active = 1
              AND (expires_at IS NULL OR expires_at > ?)
        """, (now_iso,)).fetchall()

        if not rows:
            return

        instruments = [r[0] for r in rows]
        logger.debug("Price monitor checking %d instrument(s): %s", len(instruments), instruments)

        # Step 2: Fetch prices
        prices = _fetch_prices(instruments)

        if not prices:
            logger.debug("Price monitor: no prices returned for %s", instruments)
            return

        # Step 3 & 4: Update prices + check alerts
        for instrument, price in prices.items():
            prev_row = conn.execute(
                "SELECT price FROM instrument_prices WHERE instrument = ?", (instrument,)
            ).fetchone()
            prev_price = prev_row[0] if prev_row else None

            conn.execute("""
                INSERT INTO instrument_prices (instrument, price, prev_price, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(instrument) DO UPDATE SET
                    prev_price = instrument_prices.price,
                    price      = excluded.price,
                    updated_at = excluded.updated_at
            """, (instrument, price, prev_price, now_iso))
            conn.commit()

            if prev_price is None:
                continue

            # Step 4: Check each active alert for this instrument
            alerts = conn.execute("""
                SELECT pa.id, pa.condition, pa.price AS alert_price,
                       pa.message, u.telegram_chat_id
                FROM price_alerts pa
                LEFT JOIN users u ON pa.user_id = u.id
                WHERE pa.instrument = ? AND pa.is_active = 1
                  AND (pa.expires_at IS NULL OR pa.expires_at > ?)
            """, (instrument, now_iso)).fetchall()

            for alert_row in alerts:
                alert_id    = alert_row[0]
                condition   = alert_row[1]
                alert_price = alert_row[2]
                message     = alert_row[3]
                chat_id     = alert_row[4] or config.telegram_chat_id

                triggered = False
                direction_str = ""

                if condition == "crossing_up":
                    if prev_price < alert_price <= price:
                        triggered, direction_str = True, "above"
                elif condition == "crossing_down":
                    if prev_price > alert_price >= price:
                        triggered, direction_str = True, "below"
                else:  # crossing — either direction
                    if prev_price < alert_price <= price:
                        triggered, direction_str = True, "above"
                    elif prev_price > alert_price >= price:
                        triggered, direction_str = True, "below"

                if not triggered:
                    continue

                # Step 5: Mark triggered + send Telegram
                conn.execute(
                    "UPDATE price_alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
                    (now_iso, alert_id),
                )
                conn.commit()

                # Format price with correct decimal places
                if instrument.endswith("JPY"):
                    fmt = "{:.3f}"
                elif instrument in ("XAUUSD", "XAGUSD", "USOIL", "WTIUSD"):
                    fmt = "{:.2f}"
                elif instrument in ("US30", "NAS100", "SPX500", "UK100", "GER40", "JPN225"):
                    fmt = "{:.0f}"
                else:
                    fmt = "{:.5f}"

                text = (
                    f"⚡ Price Alert: {instrument}\n\n"
                    f"Price crossed {direction_str} {fmt.format(alert_price)}\n"
                    f"Current: {fmt.format(price)}"
                )
                if message:
                    text += f"\n\n{message}"

                logger.info(
                    "%s price alert triggered — %s @ %s (alert_id=%d)",
                    instrument, condition, alert_price, alert_id,
                )

                if config.telegram_enabled and chat_id:
                    await send_alert(config.telegram_bot_token, chat_id, text)

    except Exception as exc:
        logger.exception("Price monitor cycle failed: %s", exc)
    finally:
        conn.close()
