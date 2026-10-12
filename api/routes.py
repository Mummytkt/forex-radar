from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

import csv
import io

from fastapi.responses import StreamingResponse

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
    "CHF/JPY": "Commodity Cross", "XAU/USD": "Metal",
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
    name = body.name.strip()
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


@router.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@router.get("/overview", response_model=list[InstrumentOverview])
def get_overview(request: Request):
    config = request.app.state.config
    with _db(request) as conn:
        return [_build_overview(conn, inst) for inst in config.instruments]


@router.get("/stats", response_model=Stats)
def get_stats(request: Request):
    config = request.app.state.config
    with _db(request) as conn:
        active_breakouts = conn.execute(
            "SELECT COUNT(*) FROM instrument_state WHERE active_breakout_id IS NOT NULL"
        ).fetchone()[0]

        retests = conn.execute(
            "SELECT COUNT(*) FROM instrument_state WHERE retest_in_progress = 1"
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


@router.post("/telegram/test")
async def telegram_test(request: Request):
    config = request.app.state.config
    if not config.telegram_enabled:
        return {"ok": False, "detail": "Telegram disabled"}
    try:
        from alerts.telegram import send_alert
        ok = await send_alert(
            config.telegram_bot_token,
            config.telegram_chat_id,
            "✅ <b>Bias Radar — test message</b>\n\nYour Telegram alerts are working correctly.",
        )
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@router.get("/config/instruments")
def get_config_instruments(request: Request):
    """Return the current monitored instrument list."""
    return {"instruments": request.app.state.config.instruments}


@router.put("/config/instruments")
def update_config_instruments(request: Request, body: InstrumentsUpdate):
    """Update the monitored instrument list. Takes effect on the next scheduler cycle."""
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


@router.get("/preferences", response_model=AlertPreferences)
def get_preferences(request: Request):
    """Return the owner's alert-type delivery preferences."""
    with _db(request) as conn:
        ext = conn.execute("SELECT value FROM user_config WHERE key = 'pref_alert_external'").fetchone()
        int_ = conn.execute("SELECT value FROM user_config WHERE key = 'pref_alert_internal'").fetchone()
    return AlertPreferences(
        alertExternal=(ext[0] if ext else "1") == "1",
        alertInternal=(int_[0] if int_ else "0") == "1",
    )


@router.patch("/preferences")
def update_preferences(request: Request, body: AlertPreferencesUpdate):
    """Persist alert-type delivery preferences (controls what Telegram receives)."""
    with _db_write(request) as conn:
        if body.alertExternal is not None:
            conn.execute(
                "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('pref_alert_external', ?, datetime('now'))",
                ("1" if body.alertExternal else "0",),
            )
        if body.alertInternal is not None:
            conn.execute(
                "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('pref_alert_internal', ?, datetime('now'))",
                ("1" if body.alertInternal else "0",),
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
    with _db_write(request) as conn:
        row = conn.execute("SELECT value FROM user_config WHERE key = 'tutorial_videos'").fetchone()
        videos = json.loads(row[0]) if row else []
        videos = [v for v in videos if v["url"] != url]
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('tutorial_videos', ?, datetime('now'))",
            (json.dumps(videos),),
        )
    return {"ok": True}


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
def get_journal(request: Request, period: str = Query("all")):
    where, params = _journal_period_clause(period)
    with _db(request) as conn:
        rows = conn.execute(
            f"SELECT * FROM journal_entries {where} ORDER BY trade_date DESC, id DESC",
            params,
        ).fetchall()
    return [_row_to_entry(r) for r in rows]


@router.post("/journal", response_model=JournalEntry)
def create_journal_entry(request: Request, body: JournalEntryCreate):
    with _db_write(request) as conn:
        cur = conn.execute(
            """INSERT INTO journal_entries
               (trade_date, instrument, direction, entry_price, stop_loss, take_profit,
                exit_price, pips, rr_ratio, amount_risked, amount_aimed,
                result, setup_type, h4_break_type, entry_date, exit_date,
               trigger_time, entry_time, exit_time, session, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.trade_date, body.instrument, body.direction,
             body.entry_price, body.stop_loss, body.take_profit,
             body.exit_price, body.pips, body.rr_ratio,
             body.amount_risked, body.amount_aimed,
             body.result, body.setup_type, body.h4_break_type,
             body.entry_date, body.exit_date,
             body.trigger_time, body.entry_time, body.exit_time,
             body.session, body.notes),
        )
        entry_id = cur.lastrowid
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_entry(row)


@router.put("/journal/{entry_id}", response_model=JournalEntry)
def update_journal_entry(entry_id: int, request: Request, body: JournalEntryUpdate):
    with _db_write(request) as conn:
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE journal_entries SET {set_clause} WHERE id = ?",
                list(updates.values()) + [entry_id],
            )
        row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_entry(row)


@router.delete("/journal/{entry_id}")
def delete_journal_entry(entry_id: int, request: Request):
    with _db_write(request) as conn:
        conn.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    return {"ok": True}


@router.get("/journal/export.csv")
def export_journal_csv(request: Request, period: str = Query("all")):
    where, params = _journal_period_clause(period)
    with _db(request) as conn:
        rows = conn.execute(
            f"SELECT * FROM journal_entries {where} ORDER BY trade_date DESC, id DESC",
            params,
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
                   SET active_breakout_id     = NULL,
                       retest_in_progress     = 0,
                       active_reaction_src_id = NULL,
                       retest_started_h4_ts   = NULL,
                       continuation_mode      = 0,
                       last_alert_h4_ts       = NULL,
                       last_h4_breaker_level  = NULL
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
