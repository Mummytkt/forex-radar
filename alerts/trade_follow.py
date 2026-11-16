"""
Follow the trade after an entry alert (owner request, 2026-11-11).

A level on the dashboard (an entry pattern alert) can follow the trade its confirmation gives:
  entry = the confirmation candle's close
  SL    = the pattern's wick (the low for buys, the high for sells), plus the level's buffer
  TP    = entry + tp_r x the risk          breakeven point = entry + be_r x the risk
The price monitor (every 5 minutes, 5-minute candles) then sends:
  - the breakeven point reached (once)
  - TP hit, or SL hit
  - after an SL: the level is armed again for a RE-ENTRY (user, 2026-11-16, later the same day): ANY pattern
    ticked on the level, on any ticked timeframe, in the same direction. Price has already gone back past the old
    entry (the SL is behind it), which is all a re-entry needs; where the new pattern forms does not matter. No
    limit on how many. The watch runs until an H4 candle (the POI timeframe) CLOSES with its body beyond the level (a buy:
    closes below it; a sell: above it), H4 candle after H4 candle; or until price goes on to the TP without one
    (reported: the stop was a shake-out), the level expires, or WATCH_DAYS.

LIMIT ENTRY (user, 2026-11-16, Documents/Limit_Entry_Rule.png): a level can take its entry as a limit order instead
of at the confirmation close. The limit goes at: CISD = the CISD line; OCTGD = the OC level; PCL = the PCL candle's
open; Engulfing = the close of the candle body it covered; Sweep and Break = the breaker. SL as above (the pattern's
wick + buffer); TP and breakeven are measured from the limit. Nothing is watched until price comes back to the limit
(LIMIT FILLED, then as above). The order is cancelled (CANCEL THE ORDER) when price reaches the TP first, or when an
H4 candle closes with its body beyond the level (a buy: below it; a sell: above it) before the fill.

Statuses: pending (limit not filled) -> open | cancelled ; open -> tp | sl (stopped, watching) -> sl_tp | left | reentered | expired
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import fmt_price, pip_size_for, tagged

logger = logging.getLogger(__name__)

WATCH_DAYS = 14          # a follow is dropped after this long, whatever its state
OPEN_STATES = ("open", "sl", "pending")

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
    closed_at     TEXT,
    candles       TEXT,
    mode          TEXT NOT NULL DEFAULT 'instant',
    filled_at     TEXT
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
                tf_label: str, entry: float, touch: Optional[float], pattern_level: Optional[float],
                candles: Optional[str] = None, limit_price: Optional[float] = None) -> Optional[str]:
    """Called when a level's entry alert fires. Returns the lines to add to the alert (None: not followed)."""
    if not alert.get("follow"):
        return None
    from alerts.price_monitor import _to_yf_ticker
    f = lambda v: fmt_price(instrument, v)
    bull = direction == "bullish"
    now = datetime.now(timezone.utc)
    alert_id = alert["id"]

    live = conn.execute(
        "SELECT id, status, opened_at, reentry_no FROM trade_follows WHERE alert_id = ? AND status IN ('open','sl','pending') ORDER BY id DESC",
        (alert_id,)).fetchall()
    if any(r["status"] == "open" for r in live):
        return "A trade from this level is still being followed: this one is not followed as well."
    if any(r["status"] == "pending" for r in live):
        return "A limit order from this level is still waiting to fill: this one is not followed as well."
    live = [r for r in live if r["status"] == "sl"]

    # Limit entry: the order waits at the pattern's limit price; else the entry is the confirmation close
    note = ""
    lim = None
    if (alert.get("entry_mode") or "instant") == "limit":
        lim = limit_for(pattern, direction, entry, pattern_level, candles, limit_price)
        if lim is None:
            note = "Limit entry: this alert carried no limit price (recreate the TradingView alert from the latest script), so it is followed as an instant entry.\n"
    confirm_close = entry
    if lim is not None:
        entry = lim

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
    mode = "limit" if lim is not None else "instant"
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
                                   zone_lo, zone_hi, reentry_no, status, opened_at, last_bar_at, candles, mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (alert_id, alert.get("user_id"), instrument, direction, pattern, tf_label, entry, sl, tp, be, tp_r, be_r,
          zone_lo, zone_hi, reentry_no, "pending" if mode == "limit" else "open", _iso(now), _iso(now), candles, mode))
    conn.commit()

    if mode == "limit":
        head = (f"🔁 RE-ENTRY {reentry_no}: LIMIT ORDER at your level" if reentry_no else "📥 LIMIT ORDER at your level")
        lines = [head,
                 f"{'Buy' if bull else 'Sell'} limit {f(entry)} ({_LIMIT_AT.get(_SAME.get(pattern, pattern), 'the pattern level')}) · "
                 f"SL {f(sl)} · TP {f(tp)} (1:{_r(tp_r)})"]
        if be is not None:
            lines.append(f"Breakeven alert at {f(be)} (1:{_r(be_r)})")
        if _to_yf_ticker(instrument) is None:
            lines.append("Note: there is no 5-minute price feed for this instrument, so the order can't be watched.")
        else:
            lines.append(f"Nothing is watched until price comes back to {f(entry)}: you'll get LIMIT FILLED, then breakeven, "
                         f"TP and SL. If price reaches the TP first, or an H4 candle closes with its body "
                         f"{'below' if bull else 'above'} your level before the fill, you'll get CANCEL THE ORDER.")
        return "\n".join(lines)

    head = f"🔁 RE-ENTRY {reentry_no} at your level" if reentry_no else "📌 Following this trade"
    lines = [note + head if note else head,
             f"Entry {f(entry)} · SL {f(sl)} · TP {f(tp)} (1:{_r(tp_r)})"]
    if be is not None:
        lines.append(f"Breakeven alert at {f(be)} (1:{_r(be_r)})")
    if _to_yf_ticker(instrument) is None:
        lines.append("Note: there is no 5-minute price feed for this instrument, so its SL / TP can't be watched.")
    else:
        lines.append("You'll get a message at breakeven, at TP and at SL. After an SL, any pattern you ticked forming again comes as a RE-ENTRY, until an H4 candle closes with its body beyond your level.")
    return "\n".join(lines)


_PAT_NAMES = {"pcl": "PCL", "engulfing_sweep": "PCL", "sweep": "PCL", "octgd": "OCTGD", "cisd": "CISD",
              "engulfing": "Engulfing", "sweep_break": "Sweep and Break"}
_SAME = {"engulfing_sweep": "pcl", "sweep": "pcl"}
_LIMIT_AT = {"cisd": "the CISD line", "octgd": "the OC level", "pcl": "the PCL candle's open",
             "engulfing": "the close of the candle it engulfed", "sweep_break": "the breaker"}


def limit_for(pattern: str, direction: str, close: float, pattern_level: Optional[float],
              candles: Optional[str], limit_price: Optional[float]) -> Optional[float]:
    """The limit price of a confirmation (user, 2026-11-16): CISD = the CISD line; OCTGD = the OC level; PCL = the
    PCL candle's open; Engulfing = the close of the candle it covered (its body, never the wick); Sweep and Break =
    the breaker (sent by the script). None when the alert can't give it, or it isn't on the retrace side of the close."""
    from alerts.chart_image import parse_candles
    pat = _SAME.get(pattern, pattern)
    lim = None
    if limit_price is None and pat == "sweep_break" and candles and "|" in candles:
        # the script sends "<candles>|<buy breaker>|<sell breaker>"
        parts = candles.split("|")
        try:
            raw = parts[1] if direction == "bullish" else parts[2]
            limit_price = float(raw) if raw.strip() else None
        except (IndexError, ValueError):
            limit_price = None
    if limit_price is not None:
        lim = limit_price
    elif pat in ("cisd", "octgd"):
        lim = pattern_level
    elif pat in ("pcl", "engulfing"):
        cs = parse_candles(candles)
        # the last candle sent is the confirmation candle: its close is the alert's close
        if len(cs) >= 2 and abs(cs[-1][4] - close) <= max(abs(close) * 1e-4, 1e-9):
            lim = cs[-1][1] if pat == "pcl" else cs[-2][4]
    if lim is None:
        return None
    # a buy's limit sits below the close (price comes back down to it); a sell's above
    if (direction == "bullish" and not lim < close) or (direction == "bearish" and not lim > close):
        return None
    return lim


def stopped_follow(conn: sqlite3.Connection, alert_id: int) -> Optional[dict]:
    """The level's stopped trade still watching for a re-entry, if any."""
    r = conn.execute("SELECT * FROM trade_follows WHERE alert_id = ? AND status = 'sl' ORDER BY id DESC LIMIT 1",
                     (alert_id,)).fetchone()
    return dict(r) if r else None


def is_reentry(fo: dict, pattern: str, tf_label: str, touch: Optional[float]) -> bool:
    """A re-entry (user, 2026-11-16, replacing "the same pattern past the SL" the same day): any pattern the level
    watches, on any timeframe it watches, in the trade's direction (the caller has already checked those). The
    only condition is that price went back past the old entry before it formed, and the SL hit proves that."""
    return fo.get("status") == "sl"


def level_of(fo: dict) -> Optional[float]:
    """The level the follow came from (the middle of its stored zone)."""
    if fo.get("zone_lo") is None or fo.get("zone_hi") is None:
        return None
    return (fo["zone_lo"] + fo["zone_hi"]) / 2


H4 = timedelta(hours=4)


def h4_failed_at(fo: dict, h4: list, now: datetime) -> Optional[datetime]:
    """When the POI failed after the stop: the close time of the first H4 candle (the one the SL happened in
    counts) that closed with its body beyond the level (a buy: close below it; a sell: close above it).
    h4: closed H4 candles (open datetime, o, h, l, c). None if none has yet."""
    lvl = level_of(fo)
    if lvl is None or not fo.get("sl_at"):
        return None
    sl_at = _parse(fo["sl_at"])
    bull = fo["direction"] == "bullish"
    for t, _o, _h, _l, c in sorted(h4, key=lambda x: x[0]):
        end = t + H4
        if end <= sl_at or end > now:
            continue
        if (c < lvl) if bull else (c > lvl):
            return end
    return None


def h4_cancel_at(fo: dict, h4: list, now: datetime) -> Optional[datetime]:
    """A limit order not yet filled: the close time of the first H4 candle ending after the confirmation that
    closed with its body beyond the level (a buy: below it; a sell: above it). None if none has."""
    lvl = level_of(fo)
    if lvl is None:
        return None
    opened = _parse(fo["opened_at"])
    bull = fo["direction"] == "bullish"
    for t, _o, _h, _l, c in sorted(h4, key=lambda x: x[0]):
        end = t + H4
        if end <= opened or end > now:
            continue
        if (c < lvl) if bull else (c > lvl):
            return end
    return None


def h4_from_bars(bars: list, now: datetime) -> list:
    """Closed H4 candles built from 5-minute candles, aligned like the forex H4 chart (17:00 New York + 4n),
    for instruments whose H4 candles don't come from TradingView."""
    from zoneinfo import ZoneInfo
    ny = ZoneInfo("America/New_York")
    buckets: dict = {}
    for b in bars:
        ln = b[0].astimezone(ny)
        anchor = ln.replace(hour=17, minute=0, second=0, microsecond=0)
        if anchor > ln:
            anchor -= timedelta(days=1)
        start = anchor + H4 * int((ln - anchor) / H4)
        k = start.astimezone(timezone.utc)
        if k in buckets:
            o, h, l, _c = buckets[k]
            buckets[k] = (o, max(h, b[2]), min(l, b[3]), b[4])
        else:
            buckets[k] = (b[1], b[2], b[3], b[4])
    return [(k, *v) for k, v in sorted(buckets.items()) if k + H4 <= now]


# ── One follow, the candles since it was last checked ────────────────────────

def step(fo: dict, bars: list, now: datetime, h4: Optional[list] = None) -> list[str]:
    """
    Advance one follow over the completed 5-minute candles after fo['last_bar_at'].
    Mutates fo (status, be_sent, last_bar_at, sl_at, closed_at) and returns the events, in order:
    'be' | 'tp' | 'sl' | 'sl_tp' | 'left' | 'expired'.
    A candle that touches both the SL and the TP counts as the SL (the cautious reading).
    h4: closed H4 candles (open datetime, o, h, l, c); after the SL, the first one closing beyond the level
    ends the re-entry watch ('left'). Defaults to H4 candles built from the 5-minute ones.
    """
    if h4 is None:
        h4 = h4_from_bars(bars, now)
    events: list[str] = []
    bull = fo["direction"] == "bullish"
    last = _parse(fo["last_bar_at"])
    for t, _o, h, l, c in bars:
        if t <= last or t + timedelta(minutes=5) > now:
            continue    # already seen, or still forming
        fo["last_bar_at"] = _iso(t)
        if fo["status"] == "pending":       # a limit order waiting to fill
            cancel = h4_cancel_at(fo, h4, now)
            if cancel is not None and t >= cancel:
                fo["status"], fo["closed_at"] = "cancelled", _iso(cancel)
                events.append("cancel_h4")
                break
            if l <= fo["entry"] if bull else h >= fo["entry"]:
                fo["status"], fo["filled_at"] = "open", _iso(t)
                events.append("filled")
                if l <= fo["sl"] if bull else h >= fo["sl"]:      # filled and stopped in the same 5 minutes
                    fo["status"], fo["sl_at"] = "sl", _iso(t)
                    events.append("sl")
                continue
            if h >= fo["tp"] if bull else l <= fo["tp"]:
                fo["status"], fo["closed_at"] = "cancelled", _iso(t)
                events.append("cancel_tp")
                break
            continue
        if fo["status"] == "open":
            hit_sl = l <= fo["sl"] if bull else h >= fo["sl"]
            if hit_sl:
                fo["status"], fo["sl_at"] = "sl", _iso(t)
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
            failed = h4_failed_at(fo, h4, now)
            if failed is not None and t >= failed:
                fo["status"], fo["closed_at"] = "left", _iso(failed)
                events.append("left")
                break
            if h >= fo["tp"] if bull else l <= fo["tp"]:
                fo["status"], fo["closed_at"] = "sl_tp", _iso(t)
                events.append("sl_tp")
                break
    if fo["status"] == "pending":
        cancel = h4_cancel_at(fo, h4, now)
        if cancel is not None:
            fo["status"], fo["closed_at"] = "cancelled", _iso(cancel)
            events.append("cancel_h4")
    if fo["status"] == "sl":     # an H4 close beyond the level after the last 5-minute candle
        failed = h4_failed_at(fo, h4, now)
        if failed is not None:
            fo["status"], fo["closed_at"] = "left", _iso(failed)
            events.append("left")
    if fo["status"] in OPEN_STATES and now - _parse(fo["opened_at"]) > timedelta(days=WATCH_DAYS):
        events.append("cancel_old" if fo["status"] == "pending" else "expired")
        fo["status"], fo["closed_at"] = ("cancelled" if fo["status"] == "pending" else "expired"), _iso(now)
    return events


def _text(fo: dict, ev: str) -> Optional[str]:
    inst = fo["instrument"]
    f = lambda v: fmt_price(inst, v)
    side = "BUY" if fo["direction"] == "bullish" else "SELL"
    limit = fo.get("mode") == "limit"
    head = f"{tagged(inst)} · {side} {'limit' if limit else 'from'} {f(fo['entry'])}"
    tp_r, be_r = _r(fo["tp_r"]), _r(fo["be_r"]) if fo.get("be_r") else ""
    if ev == "filled":
        be = f" · breakeven alert at {f(fo['be'])}" if fo.get("be") is not None else ""
        return (f"📥 Limit filled: {head}\n\nPrice came back to your limit {f(fo['entry'])}. The trade is on: "
                f"SL {f(fo['sl'])} · TP {f(fo['tp'])} (1:{tp_r}){be}. You'll get a message at breakeven, TP and SL.")
    if ev == "cancel_tp":
        return (f"❌ Cancel the order: {head}\n\nPrice reached the TP {f(fo['tp'])} without coming back to your limit "
                f"{f(fo['entry'])}, so the order never filled. Cancel it now.")
    if ev == "cancel_h4":
        lvl = level_of(fo)
        return (f"❌ Cancel the order: {head}\n\nAn H4 candle closed with its body "
                f"{'below' if fo['direction'] == 'bullish' else 'above'} your level{' ' + f(lvl) if lvl is not None else ''} "
                f"before the limit {f(fo['entry'])} filled: the POI failed.")
    if ev == "cancel_old":
        return f"❌ Cancel the order: {head}\n\nThe limit {f(fo['entry'])} hasn't filled in {WATCH_DAYS} days, so it is no longer watched."
    if ev == "be":
        return f"🟡 Breakeven point reached: {head}\n\nPrice reached {f(fo['be'])} (1:{be_r}). You can move the stop to your entry {f(fo['entry'])}.\nTP {f(fo['tp'])} is still ahead."
    if ev == "tp":
        return f"✅ Take profit hit: {head}\n\nPrice reached TP {f(fo['tp'])}: +{tp_r}R."
    if ev == "sl":
        pat = _PAT_NAMES.get(fo.get("pattern") or "", fo.get("pattern") or "pattern")
        bull = fo["direction"] == "bullish"
        past = "below" if bull else "above"
        lvl = level_of(fo)
        end = (f"The watch runs until an H4 candle closes with its body {past} your level {f(lvl)}. "
               if lvl is not None else "")
        return (f"🛑 Stop loss hit: {head}\n\nPrice reached SL {f(fo['sl'])}: -1R.\n"
                f"Re-entry watch: any pattern you ticked on this level that forms now comes as a RE-ENTRY. {end}"
                f"I'll also tell you if price goes on to the TP {f(fo['tp'])} without one.")
    if ev == "left":
        bull = fo["direction"] == "bullish"
        lvl = level_of(fo)
        return (f"↩️ Re-entry watch ended: {head}\n\nAn H4 candle closed with its body {'below' if bull else 'above'} "
                f"your level{' ' + f(lvl) if lvl is not None else ''} after the stop: the POI failed, so no re-entry is watched.")
    if ev == "sl_tp":
        return (f"ℹ️ Price went on to the TP after your stop: {head}\n\nAfter the SL at {f(fo['sl'])}, price reached the TP {f(fo['tp'])} "
                f"with no new confirmation at your level. The stop was a shake-out: a re-entry would have won.")
    return None


# ── The price monitor's cycle ────────────────────────────────────────────────

def follow_instruments(conn: sqlite3.Connection) -> list[str]:
    try:
        return [r[0] for r in conn.execute("SELECT DISTINCT instrument FROM trade_follows WHERE status IN ('open','sl','pending')")]
    except sqlite3.OperationalError:
        return []


def _stored_h4(conn: sqlite3.Connection, fo: dict, now: datetime) -> Optional[list]:
    """The closed H4 candles TradingView sent for the instrument since the follow opened; None when it
    sends none, so the H4 candles are built from the 5-minute ones instead."""
    try:
        since = (_parse(fo["opened_at"]) - H4).isoformat()
        rows = conn.execute("SELECT ts, o, h, l, c FROM candles WHERE instrument = ? AND tf = 'H4' AND ts > ? ORDER BY ts",
                            (fo["instrument"], since)).fetchall()
    except sqlite3.OperationalError:
        return None
    if not rows:
        return None
    return [(_parse(r[0]), r[1], r[2], r[3], r[4]) for r in rows if _parse(r[0]) + H4 <= now]


async def check_follows(conn: sqlite3.Connection, config, prices: dict, now: datetime) -> None:
    """Advance every live follow over the new 5-minute candles and send what happened."""
    from alerts.telegram import send_alert
    rows = conn.execute("""
        SELECT tf.*, u.telegram_chat_id AS chat, u.role, u.plan, u.plan_expires_at,
               epa.keep_open, epa.expires_at AS alert_expires
        FROM trade_follows tf
        LEFT JOIN users u ON u.id = tf.user_id
        LEFT JOIN entry_pattern_alerts epa ON epa.id = tf.alert_id
        WHERE tf.status IN ('open','sl','pending')
    """).fetchall()
    from alerts.follow_chart import h4_rows, standin_offset, shift, follow_picture
    offsets: dict = {}
    for row in rows:
        fo = dict(row)
        data = prices.get(fo["instrument"])
        bars = (data or {}).get("bars") or []
        # gold, oil, indices: Yahoo's stand-in moved onto the TradingView price (forex / crypto: unchanged)
        if fo["instrument"] not in offsets:
            offsets[fo["instrument"]] = standin_offset(fo["instrument"], bars, h4_rows(conn, fo["instrument"]))
        off = offsets[fo["instrument"]]
        if off:
            bars = shift(bars, off)
        events = step(fo, bars, now, _stored_h4(conn, fo, now))
        conn.execute("UPDATE trade_follows SET status = ?, be_sent = ?, last_bar_at = ?, sl_at = ?, closed_at = ?, filled_at = ? WHERE id = ?",
                     (fo["status"], fo["be_sent"], fo["last_bar_at"], fo["sl_at"], fo["closed_at"], fo.get("filled_at"), fo["id"]))
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
        from api.tv_webhook import _send_entry
        for ev in events:
            text = _text(fo, ev)
            logger.info("%s trade follow %d: %s", fo["instrument"], fo["id"], ev)
            if text and config.telegram_enabled and chat_id:
                try:   # every follow message comes with its chart (user, 2026-11-16)
                    pic = follow_picture(conn, fo, ev, bars if off is not None else None, now)
                except Exception:
                    logger.exception("%s follow chart failed", fo["instrument"])
                    pic = None
                await _send_entry(config.telegram_bot_token, chat_id, text, pic)


def summary(fo: dict) -> str:
    """One line for the dashboard: the latest follow of a level."""
    f = lambda v: fmt_price(fo["instrument"], v)
    if fo["status"] == "pending":
        return f"Limit {f(fo['entry'])} · SL {f(fo['sl'])} · TP {f(fo['tp'])} · waiting to fill"
    if fo["status"] == "cancelled":
        return f"Limit {f(fo['entry'])} · SL {f(fo['sl'])} · TP {f(fo['tp'])} · order cancelled (never filled)"
    state = {"open": ("filled" if fo.get("mode") == "limit" else "open") + (" · breakeven point reached" if fo.get("be_sent") else ""),
             "tp": "TP hit", "sl": "SL hit · watching for a re-entry (any ticked pattern) until an H4 close beyond the level",
             "sl_tp": "SL hit, then price reached the TP",
             "left": "SL hit · an H4 candle closed beyond the level", "reentered": "SL hit · re-entered", "expired": "ended"}.get(fo["status"], fo["status"])
    return f"Entry {f(fo['entry'])} · SL {f(fo['sl'])} · TP {f(fo['tp'])} · {state}"
