"""
TradingView feed health monitor (runs every 30 minutes).

Every Pine alert sends at least a PRICE_UPDATE at each H4 close, so an instrument
that has been silent for more than STALE_AFTER while its market is open means its
TradingView alert has stopped (paused, expired, deleted, script error, or the
TradingView plan lapsed). The owner gets one Telegram warning when a pair goes
quiet and one when it reports again — batched, never one message per pair.

Only instruments that have reported at least once are watched, so a pair whose
TradingView ticker doesn't match our name never raises a false alarm.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(hours=5)   # one H4 bar plus an hour of slack
_CRYPTO = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "LTC")

try:
    from zoneinfo import ZoneInfo
    _NY = ZoneInfo("America/New_York")
except Exception:  # tz data missing — fall back to a fixed 21:00 UTC session
    _NY = None


def is_crypto(instrument: str) -> bool:
    return instrument.replace("/", "").upper().startswith(_CRYPTO)


def is_market_open(instrument: str, at: datetime) -> bool:
    """Crypto never closes. Everything else follows the FX week: closed from
    Friday 17:00 to Sunday 17:00 New York time (DST-aware)."""
    from config import is_synthetic
    if is_crypto(instrument) or is_synthetic(instrument):   # 24/7 markets
        return True
    local = at.astimezone(_NY) if _NY else at - timedelta(hours=4)
    wd, hour = local.weekday(), local.hour  # Mon=0 … Sun=6
    if wd == 5:                       # Saturday
        return False
    if wd == 4 and hour >= 17:        # Friday after the close
        return False
    if wd == 6 and hour < 17:         # Sunday before the open
        return False
    return True


def _expected_live(instrument: str, now: datetime) -> bool:
    """True when the market has been open for the whole stale window, so silence is abnormal."""
    return is_market_open(instrument, now) and is_market_open(instrument, now - STALE_AFTER)


def _parse(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def feed_health(conn) -> list[dict]:
    """Status per instrument for the owner's Business page."""
    from config import normalize_symbol
    now = datetime.now(timezone.utc)
    out = []
    for r in conn.execute(
            "SELECT instrument, last_seen_at, last_type, stale_since FROM webhook_heartbeats ORDER BY instrument"):
        if normalize_symbol(r[0]) != r[0]:   # old broker-ticker row; reports under the platform name now
            continue
        last = _parse(r[1])
        if not is_market_open(r[0], now):
            status = "closed"
        elif _expected_live(r[0], now) and now - last > STALE_AFTER:
            status = "silent"
        else:
            status = "ok"
        out.append({"instrument": r[0], "last_seen_at": r[1], "last_type": r[2], "status": status})
    return out


def _fmt(dt: datetime) -> str:
    return dt.strftime("%a %H:%M UTC")


async def run_feed_check(db_path: str, config) -> None:
    from alerts.telegram import send_alert

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    now = datetime.now(timezone.utc)
    went_silent, recovered = [], []
    try:
        # Broker tickers (JP225, USOIL, ...) now report under the platform name,
        # so their old heartbeat rows would look silent forever.
        from config import normalize_symbol
        old = [(r[0],) for r in conn.execute("SELECT instrument FROM webhook_heartbeats").fetchall()
               if normalize_symbol(r[0]) != r[0]]
        conn.executemany("DELETE FROM webhook_heartbeats WHERE instrument = ?", old)
        rows = conn.execute(
            "SELECT instrument, last_seen_at, stale_since FROM webhook_heartbeats").fetchall()
        for inst, last_seen, stale_since in rows:
            last = _parse(last_seen)
            silent = _expected_live(inst, now) and now - last > STALE_AFTER
            if silent and not stale_since:
                conn.execute("UPDATE webhook_heartbeats SET stale_since = ? WHERE instrument = ?",
                             (now.isoformat(), inst))
                went_silent.append((inst, last))
            elif stale_since and last > _parse(stale_since):
                conn.execute("UPDATE webhook_heartbeats SET stale_since = NULL WHERE instrument = ?", (inst,))
                recovered.append(inst)
        # Keep ~4 months of H4 price history for the track record
        conn.execute("DELETE FROM price_ticks WHERE ts < ?",
                     ((now - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%S"),))
        conn.commit()
        total = len(rows)
    except Exception as exc:
        logger.exception("Feed check failed: %s", exc)
        return
    finally:
        conn.close()

    if not (config.telegram_enabled and config.telegram_chat_id):
        return
    if went_silent:
        names = ", ".join(sorted(i for i, _ in went_silent))
        oldest = min(t for _, t in went_silent)
        if len(went_silent) == total and total > 1:
            head = f"⚠️ TradingView has stopped sending data for ALL {total} instruments."
            hint = ("Likely causes: TradingView plan lapsed, alerts paused, or the webhook URL/secret changed. "
                    "Check TradingView → Alerts.")
        else:
            head = f"⚠️ No TradingView data for {len(went_silent)} instrument(s): {names}"
            hint = ("Their TradingView alert may be paused, expired, deleted or erroring. "
                    "Check TradingView → Alerts and restart them.")
        msg = f"{head}\nLast heard: {_fmt(oldest)} — no bias signals can fire for these until fixed.\n\n{hint}"
        await send_alert(config.telegram_bot_token, config.telegram_chat_id, msg)
        logger.warning("Feed silent: %s", names)
    if recovered:
        names = ", ".join(sorted(recovered))
        await send_alert(config.telegram_bot_token, config.telegram_chat_id,
                         f"✅ TradingView data is flowing again for: {names}")
        logger.info("Feed recovered: %s", names)
