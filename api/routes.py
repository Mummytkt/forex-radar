from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

import csv
import io

from fastapi.responses import FileResponse, StreamingResponse

from api.alert_prefs import get_alert_prefs, set_alert_pref

from api.schemas import (
    InstrumentOverview, Stats, AlertItem, AlertsPage,
    InstrumentDetail, InstrumentsUpdate,
    AlertPreferences, AlertPreferencesUpdate,
    VideoEntry, VideoAdd,
    JournalEntry, JournalEntryCreate, JournalEntryUpdate,
)



@contextmanager
def _db(request: Request):
    """Open a fresh read connection per request to avoid thread conflicts."""
    path = request.app.state.config.db_path
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def _db_write(request: Request):
    """Open a fresh write connection per request."""
    path = request.app.state.config.db_path
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


router = APIRouter()
logger = logging.getLogger(__name__)


def _require_owner(request: Request) -> None:
    """Gate platform-control actions to the owner. Mirrors the convention used
    by PUT /config/instruments: when auth is enabled the middleware always sets
    request.state.user, so a subscriber hitting these routes is rejected; before
    any account exists (bootstrap) there is no user and the call is allowed."""
    user = getattr(request.state, "user", None)
    if user and user.get("role") != "OWNER":
        raise HTTPException(status_code=403, detail="Only the platform owner can perform this action.")


CATEGORIES: dict[str, str] = {
    "EUR/USD": "Major", "GBP/USD": "Major", "USD/JPY": "Major",
    "USD/CHF": "Major", "USD/CAD": "Major", "AUD/USD": "Major", "NZD/USD": "Major",
    "EUR/JPY": "EUR Cross", "EUR/GBP": "EUR Cross", "EUR/AUD": "EUR Cross",
    "EUR/CAD": "EUR Cross", "EUR/NZD": "EUR Cross", "EUR/CHF": "EUR Cross",
    "GBP/JPY": "GBP Cross", "GBP/AUD": "GBP Cross", "GBP/CAD": "GBP Cross",
    "GBP/NZD": "GBP Cross", "GBP/CHF": "GBP Cross",
    "AUD/JPY": "Commodity Cross", "AUD/CAD": "Commodity Cross", "AUD/NZD": "Commodity Cross",
    "AUD/CHF": "Commodity Cross", "NZD/JPY": "Commodity Cross", "NZD/CAD": "Commodity Cross",
    "NZD/CHF": "Commodity Cross", "CAD/JPY": "Commodity Cross", "CAD/CHF": "Commodity Cross",
    "CHF/JPY": "Commodity Cross", "XAU/USD": "Metal", "XAG/USD": "Metal",
    "BTC/USD": "Crypto", "ETH/USD": "Crypto", "SOL/USD": "Crypto",
    "BNB/USD": "Crypto", "XRP/USD": "Crypto", "ADA/USD": "Crypto",
    "DOGE/USD": "Crypto", "LTC/USD": "Crypto",
    "WTI/USD": "Energy",
    "US30": "Index", "NAS100": "Index", "SPX500": "Index",
    "UK100": "Index", "GER40": "Index", "JPN225": "Index",
}

CRYPTO = {"BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "ADA/USD", "DOGE/USD", "LTC/USD"}


def is_forex_open() -> bool:
    now = datetime.now(timezone.utc)
    wd, h = now.weekday(), now.hour
    if wd == 5:
        return False
    if wd == 4 and h >= 22:
        return False
    if wd == 6 and h < 22:
        return False
    return True


def _build_overview(conn: sqlite3.Connection, instrument: str) -> InstrumentOverview:
    row = conn.execute(
        """SELECT active_breakout_id, retest_in_progress, last_daily_candle_ts,
                  last_h4_candle_ts, updated_at
           FROM instrument_state WHERE instrument = ?""",
        (instrument,),
    ).fetchone()

    if row is None:
        return InstrumentOverview(
            instrument=instrument, state="IDLE",
            category=CATEGORIES.get(instrument, "Other"),
        )

    active_breakout_id, retest_in_progress, _, _, updated_at = row

    if active_breakout_id is None:
        state = "IDLE"
    elif retest_in_progress:
        state = "RETEST_IN_PROGRESS"
    else:
        state = "BREAKOUT_ACTIVE"

    direction = breakout_level = breakout_ts = None
    if active_breakout_id:
        bk = conn.execute(
            "SELECT direction, broken_level, breakout_ts FROM daily_breakouts WHERE id = ?",
            (active_breakout_id,),
        ).fetchone()
        if bk:
            direction, breakout_level, breakout_ts = bk
            # Normalize to uppercase regardless of how the engine stored it
            if direction:
                direction = direction.upper()

    active_sources_count = 0
    if active_breakout_id:
        src = conn.execute(
            "SELECT COUNT(*) FROM reaction_sources WHERE daily_breakout_id = ? AND is_active = 1",
            (active_breakout_id,),
        ).fetchone()
        active_sources_count = src[0] if src else 0

    last_alert = conn.execute(
        "SELECT fired_at, direction FROM alerts WHERE instrument = ? ORDER BY fired_at DESC LIMIT 1",
        (instrument,),
    ).fetchone()

    last_alert_direction = None
    if last_alert and last_alert[1]:
        last_alert_direction = last_alert[1].upper()

    return InstrumentOverview(
        instrument=instrument,
        state=state,
        direction=direction,
        last_alert_direction=last_alert_direction,
        breakout_level=breakout_level,
        breakout_ts=breakout_ts,
        last_alert_at=last_alert[0] if last_alert else None,
        active_sources_count=active_sources_count,
        last_updated=updated_at,
        category=CATEGORIES.get(instrument, "Other"),
    )


class SignupRequestBody(BaseModel):
    name: str
    email: str
    plan: str
    telegram: str = ""


@router.post("/public/signup-request")
async def signup_request(body: SignupRequestBody, request: Request):
    """Public endpoint — no auth required. Forwards signup interest to the owner via Telegram."""
    from api.auth import client_ip, rate_limited, record_hit
    ip_key = "signup:" + client_ip(request)
    if rate_limited(ip_key, 5, 3600):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    record_hit(ip_key)
    name = body.name.strip()[:100]
    email = body.email.strip()
    plan = body.plan.strip()
    telegram_handle = body.telegram.strip()

    if not name or not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Name and valid email are required.")

    plan_labels = {
        "30DAY": "30 Days — $10",
        "6MONTH": "6 Months — $48",
        "9MONTH": "9 Months — $63",
        "12MONTH": "12 Months — $72",
    }
    plan_str = plan_labels.get(plan, plan)

    msg = (
        f"📩 New sign-up request\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Plan: {plan_str}\n"
        + (f"Telegram: {telegram_handle}\n" if telegram_handle else "")
        + f"\nReply to this email to confirm payment and set up their account."
    )

    config = request.app.state.config
    if config.telegram_enabled and config.telegram_bot_token and config.telegram_chat_id:
        try:
            from alerts.telegram import send_alert
            await send_alert(config.telegram_bot_token, config.telegram_chat_id, msg)
        except Exception:
            pass

    return {"ok": True}


@router.get("/public/track-record")
def public_track_record(request: Request):
    """Public: outcomes of Origin bias calls once they're 5 days old. Cached 10 minutes."""
    import time as _time
    from analysis.track_record import compute_track_record
    cache = getattr(request.app.state, "track_record_cache", None)
    if cache and _time.time() - cache[0] < 600:
        return cache[1]
    with _db(request) as conn:
        data = compute_track_record(conn)
    request.app.state.track_record_cache = (_time.time(), data)
    return data


@router.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@router.get("/chart-board")
def chart_board(request: Request):
    """Live Chart Board: each pair's latest 4H chart snapshot (stage + levels), sent
    by the Bias Pointer with every H4 close. The owner sees every platform pair;
    a subscriber sees only the pairs they receive alerts on (all, if no list saved)."""
    config = request.app.state.config
    pairs = [i.replace("/", "").upper() for i in config.instruments]
    user = getattr(request.state, "user", None)
    with _db(request) as conn:
        if user and user.get("role") != "OWNER":
            row = conn.execute("SELECT watched_instruments FROM users WHERE id = ?", (user.get("id"),)).fetchone()
            if row and row[0]:
                mine = {w.replace("/", "").upper() for w in json.loads(row[0])}
                pairs = [p for p in pairs if p in mine]
        rows = {r["instrument"]: r for r in conn.execute(
            "SELECT instrument, snapshot, price, updated_at FROM chart_snapshots").fetchall()}
    board = []
    for p in pairs:
        r = rows.get(p)
        board.append({
            "instrument": p,
            "snapshot": json.loads(r["snapshot"]) if r else None,
            "price": r["price"] if r else None,
            "updated_at": r["updated_at"] if r else None,
        })
    return {"pairs": board}


@router.get("/overview", response_model=list[InstrumentOverview])
def get_overview(request: Request):
    config = request.app.state.config
    with _db(request) as conn:
        return [_build_overview(conn, inst) for inst in config.instruments]


@router.get("/stats", response_model=Stats)
def get_stats(request: Request):
    config = request.app.state.config
    # Scope all counts to watched instruments only — orphan rows from removed
    # instruments would otherwise inflate retests/breakouts counts vs the
    # instruments page which only iterates config.instruments.
    watched = config.instruments
    if watched:
        placeholders = ",".join("?" * len(watched))
        inst_filter = f"AND instrument IN ({placeholders})"
        inst_params = watched
    else:
        inst_filter = ""
        inst_params = []

    with _db(request) as conn:
        active_breakouts = conn.execute(
            f"SELECT COUNT(*) FROM instrument_state WHERE active_breakout_id IS NOT NULL {inst_filter}",
            inst_params,
        ).fetchone()[0]

        retests = conn.execute(
            f"SELECT COUNT(*) FROM instrument_state WHERE retest_in_progress = 1 {inst_filter}",
            inst_params,
        ).fetchone()[0]

        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        alerts_today = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE fired_at >= ?", (today,)
        ).fetchone()[0]

        total_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    return Stats(
        total_instruments=len(config.instruments),
        active_breakouts=active_breakouts,
        retests_in_progress=retests,
        alerts_today=alerts_today,
        total_alerts=total_alerts,
    )


@router.get("/alerts/instruments")
def get_alert_instruments(request: Request):
    """Distinct pairs that have at least one alert — powers the History pair filter."""
    with _db(request) as conn:
        rows = conn.execute("SELECT DISTINCT instrument FROM alerts ORDER BY instrument").fetchall()
    return {"instruments": [r[0] for r in rows if r[0]]}


@router.get("/alerts", response_model=AlertsPage)
def get_alerts(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    instrument: Optional[str] = None,
    direction: Optional[str] = None,
):
    where, params = [], []
    if instrument:
        where.append("a.instrument = ?")
        params.append(instrument)
    if direction:
        where.append("UPPER(a.direction) = ?")
        params.append(direction.upper())

    w = ("WHERE " + " AND ".join(where)) if where else ""
    with _db(request) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM alerts a {w}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT a.id, a.instrument, a.direction,
                       COALESCE(rs.source_type, 'UNKNOWN'), a.h4_classification,
                       a.alert_classification, a.alert_text, a.fired_at
                FROM alerts a
                LEFT JOIN reaction_sources rs ON rs.id = a.reaction_source_id
                {w}
                ORDER BY a.fired_at DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

    return AlertsPage(
        items=[AlertItem(
            id=r[0], instrument=r[1],
            direction=r[2].upper() if r[2] else r[2],
            source_type=r[3], h4_classification=r[4],
            alert_classification=r[5] or "origin",
            alert_text=r[6], fired_at=r[7],
        ) for r in rows],
        total=total,
    )


async def _bot_username(request: Request) -> Optional[str]:
    """Fetch and cache the bot's @username on app.state."""
    cached = getattr(request.app.state, "bot_username", None)
    if cached:
        return cached
    from alerts.telegram import get_bot_username
    config = request.app.state.config
    username = await get_bot_username(config.telegram_bot_token)
    if username:
        request.app.state.bot_username = username
    return username


@router.get("/telegram/connection")
async def telegram_connection(request: Request):
    """
    Return the logged-in user's Telegram connection status and a one-click
    deep link to connect their own Telegram to the bot.
    """
    uid = _user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    with _db_write(request) as conn:
        row = conn.execute(
            "SELECT telegram_chat_id, telegram_link_token FROM users WHERE id = ?", (uid,)
        ).fetchone()
        chat_id = row["telegram_chat_id"] if row else None
        token = row["telegram_link_token"] if row else None
        if not token:
            import secrets as _secrets
            token = _secrets.token_urlsafe(12)
            conn.execute("UPDATE users SET telegram_link_token = ? WHERE id = ?", (token, uid))

    username = await _bot_username(request)
    link_url = f"https://t.me/{username}?start={token}" if username else None

    return {
        "connected": bool(chat_id),
        "link_url": link_url,
        "bot_username": username,
    }


@router.post("/telegram/disconnect")
def telegram_disconnect(request: Request):
    uid = _user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with _db_write(request) as conn:
        conn.execute("UPDATE users SET telegram_chat_id = NULL WHERE id = ?", (uid,))
    return {"ok": True}


@router.post("/telegram/test")
async def telegram_test(request: Request):
    config = request.app.state.config
    if not config.telegram_enabled:
        return {"ok": False, "detail": "Telegram disabled"}
    uid = _user_id(request)
    with _db(request) as conn:
        row = conn.execute("SELECT telegram_chat_id FROM users WHERE id = ?", (uid,)).fetchone() if uid else None
    chat_id = (row["telegram_chat_id"] if row else None) or None
    if not chat_id:
        return {"ok": False, "detail": "Your Telegram isn't connected yet. Tap Connect Telegram first."}
    try:
        from alerts.telegram import send_alert
        ok = await send_alert(
            config.telegram_bot_token,
            chat_id,
            "✅ MummyTKT's Bias Pointer — test message\n\nYour Telegram is connected. You'll receive your alerts here.",
        )
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


async def _handle_bot_membership(request: Request, config, mcm: dict) -> None:
    """The bot was added to / changed in / removed from a chat. If the OWNER made it an
    admin of a channel (with post + delete rights), that channel becomes the backups
    channel. Anyone else adding the bot to their channel is ignored, so backups can
    never be redirected to a stranger."""
    from alerts.telegram import send_alert
    chat = mcm.get("chat") or {}
    if chat.get("type") != "channel":
        return
    actor = str((mcm.get("from") or {}).get("id", ""))
    new = mcm.get("new_chat_member") or {}
    status = new.get("status")
    chat_id = str(chat.get("id"))
    title = chat.get("title") or "your channel"

    with _db_write(request) as conn:
        row = conn.execute("SELECT telegram_chat_id FROM users WHERE role = 'OWNER' LIMIT 1").fetchone()
        owner_ids = {str(config.telegram_chat_id or ""), str((row[0] if row else "") or "")} - {""}
        current = conn.execute("SELECT value FROM user_config WHERE key = 'backup_channel_id'").fetchone()
        current = current[0] if current else None

        if actor not in owner_ids:
            logger.warning("Ignored bot membership change in channel %s by non-owner %s", chat_id, actor)
            return

        if status == "administrator" and new.get("can_post_messages") and new.get("can_delete_messages"):
            conn.execute("INSERT OR REPLACE INTO user_config (key, value, updated_at) "
                         "VALUES ('backup_channel_id', ?, datetime('now'))", (chat_id,))
            note_owner = (f"✅ Backups channel connected: “{title}”.\n\nFrom tonight, encrypted backups go there, "
                          "and anything older than 30 days is deleted automatically (the newest 7 are always kept).")
            note_channel = "✅ Connected. Daily encrypted backups of MummyTKT's Bias Pointer will appear here."
        elif status == "administrator":
            note_owner = (f"Almost there: in “{title}”, give the bot both “Post messages” and “Delete messages” "
                          "admin permissions, then I'll start using it for backups.")
            note_channel = None
        elif status in ("left", "kicked") and current == chat_id:
            conn.execute("DELETE FROM user_config WHERE key = 'backup_channel_id'")
            note_owner = (f"The bot was removed from “{title}”. Backups will come to this chat again, "
                          "and old ones won't be deleted automatically.")
            note_channel = None
        else:
            return

    if config.telegram_enabled:
        await send_alert(config.telegram_bot_token, config.telegram_chat_id, note_owner)
        if note_channel:
            await send_alert(config.telegram_bot_token, chat_id, note_channel)


@router.post("/telegram/update")
async def telegram_update(request: Request):
    """
    Telegram bot webhook receiver. Handles the /start <token> deep link:
    links the sender's chat_id to the user account that owns the token.
    Public route (no JWT) — verified by the secret_token header Telegram sends.
    """
    config = request.app.state.config

    # Verify Telegram's secret token header (set via setWebhook). Fail closed.
    import hmac as _hmac
    sent = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not config.telegram_webhook_secret or not _hmac.compare_digest(
            sent.encode(), config.telegram_webhook_secret.encode()):
        raise HTTPException(status_code=401, detail="bad secret")

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    if update.get("my_chat_member"):
        await _handle_bot_membership(request, config, update["my_chat_member"])
        return {"ok": True}

    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if not text.startswith("/start") or chat_id is None:
        return {"ok": True}

    parts = text.split(maxsplit=1)
    token = parts[1].strip() if len(parts) > 1 else ""
    if not token:
        from alerts.telegram import send_alert
        await send_alert(config.telegram_bot_token, str(chat_id),
                         "Open the Connect Telegram button in your dashboard to link your account.")
        return {"ok": True}

    with _db_write(request) as conn:
        row = conn.execute(
            "SELECT id, name FROM users WHERE telegram_link_token = ?", (token,)
        ).fetchone()
        if row:
            # One-time link: clear the token so a leaked/old link can't relink
            # this account to someone else's chat. A fresh one is issued on demand.
            conn.execute("UPDATE users SET telegram_chat_id = ?, telegram_link_token = NULL WHERE id = ?",
                         (str(chat_id), row["id"]))

    from alerts.telegram import send_alert
    if row:
        greeting = f", {row['name']}" if row["name"] else ""
        await send_alert(config.telegram_bot_token, str(chat_id),
                         f"✅ Connected{greeting}! You'll now receive your MummyTKT Bias Pointer alerts here.")
    else:
        await send_alert(config.telegram_bot_token, str(chat_id),
                         "That link has expired. Open Connect Telegram in your dashboard again to get a fresh link.")
    return {"ok": True}


@router.get("/onboarding")
def onboarding_status(request: Request):
    """The logged-in user's setup progress for the first-login checklist."""
    uid = _user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with _db(request) as conn:
        u = conn.execute("SELECT telegram_chat_id, watched_instruments FROM users WHERE id = ?", (uid,)).fetchone()
        prefs = conn.execute(
            "SELECT 1 FROM user_config WHERE key IN (?, ?)",
            (f"pref_alert_external:{uid}", f"pref_alert_internal:{uid}")).fetchone()
        videos = conn.execute("SELECT value FROM user_config WHERE key = 'tutorial_videos'").fetchone()
    has_videos = bool(videos and json.loads(videos[0] or "[]"))
    return {
        "telegram_linked": bool(u and (u["telegram_chat_id"] or "").strip()),
        "pairs_chosen": bool(u and u["watched_instruments"]),
        "alerts_reviewed": bool(prefs),
        "has_videos": has_videos,
    }


@router.get("/config/instruments")
def get_config_instruments(request: Request):
    """Return the current monitored instrument list."""
    return {"instruments": request.app.state.config.instruments}


@router.put("/config/instruments")
def update_config_instruments(request: Request, body: InstrumentsUpdate):
    """Update the monitored instrument list. Takes effect on the next scheduler cycle."""
    user = getattr(request.state, "user", None)
    if user and user.get("role") != "OWNER":
        raise HTTPException(status_code=403, detail="Only the platform owner can change the monitored instrument list.")

    instruments = [i.strip().upper() for i in body.instruments if i.strip()]
    if not instruments:
        raise HTTPException(status_code=400, detail="Must specify at least one instrument.")

    # Persist to DB
    with _db_write(request) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('instruments', ?, datetime('now'))",
            (json.dumps(instruments),),
        )

    # Update in-memory config so the NEXT scheduler cycle picks it up immediately
    request.app.state.config.instruments = instruments

    return {"ok": True, "count": len(instruments), "instruments": instruments}


@router.get("/user/instruments")
def get_user_instruments(request: Request):
    """Return this user's personal instrument watch-list."""
    uid = _user_id(request)
    if uid:
        with _db(request) as conn:
            row = conn.execute("SELECT watched_instruments FROM users WHERE id = ?", (uid,)).fetchone()
        if row and row[0]:
            return {"instruments": json.loads(row[0])}
    # No personal list saved yet — return null so the frontend defaults to all pairs selected
    return {"instruments": None}


@router.put("/user/instruments")
def update_user_instruments(request: Request, body: InstrumentsUpdate):
    """Persist this user's personal instrument watch-list."""
    instruments = [i.strip().upper() for i in body.instruments if i.strip()]
    if not instruments:
        raise HTTPException(status_code=400, detail="Must select at least one instrument.")
    uid = _user_id(request)
    if uid:
        with _db_write(request) as conn:
            conn.execute(
                "UPDATE users SET watched_instruments = ? WHERE id = ?",
                (json.dumps(instruments), uid),
            )
    return {"ok": True, "instruments": instruments}


@router.get("/preferences", response_model=AlertPreferences)
def get_preferences(request: Request):
    """Return the logged-in user's own choice of which Origin confirmation
    types (external / internal) reach their Telegram."""
    user = getattr(request.state, "user", None)
    with _db(request) as conn:
        prefs = get_alert_prefs(conn, user["id"] if user else None, user["role"] if user else None)
    return AlertPreferences(alertExternal=prefs["external"], alertInternal=prefs["internal"])


@router.patch("/preferences")
def update_preferences(request: Request, body: AlertPreferencesUpdate):
    """Save the logged-in user's own delivery choices. Affects only their Telegram."""
    user = getattr(request.state, "user", None)
    uid = user["id"] if user else None
    with _db_write(request) as conn:
        if body.alertExternal is not None:
            set_alert_pref(conn, uid, "external", body.alertExternal)
        if body.alertInternal is not None:
            set_alert_pref(conn, uid, "internal", body.alertInternal)
    return {"ok": True}


_ACCENTS = {"indigo", "emerald", "sky", "purple", "amber", "rose", "cyan", "orange"}


@router.get("/preferences/accent")
def get_accent(request: Request):
    """Return this user's own accent colour (each account has its own)."""
    uid = _user_id(request)
    if not uid:
        return {"accent_color": None}
    with _db(request) as conn:
        row = conn.execute("SELECT value FROM user_config WHERE key = ?", (f"accent_color:{uid}",)).fetchone()
    return {"accent_color": row[0] if row else None}


@router.post("/preferences/accent")
def save_accent(request: Request, body: dict):
    """Save this user's accent colour. Body: { accent_color: 'emerald' }"""
    uid = _user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    color = body.get("accent_color", "")
    if color not in _ACCENTS:
        raise HTTPException(status_code=400, detail="Unknown accent colour")
    with _db_write(request) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (f"accent_color:{uid}", color),
        )
    return {"ok": True}


@router.get("/profile")
def get_profile(request: Request):
    config = request.app.state.config
    with _db(request) as conn:
        row = conn.execute("SELECT MIN(updated_at) FROM user_config").fetchone()
        member_since = row[0] if row and row[0] else None

        first_alert = conn.execute("SELECT MIN(fired_at) FROM alerts").fetchone()
        first_alert_at = first_alert[0] if first_alert and first_alert[0] else None

        total_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

    telegram_ok = bool(
        config.telegram_enabled
        and config.telegram_bot_token
        and config.telegram_chat_id
    )
    return {
        "telegram_configured": telegram_ok,
        "member_since": member_since,
        "first_alert_at": first_alert_at,
        "total_alerts": total_alerts,
        "instruments_count": len(config.instruments),
    }


@router.get("/videos", response_model=list[VideoEntry])
def list_videos(request: Request):
    with _db(request) as conn:
        row = conn.execute("SELECT value FROM user_config WHERE key = 'tutorial_videos'").fetchone()
    return json.loads(row[0]) if row else []


@router.post("/videos")
def add_video(request: Request, body: VideoAdd):
    _require_owner(request)
    with _db_write(request) as conn:
        row = conn.execute("SELECT value FROM user_config WHERE key = 'tutorial_videos'").fetchone()
        videos = json.loads(row[0]) if row else []
        videos.append({"title": body.title, "url": body.url})
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('tutorial_videos', ?, datetime('now'))",
            (json.dumps(videos),),
        )
    return {"ok": True}


@router.delete("/videos")
def remove_video(request: Request, url: str = Query(...)):
    _require_owner(request)
    with _db_write(request) as conn:
        row = conn.execute("SELECT value FROM user_config WHERE key = 'tutorial_videos'").fetchone()
        videos = json.loads(row[0]) if row else []
        videos = [v for v in videos if v["url"] != url]
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('tutorial_videos', ?, datetime('now'))",
            (json.dumps(videos),),
        )
    return {"ok": True}


# ── Strategy content (owner-only) ─────────────────────────────────────────────
# The methodology text is served only to the owner so it never ships inside the
# frontend bundle. Subscribers hitting this route get 403 and see no strategy
# cards at all — only the tutorial videos remain on the page for them.

STRATEGY_CONTENT = {
    "chain": [
        {"n": 1, "title": "Daily Breakout", "body": "The Daily chart is read as market structure. A structure's high and low are candle-body levels (like H4; a setting can switch them to wicks) built by fixed rules, and a new structure can form inside the current range at any depth. Only the most recent one counts, shown as the External high and low. A breakout is a Daily candle BODY closing beyond it — no tolerance — and the level it broke becomes the Daily Breaker."},
        {"n": 2, "title": "Reaction Source Identification", "body": "After a breakout, price is watched at three kinds of reaction source: a retest of the Daily Breaker, a Daily V-shape (A-shape for sells) or Daily OC level inside the range that was just broken, and post-breakout Daily OC levels. Only reactions in the breakout direction count."},
        {"n": 3, "title": "Retest Detection", "body": "Price must first move away (an H4 close more than 5 pips beyond the Daily Breaker). Then an H4 wick has to touch a reaction level exactly and hold. A close through the level (beyond a 5-pip allowance) means the reaction failed, and the engine waits for the next one."},
        {"n": 4, "title": "H4 Confirmation", "body": "While a reaction holds, the first H4 candle that closes beyond the latest H4 A-shape (buys) or V-shape (sells) body level confirms Daily + H4 alignment. This is the Origin alert, one per Daily breakout."},
    ],
    "formations": [
        {"term": "A-Shape (Bearish resistance)", "body": "A bullish candle followed by a bearish candle. On the Daily the level is the highest body top of the two (shown as D.A in a bearish bias). On the H4 it is the body high of the bullish candle."},
        {"term": "V-Shape (Bullish support)", "body": "A bearish candle followed by a bullish candle. On the Daily the level is the lowest body bottom of the two (shown as D.V in a bullish bias). On the H4 it is the body low of the bearish candle."},
        {"term": "OC (Open-Close level)", "body": "Formed when 2+ consecutive same-direction candles run. The OC level is the close of the first candle in each consecutive pair (the junction price — not the midpoint). A run of 3 candles produces exactly 2 independent OC levels."},
    ],
    "h4_classification": [
        {"label": "External", "variant": "accent", "desc": "The H4 A-shape (V-shape for sells) that was broken already existed before the reaction started at the Daily level. A failed reaction that restarts at the same level keeps that start; a reaction at a different Daily level starts fresh."},
        {"label": "Internal", "variant": "warning", "desc": "The H4 A-shape (V-shape for sells) that was broken formed after the reaction started. Each subscriber chooses whether they receive External Origins, Internal Origins or both; continuations always come through."},
    ],
    "daily_context": {
        "intro": "The Daily breakout always comes from the most recent External high or low.",
        "items": [
            {"label": "External high / low", "variant": "bullish", "desc": "The most recent structure. Its low is the lowest body bottom before price closed above an A shape (mirror for the high). The side in the move's direction keeps following price (still forming) until price pulls back by closing beyond the last A/V it came from, then it is fixed."},
            {"label": "Structures inside", "variant": "warning", "desc": "While price stays inside the range, a smaller structure can form inside it by the same rules; it then becomes the most recent External high and low. When a structure breaks, every structure inside it is dropped and the one around it counts again."},
        ],
    },
    "alert_classifications": [
        {"term": "Origin", "body": "The first confirmed bias alert for a setup. Requires the complete 4-step chain: Daily breakout → eligible reaction source → retest of that source → qualifying H4 A/V breakout. After an Origin fires, the engine enters continuation mode for that instrument until the next Daily breakout."},
        {"term": "Continuation — H4 breakout in line", "body": "While H4 is in line with the Daily, every new H4 close beyond the latest H4 A-shape (buys) or V-shape (sells) sends an “H4 breakout in line with the Daily” alert. No Daily reaction is needed. Its level becomes the new H4 Breaker and only its leg's H4 OCs (and later ones) are watched."},
        {"term": "Continuation — H4 Breaker Retest", "body": "The H4 A/V broken at the Origin becomes the H4 Breaker; each newer in-line H4 breakout replaces it with the level it broke. When price comes back, the H4 candle must open on the bias side, wick exactly to the level and close beyond it. The first time is the H4 Breaker Origin; each later visit (after price moves away) is an H4 Breaker Continuation."},
        {"term": "Continuation — H4 OC", "body": "Two H4 candles in a row in the Daily direction form an H4 OC. After each H4 breakout in the Daily direction, every OC of that breakout's leg (from its swing low/high) and any formed after it is watched. A later candle that opens on the bias side, wicks exactly to an OC and closes beyond it sends one alert naming the furthest OC reached; those OCs are then used up. An OC closed through against the bias is dropped; all are dropped when H4 breaks the other way or a new Daily breakout forms."},
        {"term": "Out of line → back in line", "body": "An H4 close beyond the latest H4 V (buys) or A (sells) puts H4 out of line with the Daily: no alert, an OUT OF LINE tag on the chart and dashboard, and every H4 OC is dropped. H4 comes back in line only after a fresh Daily reaction followed by an H4 break in the Daily direction, which sends the “H4 back in line with the Daily” continuation."},
    ],
    "reaction_sources": [
        {"term": "Daily Breaker", "body": "The External high or low the Daily close broke. Price often returns to test it from the other side (role reversal)."},
        {"term": "Inside Range", "body": "A Daily V-shape (A-shape for sells) or Daily OC level that sits inside the range that was just broken — between the Daily Breaker and the other side of that range. The H4 wick must reach that exact level and hold. Simply being back inside the range does not count. It fails if a candle closes through that level. A Daily level is dead once a Daily candle has closed through it and never counts again."},
        {"term": "Post-Breakout OC", "body": "Two consecutive Daily candles in the breakout direction after the breakout. The level is where the first one closed. The H4 wick must reach that exact level and hold. It is dead once a Daily candle closes through it."},
    ],
    "disclaimer": "Alerts confirm Daily + H4 alignment. Entry timing, risk management, and position sizing remain your responsibility.",
}


@router.post("/admin/backup")
async def admin_backup(request: Request):
    """Owner-only: take a backup now (local copy + encrypted copy to the owner's Telegram)."""
    _require_owner(request)
    from alerts.backup import run_backup
    config = request.app.state.config
    return await run_backup(config.db_path, config)


@router.get("/admin/feed-health")
def admin_feed_health(request: Request):
    """Owner-only: when TradingView last reported for each instrument."""
    _require_owner(request)
    from alerts.feed_monitor import feed_health
    with _db(request) as conn:
        return {"instruments": feed_health(conn)}


@router.get("/strategy-content")
def strategy_content(request: Request):
    _require_owner(request)
    return STRATEGY_CONTENT


# Owner-only strategy PDFs (built by docs/rulebook/build_*.py). Fixed allowlist: the
# path never comes from the request.
_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "rulebook"
STRATEGY_DOCS = {
    "rulebook": "MummyTKT_Strategy_Rulebook.pdf",
    "storybook": "The_Candle_Twins_Storybook.pdf",
}


@router.get("/strategy-docs/{doc}")
def strategy_doc(doc: str, request: Request):
    _require_owner(request)
    name = STRATEGY_DOCS.get(doc)
    if not name or not (_DOCS_DIR / name).is_file():
        raise HTTPException(status_code=404, detail="Document not found.")
    return FileResponse(_DOCS_DIR / name, media_type="application/pdf", filename=name,
                        headers={"Cache-Control": "no-store"})


# ── Journal ───────────────────────────────────────────────────────────────────

def _journal_period_clause(period: str) -> tuple[str, list]:
    """Return (WHERE clause fragment, params) for the requested period."""
    if period == "today":
        return "WHERE date(trade_date) = date('now')", []
    if period == "week":
        return "WHERE trade_date >= date('now', '-6 days')", []
    if period == "month":
        return "WHERE strftime('%Y-%m', trade_date) = strftime('%Y-%m', 'now')", []
    if period == "year":
        return "WHERE strftime('%Y', trade_date) = strftime('%Y', 'now')", []
    return "", []


def _row_to_entry(row) -> JournalEntry:
    cols = set(row.keys())
    return JournalEntry(
        id=row["id"],
        trade_date=row["trade_date"],
        instrument=row["instrument"],
        direction=row["direction"],
        entry_price=row["entry_price"],
        stop_loss=row["stop_loss"],
        take_profit=row["take_profit"],
        exit_price=row["exit_price"],
        pips=row["pips"],
        rr_ratio=row["rr_ratio"],
        amount_risked=row["amount_risked"] if "amount_risked" in cols else None,
        amount_aimed=row["amount_aimed"] if "amount_aimed" in cols else None,
        result=row["result"],
        setup_type=row["setup_type"],
        setup_type_notes=row["setup_type_notes"] if "setup_type_notes" in cols else None,
        trade_type=row["trade_type"] if "trade_type" in cols else "live",
        h4_break_type=row["h4_break_type"] if "h4_break_type" in cols else None,
        entry_date=row["entry_date"] if "entry_date" in cols else None,
        exit_date=row["exit_date"] if "exit_date" in cols else None,
        trigger_time=row["trigger_time"] if "trigger_time" in cols else None,
        entry_time=row["entry_time"] if "entry_time" in cols else None,
        exit_time=row["exit_time"] if "exit_time" in cols else None,
        session=row["session"],
        notes=row["notes"],
        created_at=row["created_at"],
    )


@router.get("/journal", response_model=list[JournalEntry])
def get_journal(request: Request, period: str = Query("all"), trade_type: str = Query("live")):
    uid = _user_id(request)
    where, params = _journal_period_clause(period)
    user_clause = "user_id = ?" if uid else "1=0"
    if where:
        full_where = f"{where} AND trade_type = ? AND {user_clause}"
    else:
        full_where = f"WHERE trade_type = ? AND {user_clause}"
    query_params = params + [trade_type] + ([uid] if uid else [])
    with _db(request) as conn:
        rows = conn.execute(
            f"SELECT * FROM journal_entries {full_where} ORDER BY trade_date DESC, id DESC",
            query_params,
        ).fetchall()
    return [_row_to_entry(r) for r in rows]


@router.post("/journal", response_model=JournalEntry)
def create_journal_entry(request: Request, body: JournalEntryCreate):
    uid = _user_id(request)
    with _db_write(request) as conn:
        cur = conn.execute(
            """INSERT INTO journal_entries
               (trade_date, instrument, direction, entry_price, stop_loss, take_profit,
                exit_price, pips, rr_ratio, amount_risked, amount_aimed,
                result, setup_type, setup_type_notes, trade_type, h4_break_type,
                entry_date, exit_date, trigger_time, entry_time, exit_time, session, notes,
                user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.trade_date, body.instrument, body.direction,
             body.entry_price, body.stop_loss, body.take_profit,
             body.exit_price, body.pips, body.rr_ratio,
             body.amount_risked, body.amount_aimed,
             body.result, body.setup_type, body.setup_type_notes, body.trade_type,
             body.h4_break_type, body.entry_date, body.exit_date,
             body.trigger_time, body.entry_time, body.exit_time,
             body.session, body.notes, uid),
        )
        entry_id = cur.lastrowid
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_entry(row)


@router.put("/journal/{entry_id}", response_model=JournalEntry)
def update_journal_entry(entry_id: int, request: Request, body: JournalEntryUpdate):
    uid = _user_id(request)
    with _db_write(request) as conn:
        row = conn.execute(
            "SELECT * FROM journal_entries WHERE id = ? AND user_id = ?", (entry_id, uid)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE journal_entries SET {set_clause} WHERE id = ? AND user_id = ?",
                list(updates.values()) + [entry_id, uid],
            )
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_entry(row)


@router.delete("/journal/{entry_id}")
def delete_journal_entry(entry_id: int, request: Request):
    uid = _user_id(request)
    with _db_write(request) as conn:
        conn.execute("DELETE FROM journal_entries WHERE id = ? AND user_id = ?", (entry_id, uid))
    return {"ok": True}


@router.get("/journal/export.csv")
def export_journal_csv(request: Request, period: str = Query("all"), trade_type: str = Query("live")):
    uid = _user_id(request)
    where, params = _journal_period_clause(period)
    user_clause = "user_id = ?" if uid else "1=0"
    if where:
        full_where = f"{where} AND trade_type = ? AND {user_clause}"
    else:
        full_where = f"WHERE trade_type = ? AND {user_clause}"
    query_params = params + [trade_type] + ([uid] if uid else [])
    with _db(request) as conn:
        rows = conn.execute(
            f"SELECT * FROM journal_entries {full_where} ORDER BY trade_date DESC, id DESC",
            query_params,
        ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = set()
    writer.writerow(["Date", "Instrument", "Direction", "Result", "Entry", "SL", "TP",
                     "Exit", "Pips", "R:R", "Amount Risked", "Amount Aimed",
                     "Setup", "H4 Break Type", "Entry Date", "Entry Time",
                     "Exit Date", "Exit Time", "Trigger Time", "Session", "Notes"])
    for r in rows:
        if not cols:
            cols = set(r.keys())
        writer.writerow([
            r["trade_date"], r["instrument"], r["direction"].upper(), r["result"].upper(),
            r["entry_price"] or "", r["stop_loss"] or "", r["take_profit"] or "",
            r["exit_price"] or "", r["pips"] or "", r["rr_ratio"] or "",
            (r["amount_risked"] if "amount_risked" in cols else "") or "",
            (r["amount_aimed"] if "amount_aimed" in cols else "") or "",
            r["setup_type"],
            (r["h4_break_type"] if "h4_break_type" in cols else "") or "",
            (r["entry_date"] if "entry_date" in cols else "") or "",
            (r["entry_time"] if "entry_time" in cols else "") or "",
            (r["exit_date"] if "exit_date" in cols else "") or "",
            (r["exit_time"] if "exit_time" in cols else "") or "",
            (r["trigger_time"] if "trigger_time" in cols else "") or "",
            r["session"] or "", (r["notes"] or "").replace("\n", " "),
        ])

    buf.seek(0)
    filename = f"journal-{period}-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/admin/reset-instrument")
def admin_reset_instrument(request: Request, body: dict):
    """
    Fully reset the state for one or more instruments.

    Body: {"instruments": ["GBPUSD", "EURJPY"]}  — use internal names (no slash).

    Deactivates the active daily breakout + all its reaction sources, then
    clears all instrument_state columns for each pair. The engine will
    re-detect from the current daily candle history on the next H4 cycle.
    Useful for correcting wrong-direction state caused by spurious supersessions.
    """
    _require_owner(request)
    raw = body.get("instruments", [])
    if not raw:
        raise HTTPException(status_code=400, detail="'instruments' list required")

    # Normalise to the DB format (EUR/USD with slash).
    # Accept both "EURUSD" and "EUR/USD" — insert slash at position 3 when missing.
    targets = []
    for s in raw:
        s = s.upper().replace("-", "/")
        if "/" not in s and len(s) >= 6:
            s = s[:3] + "/" + s[3:]
        targets.append(s)

    with _db_write(request) as conn:
        for inst in targets:
            # Deactivate all active breakouts for this instrument
            conn.execute(
                "UPDATE daily_breakouts SET is_active = 0 WHERE instrument = ? AND is_active = 1",
                (inst,),
            )
            # Deactivate all reaction sources for this instrument
            conn.execute(
                "UPDATE reaction_sources SET is_active = 0 WHERE instrument = ? AND is_active = 1",
                (inst,),
            )
            # Reset all instrument state
            conn.execute(
                """UPDATE instrument_state
                   SET active_breakout_id       = NULL,
                       retest_in_progress       = 0,
                       active_reaction_src_id   = NULL,
                       retest_started_h4_ts     = NULL,
                       continuation_mode        = 0,
                       last_alert_h4_ts         = NULL,
                       last_h4_breaker_level    = NULL,
                       external_level           = NULL,
                       external_level_direction = NULL
                   WHERE instrument = ?""",
                (inst,),
            )

    return {"ok": True, "reset": targets}


@router.get("/instrument/{slug}", response_model=InstrumentDetail)
def get_instrument(slug: str, request: Request):
    config = request.app.state.config
    instrument = slug.replace("-", "/").upper()
    if instrument not in config.instruments:
        raise HTTPException(status_code=404, detail="Instrument not found")

    with _db(request) as conn:
        overview = _build_overview(conn, instrument)

        active_sources: list[dict] = []
        row = conn.execute(
            "SELECT active_breakout_id FROM instrument_state WHERE instrument = ?", (instrument,)
        ).fetchone()
        if row and row[0]:
            srcs = conn.execute(
                """SELECT source_type, direction, level, level_band_low, level_band_high, created_at
                   FROM reaction_sources WHERE daily_breakout_id = ? AND is_active = 1""",
                (row[0],),
            ).fetchall()
            active_sources = [
                {"source_type": s[0], "direction": s[1].upper() if s[1] else s[1],
                 "level": s[2], "band_low": s[3], "band_high": s[4], "created_at": s[5]}
                for s in srcs
            ]

        rows = conn.execute(
            """SELECT a.id, a.instrument, a.direction,
                      COALESCE(rs.source_type, 'UNKNOWN'), a.h4_classification,
                      a.alert_text, a.fired_at
               FROM alerts a
               LEFT JOIN reaction_sources rs ON rs.id = a.reaction_source_id
               WHERE a.instrument = ?
               ORDER BY a.fired_at DESC LIMIT 10""",
            (instrument,),
        ).fetchall()
        recent_alerts = [
            AlertItem(
                id=r[0], instrument=r[1],
                direction=r[2].upper() if r[2] else r[2],
                source_type=r[3], h4_classification=r[4],
                alert_text=r[5], fired_at=r[6],
            )
            for r in rows
        ]

    return InstrumentDetail(overview=overview, active_sources=active_sources, recent_alerts=recent_alerts)


# ── Price Alerts ──────────────────────────────────────────────────────────────

_MAX_ACTIVE_PRICE_ALERTS = 20


class PriceAlertItem(BaseModel):
    id: int
    instrument: str
    trigger_type: str
    timeframe: str
    condition: str
    price: float
    message: Optional[str]
    expires_at: Optional[str]
    is_active: bool
    triggered_at: Optional[str]
    created_at: str


class PriceAlertsList(BaseModel):
    items: list[PriceAlertItem]
    active_count: int
    max_alerts: int


class PriceAlertCreate(BaseModel):
    instrument: str
    trigger_type: str = "on_touch"
    timeframe: str = "5m"
    condition: str = "crossing"
    price: float
    message: Optional[str] = None
    expires_at: Optional[str] = None


def _user_id(request: Request) -> Optional[int]:
    user = getattr(request.state, "user", None)
    return user["id"] if user else None


def _row_to_price_alert(row: sqlite3.Row) -> PriceAlertItem:
    d = dict(row)
    return PriceAlertItem(
        id=d["id"],
        instrument=d["instrument"],
        trigger_type=d["trigger_type"],
        timeframe=d.get("timeframe", "5m"),
        condition=d["condition"],
        price=d["price"],
        message=d.get("message"),
        expires_at=d.get("expires_at"),
        is_active=bool(d["is_active"]),
        triggered_at=d.get("triggered_at"),
        created_at=d["created_at"],
    )


@router.get("/price-alerts", response_model=PriceAlertsList)
def list_price_alerts(request: Request, tab: str = Query("active")):
    uid = _user_id(request)
    active_filter = "is_active = 1" if tab != "history" else "is_active = 0"
    with _db(request) as conn:
        if uid:
            rows = conn.execute(
                f"SELECT * FROM price_alerts WHERE user_id = ? AND {active_filter} ORDER BY created_at DESC",
                (uid,),
            ).fetchall()
            active_count = conn.execute(
                "SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1", (uid,)
            ).fetchone()[0]
        else:
            rows = conn.execute(
                f"SELECT * FROM price_alerts WHERE user_id IS NULL AND {active_filter} ORDER BY created_at DESC"
            ).fetchall()
            active_count = conn.execute(
                "SELECT COUNT(*) FROM price_alerts WHERE user_id IS NULL AND is_active = 1"
            ).fetchone()[0]
    return PriceAlertsList(
        items=[_row_to_price_alert(r) for r in rows],
        active_count=active_count,
        max_alerts=_MAX_ACTIVE_PRICE_ALERTS,
    )


@router.get("/price-alerts/prices")
def get_instrument_prices(request: Request):
    with _db(request) as conn:
        rows = conn.execute(
            "SELECT instrument, price, updated_at FROM instrument_prices"
        ).fetchall()
    return {r["instrument"]: {"price": r["price"], "updated_at": r["updated_at"]} for r in rows}


@router.post("/price-alerts", response_model=PriceAlertItem)
def create_price_alert(body: PriceAlertCreate, request: Request):
    uid = _user_id(request)
    instrument = body.instrument.replace("/", "").upper()
    with _db_write(request) as conn:
        if uid:
            count = conn.execute(
                "SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1", (uid,)
            ).fetchone()[0]
        else:
            count = conn.execute(
                "SELECT COUNT(*) FROM price_alerts WHERE user_id IS NULL AND is_active = 1"
            ).fetchone()[0]
        if count >= _MAX_ACTIVE_PRICE_ALERTS:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {_MAX_ACTIVE_PRICE_ALERTS} active price alerts reached.",
            )
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute("""
            INSERT INTO price_alerts (user_id, instrument, trigger_type, timeframe, condition, price, message, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, instrument, body.trigger_type, body.timeframe, body.condition, body.price, body.message, body.expires_at, now))
        row = conn.execute("SELECT * FROM price_alerts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_price_alert(row)


@router.delete("/price-alerts/{alert_id}")
def delete_price_alert(alert_id: int, request: Request):
    uid = _user_id(request)
    with _db_write(request) as conn:
        if uid:
            conn.execute("DELETE FROM price_alerts WHERE id = ? AND user_id = ?", (alert_id, uid))
        else:
            conn.execute("DELETE FROM price_alerts WHERE id = ? AND user_id IS NULL", (alert_id,))
    return {"ok": True}


# ── Entry Pattern Alerts (PCL + Engulfing Sweep at user-set levels) ──────────

_MAX_ACTIVE_ENTRY_ALERTS = 20


class EntryAlertItem(BaseModel):
    id: int
    instrument: str
    direction: str          # 'bullish' | 'bearish'
    price: float
    tolerance_pips: float
    note: Optional[str]
    expires_at: Optional[str]
    is_active: bool
    triggered_at: Optional[str]
    triggered_pattern: Optional[str]
    triggered_tf: Optional[str]
    created_at: str


class EntryAlertsList(BaseModel):
    items: list[EntryAlertItem]
    active_count: int
    max_alerts: int


class EntryAlertCreate(BaseModel):
    instrument: str
    direction: str          # 'bullish' | 'bearish'
    price: float
    tolerance_pips: float = 20
    note: Optional[str] = None
    expires_at: Optional[str] = None


def _row_to_entry_alert(row: sqlite3.Row) -> EntryAlertItem:
    d = dict(row)
    return EntryAlertItem(
        id=d["id"],
        instrument=d["instrument"],
        direction=d["direction"],
        price=d["price"],
        tolerance_pips=d["tolerance_pips"],
        note=d.get("note"),
        expires_at=d.get("expires_at"),
        is_active=bool(d["is_active"]),
        triggered_at=d.get("triggered_at"),
        triggered_pattern=d.get("triggered_pattern"),
        triggered_tf=d.get("triggered_tf"),
        created_at=d["created_at"],
    )


@router.get("/entry-alerts", response_model=EntryAlertsList)
def list_entry_alerts(request: Request, tab: str = Query("active")):
    uid = _user_id(request)
    active_filter = "is_active = 1" if tab != "history" else "is_active = 0"
    with _db(request) as conn:
        if uid:
            rows = conn.execute(
                f"SELECT * FROM entry_pattern_alerts WHERE user_id = ? AND {active_filter} ORDER BY created_at DESC",
                (uid,),
            ).fetchall()
            active_count = conn.execute(
                "SELECT COUNT(*) FROM entry_pattern_alerts WHERE user_id = ? AND is_active = 1", (uid,)
            ).fetchone()[0]
        else:
            rows = conn.execute(
                f"SELECT * FROM entry_pattern_alerts WHERE user_id IS NULL AND {active_filter} ORDER BY created_at DESC"
            ).fetchall()
            active_count = conn.execute(
                "SELECT COUNT(*) FROM entry_pattern_alerts WHERE user_id IS NULL AND is_active = 1"
            ).fetchone()[0]
    return EntryAlertsList(
        items=[_row_to_entry_alert(r) for r in rows],
        active_count=active_count,
        max_alerts=_MAX_ACTIVE_ENTRY_ALERTS,
    )


@router.post("/entry-alerts", response_model=EntryAlertItem)
def create_entry_alert(body: EntryAlertCreate, request: Request):
    uid = _user_id(request)
    instrument = body.instrument.replace("/", "").upper()
    direction = body.direction.lower()
    if direction not in ("bullish", "bearish"):
        raise HTTPException(status_code=400, detail="direction must be 'bullish' or 'bearish'")
    if body.tolerance_pips <= 0:
        raise HTTPException(status_code=400, detail="tolerance_pips must be > 0")
    with _db_write(request) as conn:
        if uid:
            count = conn.execute(
                "SELECT COUNT(*) FROM entry_pattern_alerts WHERE user_id = ? AND is_active = 1", (uid,)
            ).fetchone()[0]
        else:
            count = conn.execute(
                "SELECT COUNT(*) FROM entry_pattern_alerts WHERE user_id IS NULL AND is_active = 1"
            ).fetchone()[0]
        if count >= _MAX_ACTIVE_ENTRY_ALERTS:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {_MAX_ACTIVE_ENTRY_ALERTS} active entry pattern alerts reached.",
            )
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute("""
            INSERT INTO entry_pattern_alerts
                (user_id, instrument, direction, price, tolerance_pips, note, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, instrument, direction, body.price, body.tolerance_pips, body.note, body.expires_at, now))
        row = conn.execute("SELECT * FROM entry_pattern_alerts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_entry_alert(row)


@router.delete("/entry-alerts/{alert_id}")
def delete_entry_alert(alert_id: int, request: Request):
    uid = _user_id(request)
    with _db_write(request) as conn:
        if uid:
            conn.execute("DELETE FROM entry_pattern_alerts WHERE id = ? AND user_id = ?", (alert_id, uid))
        else:
            conn.execute("DELETE FROM entry_pattern_alerts WHERE id = ? AND user_id IS NULL", (alert_id,))
    return {"ok": True}
