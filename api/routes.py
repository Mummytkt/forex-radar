from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query

from api.schemas import InstrumentOverview, Stats, AlertItem, AlertsPage, InstrumentDetail

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

    active_sources_count = 0
    if active_breakout_id:
        src = conn.execute(
            "SELECT COUNT(*) FROM reaction_sources WHERE daily_breakout_id = ? AND is_active = 1",
            (active_breakout_id,),
        ).fetchone()
        active_sources_count = src[0] if src else 0

    last_alert = conn.execute(
        "SELECT fired_at FROM alerts WHERE instrument = ? ORDER BY fired_at DESC LIMIT 1",
        (instrument,),
    ).fetchone()

    return InstrumentOverview(
        instrument=instrument,
        state=state,
        direction=direction,
        breakout_level=breakout_level,
        breakout_ts=breakout_ts,
        last_alert_at=last_alert[0] if last_alert else None,
        active_sources_count=active_sources_count,
        last_updated=updated_at,
        category=CATEGORIES.get(instrument, "Other"),
    )


@router.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@router.get("/overview", response_model=list[InstrumentOverview])
def get_overview(request: Request):
    conn: sqlite3.Connection = request.app.state.conn
    config = request.app.state.config
    return [_build_overview(conn, inst) for inst in config.instruments]


@router.get("/stats", response_model=Stats)
def get_stats(request: Request):
    conn: sqlite3.Connection = request.app.state.conn
    config = request.app.state.config

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
    conn: sqlite3.Connection = request.app.state.conn
    where, params = [], []
    if instrument:
        where.append("a.instrument = ?")
        params.append(instrument)
    if direction:
        where.append("a.direction = ?")
        params.append(direction.upper())

    w = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM alerts a {w}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT a.id, a.instrument, a.direction,
                   COALESCE(rs.source_type, 'UNKNOWN'), a.h4_classification,
                   a.alert_text, a.fired_at
            FROM alerts a
            LEFT JOIN reaction_sources rs ON rs.id = a.reaction_source_id
            {w}
            ORDER BY a.fired_at DESC LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()

    return AlertsPage(
        items=[AlertItem(id=r[0], instrument=r[1], direction=r[2], source_type=r[3],
                         h4_classification=r[4], alert_text=r[5], fired_at=r[6])
               for r in rows],
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


@router.get("/instrument/{slug}", response_model=InstrumentDetail)
def get_instrument(slug: str, request: Request):
    conn: sqlite3.Connection = request.app.state.conn
    config = request.app.state.config
    instrument = slug.replace("-", "/").upper()
    if instrument not in config.instruments:
        raise HTTPException(status_code=404, detail="Instrument not found")

    overview = _build_overview(conn, instrument)

    # Active sources
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
            {"source_type": s[0], "direction": s[1], "level": s[2],
             "band_low": s[3], "band_high": s[4], "created_at": s[5]}
            for s in srcs
        ]

    # Recent alerts
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
        AlertItem(id=r[0], instrument=r[1], direction=r[2], source_type=r[3],
                  h4_classification=r[4], alert_text=r[5], fired_at=r[6])
        for r in rows
    ]

    return InstrumentDetail(overview=overview, active_sources=active_sources, recent_alerts=recent_alerts)
