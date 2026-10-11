"""
SQLite connection management and schema bootstrap.

All datetimes are stored as ISO 8601 UTC TEXT strings.
All prices are stored as REAL (IEEE 754 double).
No SQLite-specific types are used — this schema migrates to PostgreSQL
by changing the connection string and substituting INTEGER PRIMARY KEY
AUTOINCREMENT → SERIAL PRIMARY KEY.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS formations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument       TEXT    NOT NULL,
    timeframe        TEXT    NOT NULL,
    formation_type   TEXT    NOT NULL,
    direction        TEXT    NOT NULL,
    level            REAL    NOT NULL,
    established_at   TEXT    NOT NULL,
    candle_1_ts      TEXT    NOT NULL,
    candle_2_ts      TEXT    NOT NULL,
    is_active        INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_formations_inst_tf
    ON formations (instrument, timeframe, is_active);

CREATE TABLE IF NOT EXISTS daily_breakouts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument     TEXT    NOT NULL,
    direction      TEXT    NOT NULL,
    broken_level   REAL    NOT NULL,
    broken_type    TEXT    NOT NULL,
    breakout_ts    TEXT    NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_breakouts_inst
    ON daily_breakouts (instrument, is_active);

CREATE TABLE IF NOT EXISTS reaction_sources (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument         TEXT    NOT NULL,
    source_type        TEXT    NOT NULL,
    direction          TEXT    NOT NULL,
    level              REAL    NOT NULL,
    level_band_low     REAL    NOT NULL,
    level_band_high    REAL    NOT NULL,
    daily_breakout_id  INTEGER NOT NULL REFERENCES daily_breakouts(id),
    is_active          INTEGER NOT NULL DEFAULT 1,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_reactions_inst
    ON reaction_sources (instrument, is_active);

CREATE TABLE IF NOT EXISTS instrument_state (
    instrument             TEXT    PRIMARY KEY,
    last_daily_candle_ts   TEXT,
    last_h4_candle_ts      TEXT,
    active_breakout_id     INTEGER REFERENCES daily_breakouts(id),
    retest_in_progress     INTEGER NOT NULL DEFAULT 0,
    active_reaction_src_id INTEGER REFERENCES reaction_sources(id),
    continuation_mode      INTEGER NOT NULL DEFAULT 0,
    last_alert_h4_ts       TEXT,
    last_h4_breaker_level  REAL,
    updated_at             TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument           TEXT    NOT NULL,
    direction            TEXT    NOT NULL,
    alert_classification TEXT    NOT NULL DEFAULT 'origin',
    daily_breakout_id    INTEGER NOT NULL REFERENCES daily_breakouts(id),
    reaction_source_id   INTEGER          REFERENCES reaction_sources(id),
    h4_formation_id      INTEGER          REFERENCES formations(id),
    h4_classification    TEXT    NOT NULL,
    alert_text           TEXT    NOT NULL,
    fired_at             TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_inst
    ON alerts (instrument, fired_at);

CREATE TABLE IF NOT EXISTS raw_candles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument   TEXT    NOT NULL,
    timeframe    TEXT    NOT NULL,
    ts           TEXT    NOT NULL,
    open         REAL    NOT NULL,
    high         REAL    NOT NULL,
    low          REAL    NOT NULL,
    close        REAL    NOT NULL,
    volume       REAL    NOT NULL,
    UNIQUE (instrument, timeframe, ts)
);
CREATE INDEX IF NOT EXISTS idx_raw_candles_inst_tf
    ON raw_candles (instrument, timeframe, ts);

CREATE TABLE IF NOT EXISTS user_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    email            TEXT    NOT NULL UNIQUE,
    name             TEXT,
    password_hash    TEXT,
    role             TEXT    NOT NULL DEFAULT 'SUBSCRIBER',
    plan             TEXT    NOT NULL DEFAULT 'TRIAL',
    plan_expires_at  TEXT,
    telegram_chat_id TEXT,
    invite_token     TEXT    UNIQUE,
    invite_used      INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    last_login_at    TEXT
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Return a SQLite connection with WAL journaling and foreign keys enabled.
    Creates the database file if it does not exist.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def bootstrap_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indices if they do not already exist."""
    conn.executescript(_SCHEMA_SQL)
    _migrate_schema(conn)
    conn.commit()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """
    Apply incremental schema migrations to existing databases.
    All operations are idempotent — safe to run on every startup.
    """
    # Add continuation columns to instrument_state (safe on existing DBs)
    for col_def in [
        "continuation_mode INTEGER NOT NULL DEFAULT 0",
        "last_alert_h4_ts TEXT",
        "last_h4_breaker_level REAL",
    ]:
        col_name = col_def.split()[0]
        existing = {row[1] for row in conn.execute("PRAGMA table_info(instrument_state)").fetchall()}
        if col_name not in existing:
            conn.execute(f"ALTER TABLE instrument_state ADD COLUMN {col_def}")

    # Migrate alerts table: add alert_classification + nullable reaction/formation IDs
    # Check by looking for alert_classification column
    alert_cols = {row[1] for row in conn.execute("PRAGMA table_info(alerts)").fetchall()}
    if "alert_classification" not in alert_cols:
        conn.executescript("""
            CREATE TABLE alerts_v2 (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument           TEXT    NOT NULL,
                direction            TEXT    NOT NULL,
                alert_classification TEXT    NOT NULL DEFAULT 'origin',
                daily_breakout_id    INTEGER NOT NULL REFERENCES daily_breakouts(id),
                reaction_source_id   INTEGER          REFERENCES reaction_sources(id),
                h4_formation_id      INTEGER          REFERENCES formations(id),
                h4_classification    TEXT    NOT NULL,
                alert_text           TEXT    NOT NULL,
                fired_at             TEXT    NOT NULL
            );
            INSERT INTO alerts_v2
                (id, instrument, direction, alert_classification,
                 daily_breakout_id, reaction_source_id, h4_formation_id,
                 h4_classification, alert_text, fired_at)
            SELECT
                id, instrument, direction, 'origin',
                daily_breakout_id, reaction_source_id, h4_formation_id,
                h4_classification, alert_text, fired_at
            FROM alerts;
            DROP TABLE alerts;
            ALTER TABLE alerts_v2 RENAME TO alerts;
            CREATE INDEX IF NOT EXISTS idx_alerts_inst ON alerts (instrument, fired_at);
        """)

    conn.commit()
