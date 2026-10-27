"""
All database read/write operations.

Every function accepts a sqlite3.Connection. No global state.
Datetimes are serialised as ISO 8601 UTC strings and deserialised back to
naive datetime objects (all UTC by convention).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from data.models import (
    AlertClassification,
    AlertRecord,
    BreakoutClassification,
    Candle,
    DailyBreakout,
    Direction,
    Formation,
    FormationType,
    H4BreakoutEvent,
    ReactionSource,
    ReactionSourceType,
    Timeframe,
)


# ── Datetime helpers ──────────────────────────────────────────────────────────

def _dt_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _str_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


# ── Instrument state ──────────────────────────────────────────────────────────

@dataclass
class InstrumentStateRow:
    instrument: str
    last_daily_candle_ts: Optional[datetime]
    last_h4_candle_ts: Optional[datetime]
    active_breakout_id: Optional[int]
    retest_in_progress: bool
    active_reaction_src_id: Optional[int]
    updated_at: datetime
    continuation_mode: bool = False
    last_alert_h4_ts: Optional[datetime] = None
    last_h4_breaker_level: Optional[float] = None
    retest_started_h4_ts: Optional[datetime] = None
    external_level: Optional[float] = None
    external_level_direction: Optional[str] = None  # 'bearish' or 'bullish'


def get_instrument_state(conn: sqlite3.Connection, instrument: str) -> Optional[InstrumentStateRow]:
    row = conn.execute(
        "SELECT * FROM instrument_state WHERE instrument = ?", (instrument,)
    ).fetchone()
    if row is None:
        return None
    keys = row.keys()
    return InstrumentStateRow(
        instrument=row["instrument"],
        last_daily_candle_ts=_str_dt(row["last_daily_candle_ts"]) if row["last_daily_candle_ts"] else None,
        last_h4_candle_ts=_str_dt(row["last_h4_candle_ts"]) if row["last_h4_candle_ts"] else None,
        active_breakout_id=row["active_breakout_id"],
        retest_in_progress=bool(row["retest_in_progress"]),
        active_reaction_src_id=row["active_reaction_src_id"],
        updated_at=_str_dt(row["updated_at"]),
        continuation_mode=bool(row["continuation_mode"]) if "continuation_mode" in keys else False,
        last_alert_h4_ts=_str_dt(row["last_alert_h4_ts"]) if ("last_alert_h4_ts" in keys and row["last_alert_h4_ts"]) else None,
        last_h4_breaker_level=float(row["last_h4_breaker_level"]) if ("last_h4_breaker_level" in keys and row["last_h4_breaker_level"] is not None) else None,
        retest_started_h4_ts=_str_dt(row["retest_started_h4_ts"]) if ("retest_started_h4_ts" in keys and row["retest_started_h4_ts"]) else None,
        external_level=float(row["external_level"]) if ("external_level" in keys and row["external_level"] is not None) else None,
        external_level_direction=row["external_level_direction"] if ("external_level_direction" in keys and row["external_level_direction"]) else None,
    )


def upsert_instrument_state(conn: sqlite3.Connection, state: InstrumentStateRow) -> None:
    conn.execute(
        """
        INSERT INTO instrument_state
            (instrument, last_daily_candle_ts, last_h4_candle_ts,
             active_breakout_id, retest_in_progress, active_reaction_src_id,
             continuation_mode, last_alert_h4_ts, last_h4_breaker_level,
             retest_started_h4_ts, external_level, external_level_direction,
             updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument) DO UPDATE SET
            last_daily_candle_ts      = excluded.last_daily_candle_ts,
            last_h4_candle_ts         = excluded.last_h4_candle_ts,
            active_breakout_id        = excluded.active_breakout_id,
            retest_in_progress        = excluded.retest_in_progress,
            active_reaction_src_id    = excluded.active_reaction_src_id,
            continuation_mode         = excluded.continuation_mode,
            last_alert_h4_ts          = excluded.last_alert_h4_ts,
            last_h4_breaker_level     = excluded.last_h4_breaker_level,
            retest_started_h4_ts      = excluded.retest_started_h4_ts,
            external_level            = excluded.external_level,
            external_level_direction  = excluded.external_level_direction,
            updated_at                = excluded.updated_at
        """,
        (
            state.instrument,
            _dt_str(state.last_daily_candle_ts) if state.last_daily_candle_ts else None,
            _dt_str(state.last_h4_candle_ts) if state.last_h4_candle_ts else None,
            state.active_breakout_id,
            int(state.retest_in_progress),
            state.active_reaction_src_id,
            int(state.continuation_mode),
            _dt_str(state.last_alert_h4_ts) if state.last_alert_h4_ts else None,
            state.last_h4_breaker_level,
            _dt_str(state.retest_started_h4_ts) if state.retest_started_h4_ts else None,
            state.external_level,
            state.external_level_direction,
            _dt_str(state.updated_at),
        ),
    )
    conn.commit()


# ── Daily breakouts ───────────────────────────────────────────────────────────

def get_active_breakout(conn: sqlite3.Connection, instrument: str) -> Optional[DailyBreakout]:
    row = conn.execute(
        "SELECT * FROM daily_breakouts WHERE instrument = ? AND is_active = 1",
        (instrument,),
    ).fetchone()
    if row is None:
        return None
    b = DailyBreakout(
        instrument=row["instrument"],
        direction=Direction(row["direction"]),
        broken_level=row["broken_level"],
        broken_type=FormationType(row["broken_type"]),
        breakout_ts=_str_dt(row["breakout_ts"]),
        is_active=bool(row["is_active"]),
    )
    b.db_id = row["id"]
    return b


def insert_breakout(conn: sqlite3.Connection, breakout: DailyBreakout) -> int:
    cur = conn.execute(
        """
        INSERT INTO daily_breakouts (instrument, direction, broken_level, broken_type, breakout_ts)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            breakout.instrument,
            breakout.direction.value,
            breakout.broken_level,
            breakout.broken_type.value,
            _dt_str(breakout.breakout_ts),
        ),
    )
    conn.commit()
    return cur.lastrowid


def deactivate_breakout(conn: sqlite3.Connection, breakout_id: int) -> None:
    conn.execute(
        "UPDATE daily_breakouts SET is_active = 0 WHERE id = ?", (breakout_id,)
    )
    conn.commit()


def deactivate_all_breakouts(conn: sqlite3.Connection, instrument: str) -> None:
    conn.execute(
        "UPDATE daily_breakouts SET is_active = 0 WHERE instrument = ?", (instrument,)
    )
    conn.commit()


# ── Reaction sources ──────────────────────────────────────────────────────────

def get_active_reaction_sources(
    conn: sqlite3.Connection, instrument: str
) -> list[ReactionSource]:
    rows = conn.execute(
        """
        SELECT rs.*, db.breakout_ts
        FROM reaction_sources rs
        JOIN daily_breakouts db ON rs.daily_breakout_id = db.id
        WHERE rs.instrument = ? AND rs.is_active = 1
        """,
        (instrument,),
    ).fetchall()
    results = []
    for row in rows:
        src = ReactionSource(
            instrument=row["instrument"],
            source_type=ReactionSourceType(row["source_type"]),
            direction=Direction(row["direction"]),
            level=row["level"],
            level_band_low=row["level_band_low"],
            level_band_high=row["level_band_high"],
            daily_breakout_ts=_str_dt(row["breakout_ts"]),
            is_active=bool(row["is_active"]),
        )
        src.db_id = row["id"]
        results.append(src)
    return results


def insert_reaction_sources(
    conn: sqlite3.Connection,
    sources: list[ReactionSource],
    daily_breakout_id: int,
) -> list[int]:
    ids = []
    for src in sources:
        cur = conn.execute(
            """
            INSERT INTO reaction_sources
                (instrument, source_type, direction, level,
                 level_band_low, level_band_high, daily_breakout_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                src.instrument,
                src.source_type.value,
                src.direction.value,
                src.level,
                src.level_band_low,
                src.level_band_high,
                daily_breakout_id,
            ),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    return ids


def deactivate_reaction_sources_for_breakout(
    conn: sqlite3.Connection, breakout_id: int
) -> None:
    conn.execute(
        "UPDATE reaction_sources SET is_active = 0 WHERE daily_breakout_id = ?",
        (breakout_id,),
    )
    conn.commit()


def deactivate_reaction_source(conn: sqlite3.Connection, source_id: int) -> None:
    conn.execute(
        "UPDATE reaction_sources SET is_active = 0 WHERE id = ?", (source_id,)
    )
    conn.commit()


# ── Formations ────────────────────────────────────────────────────────────────

def insert_formation(conn: sqlite3.Connection, formation: Formation) -> int:
    cur = conn.execute(
        """
        INSERT INTO formations
            (instrument, timeframe, formation_type, direction, level,
             established_at, candle_1_ts, candle_2_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            formation.instrument,
            formation.timeframe.value,
            formation.formation_type.value,
            formation.direction.value,
            formation.level,
            _dt_str(formation.established_at),
            _dt_str(formation.candle_1_ts),
            _dt_str(formation.candle_2_ts),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_formation_by_id(conn: sqlite3.Connection, formation_id: int) -> Optional[Formation]:
    row = conn.execute(
        "SELECT * FROM formations WHERE id = ?", (formation_id,)
    ).fetchone()
    if row is None:
        return None
    f = Formation(
        instrument=row["instrument"],
        timeframe=Timeframe(row["timeframe"]),
        formation_type=FormationType(row["formation_type"]),
        direction=Direction(row["direction"]),
        level=row["level"],
        established_at=_str_dt(row["established_at"]),
        candle_1_ts=_str_dt(row["candle_1_ts"]),
        candle_2_ts=_str_dt(row["candle_2_ts"]),
        is_active=bool(row["is_active"]),
    )
    f.db_id = row["id"]
    return f


# ── Alerts ────────────────────────────────────────────────────────────────────

# Alert type for the notification-list filter, from the stored classification
# (and, for H4 breakouts, the title in the alert text). Used for old rows too.
_CLASS_TO_TYPE = {"origin": "origin", "h4_breaker_origin": "breaker", "h4_breaker_cont": "breaker",
                  "continuation_h4breaker": "breaker", "h4_oc_cont": "oc", "continuation_h4oc": "oc",
                  "h4_engulfing_cont": "engulfing", "h4_fvg": "h4_fvg", "d_engulfing": "d_engulfing"}


def alert_type_for(classification: Optional[str], alert_text: Optional[str]) -> str:
    if classification in _CLASS_TO_TYPE:
        return _CLASS_TO_TYPE[classification]
    text = alert_text or ""
    if "Daily reaction + H4 breakout" in text:
        return "daily_react"
    if "back in line" in text:
        return "realign"
    return "inline"


def insert_alert(
    conn: sqlite3.Connection,
    alert: AlertRecord,
    daily_breakout_id: int,
    reaction_source_id: Optional[int],
    h4_formation_id: Optional[int],
    alert_text: str,
) -> int:
    # h4_classification: use formation classification for A/V breaks, else label the type
    if alert.h4_event is not None:
        h4_cls = alert.h4_event.classification.value
    elif alert.classification == AlertClassification.CONTINUATION_H4_OC:
        h4_cls = "oc_reaction"
    elif alert.classification == AlertClassification.CONTINUATION_H4_BREAKER:
        h4_cls = "breaker_retest"
    else:
        h4_cls = "continuation"

    cur = conn.execute(
        """
        INSERT INTO alerts
            (instrument, direction, alert_classification, daily_breakout_id,
             reaction_source_id, h4_formation_id, h4_classification, alert_text, fired_at, alert_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert.instrument,
            alert.direction.value,
            alert.classification.value,
            daily_breakout_id,
            reaction_source_id,
            h4_formation_id,
            h4_cls,
            alert_text,
            _dt_str(alert.fired_at),
            alert.alert_type or alert_type_for(alert.classification.value, alert_text),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_recent_alerts(
    conn: sqlite3.Connection, instrument: str, limit: int = 20
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT instrument, direction, h4_classification, alert_text, fired_at
        FROM alerts
        WHERE instrument = ?
        ORDER BY fired_at DESC
        LIMIT ?
        """,
        (instrument, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_all_recent_alerts(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        """
        SELECT instrument, direction, h4_classification, alert_text, fired_at
        FROM alerts
        ORDER BY fired_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


# ── Raw candle cache ──────────────────────────────────────────────────────────

def upsert_raw_candles(conn: sqlite3.Connection, candles: list[Candle]) -> None:
    conn.executemany(
        """
        INSERT INTO raw_candles (instrument, timeframe, ts, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument, timeframe, ts) DO NOTHING
        """,
        [
            (
                c.instrument,
                c.timeframe.value,
                _dt_str(c.timestamp),
                c.open,
                c.high,
                c.low,
                c.close,
                c.volume,
            )
            for c in candles
        ],
    )
    conn.commit()


def get_cached_candles(
    conn: sqlite3.Connection,
    instrument: str,
    timeframe: Timeframe,
    limit: int = 500,
) -> list[Candle]:
    rows = conn.execute(
        """
        SELECT * FROM raw_candles
        WHERE instrument = ? AND timeframe = ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        (instrument, timeframe.value, limit),
    ).fetchall()
    candles = [
        Candle(
            instrument=row["instrument"],
            timeframe=Timeframe(row["timeframe"]),
            timestamp=_str_dt(row["ts"]),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )
        for row in rows
    ]
    candles.reverse()  # oldest → newest
    return candles
