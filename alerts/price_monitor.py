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

from config import tagged
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


def _fetch_prices(instruments: list[str]) -> dict[str, dict]:
    """
    Fetch current OHLC for a list of instruments via Yahoo Finance.
    Returns {instrument: {price, high, low, bars}}; bars = the 5-minute candles
    [(open_time, o, h, l, c), ...] oldest first. Missing instruments are omitted.
    """
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        logger.error("yfinance/pandas not installed — run: pip install yfinance pandas")
        return {}

    sym_map: dict[str, str] = {}
    for inst in instruments:
        sym = _to_yf_ticker(inst)
        if sym:
            sym_map[inst] = sym

    if not sym_map:
        return {}

    unique_syms = list(dict.fromkeys(sym_map.values()))
    prices: dict[str, dict] = {}

    try:
        tickers_arg = unique_syms if len(unique_syms) > 1 else unique_syms[0]
        raw = yf.download(
            tickers_arg,
            period="2d",
            interval="5m",
            progress=False,
            auto_adjust=True,
        )

        if raw.empty:
            logger.debug("yfinance returned empty DataFrame for %s", unique_syms)
            return {}

        multi = isinstance(raw["Close"], pd.DataFrame)

        for inst, sym in sym_map.items():
            try:
                def _col(field: str) -> "pd.Series":
                    s = raw[field][sym] if multi else raw[field]
                    return s.dropna()

                close_col = _col("Close")
                if close_col.empty:
                    continue
                val = float(close_col.iloc[-1])
                if val != val:  # NaN check
                    continue
                high_col = _col("High")
                low_col  = _col("Low")
                high_val = float(high_col.iloc[-1]) if not high_col.empty else val
                low_val  = float(low_col.iloc[-1])  if not low_col.empty  else val
                open_col = _col("Open")
                bars = []
                for ts in close_col.index:
                    try:
                        t = ts.to_pydatetime()
                        t = t.astimezone(timezone.utc) if t.tzinfo else t.replace(tzinfo=timezone.utc)
                        c_ = float(close_col[ts])
                        bars.append((t, float(open_col.get(ts, c_)), float(high_col.get(ts, c_)),
                                     float(low_col.get(ts, c_)), c_))
                    except Exception:
                        continue
                prices[inst] = {"price": val, "high": high_val, "low": low_val, "bars": bars}
            except Exception as exc:
                logger.debug("Could not extract price for %s (%s): %s", inst, sym, exc)

    except Exception as exc:
        logger.warning("yfinance batch download failed: %s", exc)

    return prices


_TF_MINUTES: dict[str, int] = {
    "5m": 5, "15m": 15, "30m": 30, "45m": 45,
    "1h": 60, "2h": 120, "3h": 180, "4h": 240,
}


def tf_candle(bars: list, timeframe: str, now: datetime) -> Optional[tuple]:
    """The candle of this timeframe that has just closed, built from its 5-minute
    candles: (o, h, l, c, prev_close). prev_close = the close of the candle before
    it (for "closes above / below"). None if its 5-minute candles aren't in yet.
    Candles are aligned to 00:00 UTC (4h: 00, 04, 08, ... like the H4 chart)."""
    from datetime import timedelta
    tf_min = _TF_MINUTES.get(timeframe, 5)
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    mins = (now - day0).total_seconds() // 60
    end = day0 + timedelta(minutes=(mins // tf_min) * tf_min)
    start = end - timedelta(minutes=tf_min)
    inside = [b for b in bars if start <= b[0] < end]
    if not inside:
        return None
    before = [b for b in bars if b[0] < start]
    prev_close = before[-1][4] if before else None
    return (inside[0][1], max(b[2] for b in inside), min(b[3] for b in inside), inside[-1][4], prev_close)


def _is_candle_close_window(timeframe: str, now: datetime) -> bool:
    """Return True if now falls within a candle-close window for this timeframe."""
    tf_min = _TF_MINUTES.get(timeframe, 5)
    total_min = now.hour * 60 + now.minute
    # Round down to nearest 5-min slot (price monitor fires every 5 min)
    slot = (total_min // 5) * 5
    return slot % tf_min == 0


# ── Daily / Weekly candle closes (Level Watch 1D / 1W) ──────────────────────
# Read from the Daily candles the Bias Pointer sends from TradingView (the same
# candles the person sees there); a Weekly candle is built from them. Only
# COMPLETED candles that closed after the alert was set are checked.

_HTF = {"1D": "Daily", "1W": "Weekly"}


def _price_fmt(instrument: str) -> str:
    if instrument.endswith("JPY"):
        return "{:.3f}"
    if instrument in ("XAUUSD", "XAGUSD", "USOIL", "WTIUSD"):
        return "{:.2f}"
    if instrument in ("US30", "NAS100", "SPX500", "UK100", "GER40", "JPN225"):
        return "{:.0f}"
    return "{:.5f}"


def _parse_ts(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace(" ", "T").replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _always_open(instrument: str) -> bool:
    """Markets that trade at weekends (their week ends on Sunday)."""
    return any(instrument.startswith(b) for b in _CRYPTO_BASES)


def htf_candles(conn, instrument: str, tf: str) -> list[tuple]:
    """Completed candles, oldest first: (open_time, close_time, o, h, l, c)."""
    from datetime import timedelta
    from state.candles import recent
    days = [(_parse_ts(t), o, h, l, c) for t, o, h, l, c in recent(conn, instrument, "D", 60)]
    if not days:
        return []
    if tf == "1D":
        out = []
        for i, (t, o, h, l, c) in enumerate(days):
            end = days[i + 1][0] if i + 1 < len(days) else t + timedelta(days=1)
            out.append((t, end, o, h, l, c))
        return out
    # Weekly: group the Daily candles by trading week (a Daily candle that opens on
    # Sunday evening UTC belongs to Monday's week, hence the +12 h)
    weeks: dict = {}
    for t, o, h, l, c in days:
        key = (t + timedelta(hours=12)).isocalendar()[:2]
        w = weeks.get(key)
        if w is None:
            weeks[key] = [t, t, o, h, l, c]
        else:
            w[1] = t
            w[3] = max(w[3], h)
            w[4] = min(w[4], l)
            w[5] = c
    keys = sorted(weeks)
    out = []
    for i, k in enumerate(keys):
        t0, tlast, o, h, l, c = weeks[k]
        if i + 1 < len(keys):
            end = weeks[keys[i + 1]][0]
        else:
            # the latest week is complete once its last trading day is in
            last_day = (tlast + timedelta(hours=12)).weekday()
            if last_day < (6 if _always_open(instrument) else 4):
                continue
            end = tlast + timedelta(days=1)
        out.append((t0, end, o, h, l, c))
    return out


def htf_triggered(condition: str, level: float, prev_close: Optional[float], h: float, l: float, c: float) -> str:
    """'' if not triggered, else how: 'above' / 'below' / 'from above' / 'from below'."""
    if condition == "rejects":
        if h >= level and c < level:
            return "from above"
        if l <= level and c > level:
            return "from below"
        return ""
    if prev_close is None:
        return ""
    if condition in ("crossing_up", "crossing") and prev_close < level <= c:
        return "above"
    if condition in ("crossing_down", "crossing") and prev_close > level >= c:
        return "below"
    return ""


async def _check_htf(conn, config, now_iso: str) -> None:
    from alerts.telegram import send_alert
    rows = conn.execute("""
        SELECT pa.id, pa.instrument, pa.condition, pa.price, pa.message, pa.timeframe,
               pa.created_at, u.telegram_chat_id
        FROM price_alerts pa
        LEFT JOIN users u ON pa.user_id = u.id
        WHERE pa.is_active = 1 AND pa.trigger_type = 'on_candle_close'
          AND pa.timeframe IN ('1D', '1W')
          AND (pa.expires_at IS NULL OR pa.expires_at > ?)
    """, (now_iso,)).fetchall()
    cache: dict = {}
    for aid, inst, cond, level, message, tf, created, chat in rows:
        key = (inst, tf)
        if key not in cache:
            cache[key] = htf_candles(conn, inst, tf)
        candles = cache[key]
        if not candles:
            continue
        set_at = _parse_ts(created) if created else None
        # the latest completed candle, if it closed after the alert was set
        t0, end, o, h, l, c = candles[-1]
        if set_at is not None and end <= set_at:
            continue
        prev_close = candles[-2][5] if len(candles) > 1 else None
        how = htf_triggered(cond, level, prev_close, h, l, c)
        if not how:
            continue
        conn.execute("UPDATE price_alerts SET is_active = 0, triggered_at = ? WHERE id = ?", (now_iso, aid))
        conn.commit()
        fmt = _price_fmt(inst)
        name = _HTF[tf]
        if cond == "rejects":
            text = (f"⚡ Price Alert: {tagged(inst)}\n\n"
                    f"{name} rejection at {fmt.format(level)} ({how})\n"
                    f"{name} close: {fmt.format(c)}")
        else:
            text = (f"⚡ Price Alert: {tagged(inst)}\n\n"
                    f"{name} candle closed {how} {fmt.format(level)}\n"
                    f"{name} close: {fmt.format(c)}")
        if message:
            text += f"\n\n{message}"
        logger.info("%s %s price alert triggered — %s @ %s (alert_id=%d)", inst, tf, cond, level, aid)
        chat_id = chat or config.telegram_chat_id
        if config.telegram_enabled and chat_id:
            await send_alert(config.telegram_bot_token, chat_id, text)


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

        # Daily / Weekly candle-close alerts: from the stored TradingView Daily candles
        try:
            await _check_htf(conn, config, now_iso)
        except Exception as exc:
            logger.warning("Daily / Weekly level check failed: %s", exc)

        instruments = [r[0] for r in rows]
        logger.debug("Price monitor checking %d instrument(s): %s", len(instruments), instruments)

        # Step 2: Fetch prices
        prices = _fetch_prices(instruments)

        if not prices:
            logger.debug("Price monitor: no prices returned for %s", instruments)
            return

        # Step 3 & 4: Update prices + check alerts
        for instrument, candle_data in prices.items():
            price = candle_data["price"]
            high  = candle_data.get("high", price)
            low   = candle_data.get("low",  price)
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
                       pa.message, pa.trigger_type, pa.timeframe, u.telegram_chat_id
                FROM price_alerts pa
                LEFT JOIN users u ON pa.user_id = u.id
                WHERE pa.instrument = ? AND pa.is_active = 1
                  AND (pa.expires_at IS NULL OR pa.expires_at > ?)
            """, (instrument, now_iso)).fetchall()

            now_dt = datetime.now(timezone.utc)
            for alert_row in alerts:
                alert_id    = alert_row[0]
                condition   = alert_row[1]
                alert_price = alert_row[2]
                message     = alert_row[3]
                trigger_type = alert_row[4]
                timeframe   = alert_row[5] or "5m"
                chat_id     = alert_row[6] or config.telegram_chat_id

                if trigger_type == "on_candle_close" and timeframe in _HTF:
                    continue   # checked on the Daily / Weekly close (_check_htf)
                # For on_candle_close, only fire at the correct timeframe boundary
                if trigger_type == "on_candle_close" and not _is_candle_close_window(timeframe, now_dt):
                    continue

                triggered = False
                direction_str = ""
                shown_close = price   # the close quoted in the message

                # On candle close: the whole candle of that timeframe (built from its
                # 5-minute candles), not just the last 5 minutes of it
                if trigger_type == "on_candle_close" and timeframe != "5m":
                    cndl = tf_candle(candle_data.get("bars") or [], timeframe, now_dt)
                    if cndl is None:
                        continue
                    _o, c_high, c_low, c_close, c_prev = cndl
                    how = htf_triggered(condition, alert_price, c_prev, c_high, c_low, c_close)
                    if not how:
                        continue
                    triggered, direction_str = True, how
                    shown_close = c_close

                if triggered:
                    pass
                elif condition == "crossing_up":
                    if prev_price < alert_price <= price:
                        triggered, direction_str = True, "above"
                elif condition == "crossing_down":
                    if prev_price > alert_price >= price:
                        triggered, direction_str = True, "below"
                elif condition == "rejects":
                    # Bearish rejection: wick reached/exceeded level, close back below
                    if high >= alert_price and price < alert_price:
                        triggered, direction_str = True, "from above"
                    # Bullish rejection: wick dipped to/below level, close back above
                    elif low <= alert_price and price > alert_price:
                        triggered, direction_str = True, "from below"
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

                if condition == "rejects":
                    text = (
                        f"⚡ Price Alert: {tagged(instrument)}\n\n"
                        f"Price rejected at {fmt.format(alert_price)} ({direction_str})\n"
                        f"Close: {fmt.format(shown_close)}"
                    )
                else:
                    text = (
                        f"⚡ Price Alert: {tagged(instrument)}\n\n"
                        f"Price crossed {direction_str} {fmt.format(alert_price)}\n"
                        f"{'Close' if trigger_type == 'on_candle_close' else 'Current'}: {fmt.format(shown_close)}"
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
