"""
Entry Tester — the owner's backtest of entry patterns (owner only).

Each row is one trade idea (a pair, a date, a direction, the H4 alert it came
from). On that same trade the owner ticks how each entry pattern did: win,
loss, breakeven or no entry (the pattern never formed), plus the RR it made.
The page then compares the patterns across every trade. Subscribers' Backtest
Journal is separate and unchanged.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_owner

router = APIRouter()

# The entry patterns being compared (key → label). Keys are stored, so never rename one.
ENTRY_TYPES: list[tuple[str, str]] = [
    ("direct_fvg", "Direct entry on FVG"),
    ("direct_engulfing", "Direct entry on Engulfing"),
    ("direct_h4_key", "Direct entry on H4 fresh key level"),
    ("h1_smc", "1H SMC confirmation"),
    ("h1_engulfing", "1H Engulfing"),
    ("h2_engulfing", "2H Engulfing"),
    ("m5_cisd", "5M CISD"),
    ("m5_smc", "5M SMC"),
    ("m15_smc", "15M SMC"),
    ("m15_cisd", "15M CISD"),
    ("h4_3cr", "4H 3CR"),
    ("h2_3cr", "2H 3CR"),
]
_KEYS = {k for k, _ in ENTRY_TYPES}
OUTCOMES = ("win", "loss", "be", "none")


@contextmanager
def _db(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class EntryResult(BaseModel):
    outcome: str
    rr: Optional[float] = None


class TradeBody(BaseModel):
    trade_date: str
    instrument: str
    direction: str
    alert_type: str = ""
    notes: str = ""
    results: dict[str, EntryResult] = {}


def _clean(body: TradeBody) -> tuple[str, str, str, str, str, str]:
    if body.direction not in ("buy", "sell"):
        raise HTTPException(400, "direction must be buy or sell")
    if not body.instrument.strip() or not body.trade_date.strip():
        raise HTTPException(400, "pair and date are required")
    res = {}
    for k, r in body.results.items():
        if k not in _KEYS or r.outcome not in OUTCOMES:
            raise HTTPException(400, f"unknown entry type or outcome: {k}")
        rr = r.rr if r.outcome == "win" and r.rr is not None and 0 < r.rr <= 100 else None
        res[k] = {"outcome": r.outcome, "rr": rr}
    return (body.trade_date.strip()[:10], body.instrument.strip().upper()[:20], body.direction,
            body.alert_type.strip()[:40], body.notes.strip()[:500], json.dumps(res))


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["results"] = json.loads(d.pop("results_json") or "{}")
    return d


@router.get("/entry-tests/types")
def entry_types(request: Request):
    require_owner(request)
    return [{"key": k, "label": l} for k, l in ENTRY_TYPES]


@router.get("/entry-tests")
def list_trades(request: Request):
    u = require_owner(request)
    with _db(request) as conn:
        rows = conn.execute(
            "SELECT * FROM entry_tests WHERE user_id = ? ORDER BY trade_date DESC, id DESC", (u["id"],)).fetchall()
    return [_row(r) for r in rows]


@router.post("/entry-tests")
def create_trade(request: Request, body: TradeBody):
    u = require_owner(request)
    vals = _clean(body)
    with _db(request) as conn:
        cur = conn.execute(
            """INSERT INTO entry_tests (trade_date, instrument, direction, alert_type, notes, results_json, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""", vals + (u["id"],))
        row = conn.execute("SELECT * FROM entry_tests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row(row)


@router.put("/entry-tests/{trade_id}")
def update_trade(trade_id: int, request: Request, body: TradeBody):
    u = require_owner(request)
    vals = _clean(body)
    with _db(request) as conn:
        cur = conn.execute(
            """UPDATE entry_tests SET trade_date = ?, instrument = ?, direction = ?, alert_type = ?, notes = ?,
                      results_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE id = ? AND user_id = ?""", vals + (trade_id, u["id"]))
        if cur.rowcount == 0:
            raise HTTPException(404, "Trade not found")
        row = conn.execute("SELECT * FROM entry_tests WHERE id = ?", (trade_id,)).fetchone()
    return _row(row)


@router.delete("/entry-tests/{trade_id}")
def delete_trade(trade_id: int, request: Request):
    u = require_owner(request)
    with _db(request) as conn:
        conn.execute("DELETE FROM entry_tests WHERE id = ? AND user_id = ?", (trade_id, u["id"]))
    return {"ok": True}
