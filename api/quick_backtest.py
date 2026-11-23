"""Quick Backtest (owner only, 2026-11-21): the fastest way to journal one entry model's backtest.

One row per setup the owner finds on the chart (breakout → liquidity → POI), with tick boxes instead of typing:
the date, pair, buy/sell, whether it was an inside-range or opposite-range trade, and, for each H1 confirmation
that formed at the POI (PCL, Engulfing, OCTGD 1, OCTGD 2, CISD), how it ended and how many times she took it before
price closed outside the level. The confirmation that formed first is starred: that is the one she would trade.

One pass through 2020-2026 records every confirmation at each setup, so she never re-scrolls the years per
confirmation. Results use her rules: TP 3R, breakeven at 2R. A setup taken N times: each take before the last is a
loss; the last take is the ticked result (same as the Entry Tester's takes). No pictures, for speed.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_owner

router = APIRouter()

# Stored keys: never rename one (labels can change). Order = how they show.
CONFIRMATIONS = [("pcl", "H1 PCL"), ("eng", "H1 Engulfing"), ("octgd1", "H1 OCTGD 1"), ("octgd2", "H1 OCTGD 2"),
                 ("cisd", "H1 CISD"), ("octgd15", "M15 OCTGD"), ("octgd215", "M15 OCTGD 2"), ("cisd15", "M15 CISD"),
                 ("cisd5", "M5 CISD")]
OUTCOMES = ("win", "be", "loss")
RANGES = ("inside", "opposite")
DEFAULT_TP_R = 3.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS quick_bt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    date TEXT NOT NULL,             -- the setup's chart date, YYYY-MM-DD
    side TEXT NOT NULL,             -- buy / sell
    range_type TEXT NOT NULL,       -- inside / opposite
    valid INTEGER NOT NULL DEFAULT 1,
    results_json TEXT NOT NULL,     -- {"pcl": {"outcome": "win", "takes": 2}, ...}; absent = did not form
    first TEXT,                     -- the confirmation that formed first (the one she would trade)
    tp_r REAL NOT NULL DEFAULT 3,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)"""


@contextmanager
def _db(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


class Result(BaseModel):
    outcome: str
    takes: int = 1


class SetupBody(BaseModel):
    pair: str = "EURUSD"
    date: str
    side: str
    range_type: str
    valid: bool = True
    results: dict[str, Result] = {}
    first: Optional[str] = None
    note: str = ""


def _clean(b: SetupBody) -> tuple:
    keys = {k for k, _ in CONFIRMATIONS}
    pair = re.sub(r"[^A-Z0-9]", "", b.pair.upper())[:12] or "EURUSD"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", b.date or ""):
        raise HTTPException(400, "Pick the setup's date")
    if b.side not in ("buy", "sell"):
        raise HTTPException(400, "Pick Buy or Sell")
    if b.range_type not in RANGES:
        raise HTTPException(400, "Pick Inside range or Opposite range")
    res = {}
    for k, r in b.results.items():
        if k not in keys or r.outcome not in OUTCOMES:
            raise HTTPException(400, f"Unknown confirmation or result: {k}")
        res[k] = {"outcome": r.outcome, "takes": max(1, min(int(r.takes or 1), 20))}
    first = b.first if b.first in res else None
    if res and not first:      # one formed: it is the first; several: she must star one
        first = next(iter(res)) if len(res) == 1 else None
    return pair, b.date, b.side, b.range_type, int(b.valid), json.dumps(res), first, b.note.strip()[:300]


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["results"] = json.loads(d.pop("results_json") or "{}")
    d["valid"] = bool(d["valid"])
    return d


@router.get("/quick-bt")
def list_setups(request: Request):
    require_owner(request)
    with _db(request) as conn:
        rows = [_row(r) for r in conn.execute("SELECT * FROM quick_bt ORDER BY date DESC, id DESC")]
    return {"setups": rows, "confirmations": CONFIRMATIONS, "tp_r": DEFAULT_TP_R, "be_at_r": 2}


@router.post("/quick-bt")
def add_setup(body: SetupBody, request: Request):
    require_owner(request)
    now = datetime.now(timezone.utc).isoformat()
    with _db(request) as conn:
        sid = conn.execute(
            "INSERT INTO quick_bt (pair, date, side, range_type, valid, results_json, first, note, tp_r, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*_clean(body), DEFAULT_TP_R, now, now)).lastrowid
        return _row(conn.execute("SELECT * FROM quick_bt WHERE id = ?", (sid,)).fetchone())


@router.put("/quick-bt/{sid}")
def update_setup(sid: int, body: SetupBody, request: Request):
    require_owner(request)
    with _db(request) as conn:
        if not conn.execute("SELECT 1 FROM quick_bt WHERE id = ?", (sid,)).fetchone():
            raise HTTPException(404, "Setup not found")
        conn.execute("UPDATE quick_bt SET pair = ?, date = ?, side = ?, range_type = ?, valid = ?, results_json = ?, "
                     "first = ?, note = ?, updated_at = ? WHERE id = ?",
                     (*_clean(body), datetime.now(timezone.utc).isoformat(), sid))
        return _row(conn.execute("SELECT * FROM quick_bt WHERE id = ?", (sid,)).fetchone())


@router.delete("/quick-bt/{sid}")
def delete_setup(sid: int, request: Request):
    require_owner(request)
    with _db(request) as conn:
        conn.execute("DELETE FROM quick_bt WHERE id = ?", (sid,))
    return {"ok": True}


# ── Auto-check (2026-11-23): she marks the POI, the server finds and trades every confirmation ──────────────
class AutoBody(BaseModel):
    pair: str = "EURUSD"
    side: str
    level: float               # the level line (an OC: the first candle's close; a V: its level; ...)
    start: str                 # when the watch begins, ISO 8601 with its UTC offset (the owner's timezone)
    end_at: Optional[str] = None   # the next H4 breakout, if she knows it (ends the setup)
    mode: str = "limit"        # limit (her live rule) or instant
    tp_r: float = DEFAULT_TP_R
    be_r: float = 2.0


def _cache_base(request: Request) -> str:
    import os
    return os.path.dirname(os.path.abspath(request.app.state.config.db_path)) or "."


@router.get("/quick-bt/auto/status")
def auto_status(request: Request, pair: str = "EURUSD"):
    require_owner(request)
    from api.autobacktest import coverage
    return coverage(pair.upper(), _cache_base(request))


@router.post("/quick-bt/auto")
def auto_check(request: Request, body: AutoBody):
    """Runs in a worker thread (a plain def route), so the price checks keep running meanwhile."""
    require_owner(request)
    from api.autobacktest import run
    if body.side not in ("buy", "sell"):
        raise HTTPException(400, "side must be buy or sell")
    def _when(v: str) -> datetime:
        t = datetime.fromisoformat(v)
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    try:
        start = _when(body.start)
        end_at = _when(body.end_at) if body.end_at else None
    except ValueError:
        raise HTTPException(400, "start / end must be a date and time")
    if not body.level > 0:
        raise HTTPException(400, "Type the level's price")
    if body.mode not in ("limit", "instant"):
        raise HTTPException(400, "mode must be limit or instant")
    try:
        return run(body.pair.upper(), body.side, body.level, start, _cache_base(request), body.tp_r, body.be_r,
                   body.mode, end_at)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
