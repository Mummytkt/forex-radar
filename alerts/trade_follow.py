"""
Follow the trade after an entry alert (owner request, 2026-11-11).

A level on the dashboard (an entry pattern alert) can follow the trade its confirmation gives:
  entry = the confirmation candle's close
  SL    = the pattern's wick (the low for buys, the high for sells), plus the level's buffer
  TP    = entry + tp_r x the risk          breakeven point = entry + be_r x the risk
The price monitor (every 5 minutes, 5-minute candles) then sends:
  - the breakeven point reached (once)
  - TP hit, or SL hit
  - after an SL: the level is armed again for a RE-ENTRY for as long as price stays inside the level's
    zone (level +/- tolerance). It ends when a candle closes beyond the zone, or when price goes on to the
    TP without a re-entry (that is reported: the stop was a shake-out).

Statuses: open -> tp | sl (stopped, watching) -> sl_tp | left | reentered | expired
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import fmt_price, pip_size_for, tagged

logger = logging.getLogger(__name__)

WATCH_DAYS = 14          # a follow is dropped after this long, whatever its state
OPEN_STATES = ("open", "sl")

SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_follows (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id      INTEGER,
    user_id       INTEGER,
    instrument    TEXT    NOT NULL,
    direction     TEXT    NOT NULL,
    pattern       TEXT,
    tf            TEXT,
    entry         REAL    NOT NULL,
    sl            REAL    NOT NULL,
    tp            REAL    NOT NULL,
    be            REAL,
    tp_r          REAL    NOT NULL DEFAULT 2,
    be_r          REAL,
    zone_lo       REAL,
    zone_hi       REAL,
    be_sent       INTEGER NOT NULL DEFAULT 0,
    rearmed       INTEGER NOT NULL DEFAULT 0,
    reentry_no    INTEGER NOT NULL DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'open',
    opened_at     TEXT    NOT NULL,
    last_bar_at   TEXT    NOT NULL,
    sl_at         TEXT,
    closed_at     TEXT
)
"""


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _r(v: float) -> str:
    return f"{v:g}"


# ── Opening a follow when an entry alert fires ───────────────────────────────

def open_follow(conn: sqlite3.Connection, alert: dict, instrument: str, direction: str, pattern: str,
                tf_label: str, entry: float, touch: Optional[float], pattern_level: Optional[float]) -> Optional[str]:
    """Called when a level's entry alert fires. Returns the lines to add to the alert (None: not followed)."""
    if not alert.get("follow"):
        return None
    from alerts.price_monitor import _to_yf_ticker
    f = lambda v: fmt_price(instrument, v)
    bull = direction == "bullish"
    now = datetime.now(timezone.utc)
    alert_id = alert["id"]

    live = conn.execute(
        "SELECT id, status, opened_at, reentry_no FROM trade_follows WHERE alert_id = ? AND status IN ('open','sl') ORDER BY id DESC",
        (alert_id,)).fetchall()
    if any(r["status"] == "open" for r in live):
        return "A trade from this level is still being followed: this one is not followed as well."

    # SL behind the pattern: its wick; else the pattern's level, when that is on the right side of the entry
    pip = pip_size_for(instrument)
    buf = float(alert.get("sl_buffer_pips") or 0) * pip
    base = None
    for cand in (touch, pattern_level):
        if cand is not None and ((bull and cand < entry) or (not bull and cand > entry)):
            base = cand
            break
    if base is None:
        return "Not followed: the alert carried no wick behind the entry to put the stop at."
    sl = base - buf if bull else base + buf
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    tp_r = float(alert.get("tp_r") or 2)
    be_r = alert.get("be_r")
    be_r = float(be_r) if be_r else None
    sign = 1 if bull else -1
    tp = entry + sign * tp_r * risk
    be = entry + sign * be_r * risk if be_r and be_r < tp_r else None
    tol = float(alert.get("tolerance_pips") or 20) * pip
    zone_lo, zone_hi = alert["price"] - tol, alert["price"] + tol

    reentry_no = 0
    for r in live:      # stopped ones: this is the re-entry
        reentry_no = max(reentry_no, int(r["reentry_no"] or 0) + 1)
        conn.execute("UPDATE trade_follows SET status = 'reentered', closed_at = ? WHERE id = ?", (_iso(now), r["id"]))

    conn.execute("""
        INSERT INTO trade_follows (alert_id, user_id, instrument, direction, pattern, tf, entry, sl, tp, be, tp_r, be_r,
                                   zone_lo, zone_hi, reentry_no, status, opened_at, last_bar_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
    """, (alert_id, alert.get("user_id"), instrument, direction, pattern, tf_label, entry, sl, tp, be, tp_r, be_r,
          zone_lo, zone_hi, reentry_no, _iso(now), _iso(now)))
    conn.commit()

    head = f"🔁 RE-ENTRY {reentry_no} at your level" if reentry_no else "📌 Following this trade"
    lines = [head,
             f"Entry {f(entry)} · SL {f(sl)} · TP {f(tp)} (1:{_r(tp_r)})"]
    if be is not None:
        lines.append(f"Breakeven alert at {f(be)} (1:{_r(be_r)})")
    if _to_yf_ticker(instrument) is None:
        lines.append("Note: there is no 5-minute price feed for this instrument, so its SL / TP can't be watched.")
    else:
        lines.append("You'll get a message at breakeven, at TP and at SL. After an SL the level is watched for a re-entry while price stays in its zone.")
    return "\n".join(lines)


# ── One follow, the candles since it was last checked ────────────────────────

def step(fo: dict, bars: list, now: datetime) -> list[str]:
    """
    Advance one follow over the completed 5-minute candles after fo['last_bar_at'].
    Mutates fo (status, be_sent, last_bar_at, sl_at, closed_at) and returns the events, in order:
    'be' | 'tp' | 'sl' | 'sl_left' | 'sl_tp' | 'left' | 'expired'.
    A candle that touches both the SL and the TP counts as the SL (the cautious reading).
    """
    events: list[str] = []
    bull = fo["direction"] == "bullish"
    last = _parse(fo["last_bar_at"])
    for t, _o, h, l, c in bars:
        if t <= last or t + timedelta(minutes=5) > now:
            continue    # already seen, or still forming
        fo["last_bar_at"] = _iso(t)
        if fo["status"] == "open":
            hit_sl = l <= fo["sl"] if bull else h >= fo["sl"]
            if hit_sl:
                fo["status"], fo["sl_at"] = "sl", _iso(t)
                out = fo.get("zone_lo") is not None and (c < fo["zone_lo"] if bull else c > fo["zone_hi"])
                if out:
                    fo["status"], fo["closed_at"] = "left", _iso(t)
                    events.append("sl_left")
                    break
                events.append("sl")
                continue
            if fo.get("be") is not None and not fo.get("be_sent") and (h >= fo["be"] if bull else l <= fo["be"]):
                fo["be_sent"] = 1
                events.append("be")
            if h >= fo["tp"] if bull else l <= fo["tp"]:
                fo["status"], fo["closed_at"] = "tp", _iso(t)
                events.append("tp")
                break
        elif fo["status"] == "sl":
            if h >= fo["tp"] if bull else l <= fo["tp"]:
                fo["status"], fo["closed_at"] = "sl_tp", _iso(t)
                events.append("sl_tp")
                break
            if fo.get("zone_lo") is not None and (c < fo["zone_lo"] if bull else c > fo["zone_hi"]):
                fo["status"], fo["closed_at"] = "left", _iso(t)
                events.append("left")
                break
    if fo["status"] in OPEN_STATES and now - _parse(fo["opened_at"]) > timedelta(days=WATCH_DAYS):
        fo["status"], fo["closed_at"] = "expired", _iso(now)
        events.append("expired")
    return events


def _text(fo: dict, ev: str) -> Optional[str]:
    inst = fo["instrument"]
    f = lambda v: fmt_price(inst, v)
    side = "BUY" if fo["direction"] == "bullish" else "SELL"
    head = f"{tagged(inst)} · {side} from {f(fo['entry'])}"
    tp_r, be_r = _r(fo["tp_r"]), _r(fo["be_r"]) if fo.get("be_r") else ""
    if ev == "be":
        return f"🟡 Breakeven point reached: {head}\n\nPrice reached {f(fo['be'])} (1:{be_r}). You can move the stop to your entry {f(fo['entry'])}.\nTP {f(fo['tp'])} is still ahead."
    if ev == "tp":
        return f"✅ Take profit hit: {head}\n\nPrice reached TP {f(fo['tp'])}: +{tp_r}R."
    if ev == "sl":
        return (f"🛑 Stop loss hit: {head}\n\nPrice reached SL {f(fo['sl'])}: -1R.\n"
                f"Price is still inside your zone ({f(fo['zone_lo'])} – {f(fo['zone_hi'])}), so the level is armed again: "
                f"you'll get the next confirmation there as a RE-ENTRY. I'll also tell you if price goes on to the TP {f(fo['tp'])} without one.")
    if ev == "sl_left":
        return (f"🛑 Stop loss hit: {head}\n\nPrice reached SL {f(fo['sl'])}: -1R.\n"
                f"The candle closed outside your zone ({f(fo['zone_lo'])} – {f(fo['zone_hi'])}), so no re-entry is watched.")
    if ev == "sl_tp":
        return (f"ℹ️ Price went on to the TP after your stop: {head}\n\nAfter the SL at {f(fo['sl'])}, price reached the TP {f(fo['tp'])} "
                f"with no new confirmation at your level. The stop was a shake-out: a re-entry would have won.")
    if ev == "left":
        return (f"↩️ Re-entry watch ended: {head}\n\nA candle closed outside your zone ({f(fo['zone_lo'])} – {f(fo['zone_hi'])}) "
                f"after the stop. The level is no longer watched for a re-entry.")
    return None


# ── The price monitor's cycle ────────────────────────────────────────────────

def follow_instruments(conn: sqlite3.Connection) -> list[str]:
    try:
        return [r[0] for r in conn.execute("SELECT DISTINCT instrument FROM trade_follows WHERE status IN ('open','sl')")]
    except sqlite3.OperationalError:
        return []


async def check_follows(conn: sqlite3.Connection, config, prices: dict, now: datetime) -> None:
    """Advance every live follow over the new 5-minute candles and send what happened."""
    from alerts.telegram import send_alert
    rows = conn.execute("""
        SELECT tf.*, u.telegram_chat_id AS chat, u.role, u.plan, u.plan_expires_at,
               epa.keep_open, epa.expires_at AS alert_expires
        FROM trade_follows tf
        LEFT JOIN users u ON u.id = tf.user_id
        LEFT JOIN entry_pattern_alerts epa ON epa.id = tf.alert_id
        WHERE tf.status IN ('open','sl')
    """).fetchall()
    for row in rows:
        fo = dict(row)
        data = prices.get(fo["instrument"])
        bars = (data or {}).get("bars") or []
        events = step(fo, bars, now)
        conn.execute("UPDATE trade_follows SET status = ?, be_sent = ?, last_bar_at = ?, sl_at = ?, closed_at = ? WHERE id = ?",
                     (fo["status"], fo["be_sent"], fo["last_bar_at"], fo["sl_at"], fo["closed_at"], fo["id"]))
        now_iso = _iso(now)
        for ev in events:
            if ev == "sl" and fo["alert_id"]:
                # the level hears the next confirmation in its zone again (the re-entry), unless it has expired
                cur = conn.execute("""UPDATE entry_pattern_alerts SET is_active = 1
                                      WHERE id = ? AND (expires_at IS NULL OR expires_at > ?)""", (fo["alert_id"], now_iso))
                if cur.rowcount:
                    conn.execute("UPDATE trade_follows SET rearmed = 1 WHERE id = ?", (fo["id"],))
                    fo["rearmed"] = 1
            if ev in ("left", "sl_tp") and fo.get("rearmed") and fo["alert_id"] and not fo.get("keep_open"):
                conn.execute("UPDATE entry_pattern_alerts SET is_active = 0 WHERE id = ?", (fo["alert_id"],))
        conn.commit()
        if not events:
            continue
        try:
            from api.tv_webhook import _resolve_chat
            chat_id = _resolve_chat(config, fo["user_id"], fo["chat"], fo["role"], fo["plan"], fo["plan_expires_at"])
        except Exception:
            chat_id = fo["chat"] or config.telegram_chat_id
        for ev in events:
            text = _text(fo, ev)
            logger.info("%s trade follow %d: %s", fo["instrument"], fo["id"], ev)
            if text and config.telegram_enabled and chat_id:
                await send_alert(config.telegram_bot_token, chat_id, text)


def summary(fo: dict) -> str:
    """One line for the dashboard: the latest follow of a level."""
    f = lambda v: fmt_price(fo["instrument"], v)
    state = {"open": "open" + (" · breakeven point reached" if fo.get("be_sent") else ""),
             "tp": "TP hit", "sl": "SL hit · watching for a re-entry", "sl_tp": "SL hit, then price reached the TP",
             "left": "SL hit · price left the zone", "reentered": "SL hit · re-entered", "expired": "ended"}.get(fo["status"], fo["status"])
    return f"Entry {f(fo['entry'])} · SL {f(fo['sl'])} · TP {f(fo['tp'])} · {state}"
