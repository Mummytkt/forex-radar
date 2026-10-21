"""
High-impact economic news on subscribers' Telegram.

  • refresh_calendar (every 3 hours): ForexFactory's free weekly calendar feed
    (this week and next week) → news_events. High impact only.
  • run_news_summary (06:00 UTC daily = 07:00 WAT): the high-impact events of
    the next 24 hours for the currencies in each person's pairs.
  • run_news_reminders (every 5 minutes): one message 30 minutes before each
    release time (events at the same time are grouped).

Each person can switch news off in Alert Filters (preference 'news', on by
default). Every message is recorded in notices_sent, so nothing is sent twice
however often a job runs or the server restarts.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import httpx

logger = logging.getLogger(__name__)

FEEDS = (
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
)
REMIND_BEFORE = timedelta(minutes=30)
WAT = timezone(timedelta(hours=1))

FIAT = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD")
_INDEX_CCY = {"US30": "USD", "NAS100": "USD", "SPX500": "USD", "UK100": "GBP", "GER40": "EUR", "JPN225": "JPY"}


# ── Storage ───────────────────────────────────────────────────────────────────

def ensure_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_events (
            id        TEXT PRIMARY KEY,
            ts        TEXT NOT NULL,   -- ISO 8601 UTC
            currency  TEXT NOT NULL,
            title     TEXT NOT NULL,
            forecast  TEXT,
            previous  TEXT,
            fetched_at TEXT NOT NULL
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ts ON news_events (ts)")
    conn.commit()


def parse_feed(items: Iterable[dict]) -> list[dict]:
    """High-impact events from the ForexFactory JSON, times in UTC."""
    out = []
    for it in items or []:
        if str(it.get("impact", "")).lower() != "high":
            continue
        ccy = str(it.get("country", "")).upper()
        title = str(it.get("title", "")).strip()
        try:
            ts = datetime.fromisoformat(str(it["date"])).astimezone(timezone.utc)
        except Exception:
            continue
        if not ccy or not title:
            continue
        eid = hashlib.sha1(f"{ccy}|{title}|{ts.isoformat()}".encode()).hexdigest()[:16]
        out.append({"id": eid, "ts": ts.isoformat(), "currency": ccy, "title": title,
                    "forecast": (it.get("forecast") or "").strip() or None,
                    "previous": (it.get("previous") or "").strip() or None})
    return out


def store_events(conn, events: list[dict]) -> int:
    ensure_table(conn)
    now = datetime.now(timezone.utc).isoformat()
    for e in events:
        conn.execute(
            "INSERT INTO news_events (id, ts, currency, title, forecast, previous, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET forecast = excluded.forecast, previous = excluded.previous, fetched_at = excluded.fetched_at",
            (e["id"], e["ts"], e["currency"], e["title"], e["forecast"], e["previous"], now))
    # A rescheduled release would leave its old time behind: drop future events
    # this refresh no longer lists, and anything older than two weeks.
    if events:
        ids = [e["id"] for e in events]
        conn.execute(f"DELETE FROM news_events WHERE ts > ? AND id NOT IN ({','.join('?' * len(ids))})", (now, *ids))
    conn.execute("DELETE FROM news_events WHERE ts < ?", ((datetime.now(timezone.utc) - timedelta(days=14)).isoformat(),))
    conn.commit()
    return len(events)


async def refresh_calendar(db_path: str, config=None) -> None:
    items: list[dict] = []
    ok = False
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "MummyTKT-BiasPointer/1.0"}) as client:
        for url in FEEDS:
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    items += r.json()
                    ok = ok or url.endswith("thisweek.json")
                else:
                    logger.info("News feed %s returned %s", url, r.status_code)
            except Exception as exc:
                logger.warning("News feed %s failed: %s", url, exc)
    if not ok:
        return   # keep what we have rather than wiping the calendar
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        n = store_events(conn, parse_feed(items))
        logger.info("News calendar refreshed: %d high-impact events", n)
    finally:
        conn.close()


# ── Who gets what ─────────────────────────────────────────────────────────────

def currencies_for(instruments: Iterable[str]) -> set[str]:
    """Currencies whose news moves these instruments (synthetics have none)."""
    from config import is_synthetic
    out: set[str] = set()
    for inst in instruments:
        s = inst.replace("/", "").upper()
        if is_synthetic(s):
            continue
        if s in _INDEX_CCY:
            out.add(_INDEX_CCY[s])
            continue
        for c in FIAT:
            if s.startswith(c) or s.endswith(c):
                out.add(c)
    return out


def _recipients(conn, config) -> list[tuple[int, str, set[str]]]:
    """(user id, chat id, currencies) for everyone who should get news."""
    import json
    from api.alert_prefs import get_alert_prefs
    from api.tv_webhook import _subscription_active
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, telegram_chat_id, watched_instruments, role, plan, plan_expires_at FROM users "
        "WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != ''").fetchall()
    out = []
    for r in rows:
        if not _subscription_active(r["role"], r["plan"], r["plan_expires_at"]):
            continue
        if not get_alert_prefs(conn, r["id"], r["role"]).get("news", True):
            continue
        pairs = json.loads(r["watched_instruments"]) if r["watched_instruments"] else config.instruments
        out.append((r["id"], r["telegram_chat_id"], currencies_for(pairs)))
    return out


def _events_between(conn, start: datetime, end: datetime) -> list[sqlite3.Row]:
    ensure_table(conn)
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM news_events WHERE ts > ? AND ts <= ? ORDER BY ts, currency, title",
                        (start.isoformat(), end.isoformat())).fetchall()


# ── Message text ──────────────────────────────────────────────────────────────

def _when(ts: str) -> str:
    d = datetime.fromisoformat(ts)
    return f"{d.strftime('%a %d %b, %H:%M')} UTC ({d.astimezone(WAT).strftime('%H:%M')} WAT)"


def _figures(e) -> str:
    bits = []
    if e["forecast"]:
        bits.append(f"Forecast {e['forecast']}")
    if e["previous"]:
        bits.append(f"Previous {e['previous']}")
    return " · ".join(bits)


def summary_text(events) -> str:
    lines = ["📰 High-impact news in the next 24 hours", ""]
    for e in events:
        lines.append(_when(e["ts"]))
        lines.append(f"{e['currency']}: {e['title']}")
        fig = _figures(e)
        if fig:
            lines.append(fig)
        lines.append("")
    lines.append("Expect sharp moves on the affected pairs around these times.")
    return "\n".join(lines)


def reminder_text(events) -> str:
    lines = ["⏰ High-impact news in 30 minutes", "", _when(events[0]["ts"])]
    for e in events:
        fig = _figures(e)
        lines.append(f"{e['currency']}: {e['title']}" + (f"  ({fig})" if fig else ""))
    lines += ["", "Expect sharp moves on the affected pairs."]
    return "\n".join(lines)


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def run_news_summary(db_path: str, config, now: Optional[datetime] = None) -> int:
    """Morning summary of the next 24 hours. Returns how many people got one."""
    from alerts.reminders import notify_once
    now = now or datetime.now(timezone.utc)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    sent = 0
    try:
        events = _events_between(conn, now, now + timedelta(hours=24))
        if not events:
            return 0
        day = now.strftime("%Y-%m-%d")
        for uid, chat, ccys in _recipients(conn, config):
            mine = [e for e in events if e["currency"] in ccys]
            if mine and await notify_once(conn, config, f"news_day:{uid}:{day}", chat, summary_text(mine)):
                sent += 1
    finally:
        conn.close()
    return sent


async def run_news_reminders(db_path: str, config, now: Optional[datetime] = None) -> int:
    """A reminder 30 minutes before each release time. Returns messages sent."""
    from alerts.reminders import notify_once
    now = now or datetime.now(timezone.utc)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    sent = 0
    try:
        events = _events_between(conn, now, now + REMIND_BEFORE)
        if not events:
            return 0
        by_time: dict[str, list] = {}
        for e in events:
            by_time.setdefault(e["ts"], []).append(e)
        people = _recipients(conn, config)
        for ts, group in by_time.items():
            for uid, chat, ccys in people:
                mine = [e for e in group if e["currency"] in ccys]
                if mine and await notify_once(conn, config, f"news_rem:{uid}:{ts}", chat, reminder_text(mine)):
                    sent += 1
    finally:
        conn.close()
    return sent
