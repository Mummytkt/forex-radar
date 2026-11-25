"""
"Test my strategy" requests (owner, 2026-11-25). A trader, mentor or community lead describes their strategy on the
public page; it lands here, the owner gets a Telegram note, and her Requests page (it replaced Job Hunt) tracks each
one from New to Delivered. The owner now wants clients to come to her instead of applying for jobs.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import rate_limited, require_owner

router = APIRouter()

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT NOT NULL,
    contact TEXT NOT NULL,          -- email, WhatsApp or Telegram, as they typed it
    role TEXT,                      -- trader / mentor / community / other
    markets TEXT,
    timeframes TEXT,
    strategy TEXT NOT NULL,         -- their entry rules, in their own words
    backtest_now TEXT,              -- how they test it today
    goal TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT
)"""
STATUSES = ("new", "contacted", "call", "building", "delivered", "closed")
ROLES = ("trader", "mentor", "community", "other")


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


class RequestBody(BaseModel):
    name: str
    contact: str
    role: str = "trader"
    markets: str = ""
    timeframes: str = ""
    strategy: str
    backtest_now: str = ""
    goal: str = ""
    website: str = ""               # a hidden field people never see: bots fill it in


def _clip(s: Optional[str], n: int) -> str:
    return (s or "").strip()[:n]


@router.post("/public/strategy-request")
async def create_request(body: RequestBody, request: Request):
    if body.website:                # a bot: say thanks, keep nothing
        return {"ok": True}
    ip = request.client.host if request.client else "?"
    if rate_limited(f"strategy-req:{ip}", 5, 3600):
        raise HTTPException(429, "Too many requests from here. Please try again in an hour.")
    name, contact, strategy = _clip(body.name, 80), _clip(body.contact, 120), _clip(body.strategy, 4000)
    if len(name) < 2 or len(contact) < 5:
        raise HTTPException(400, "Please add your name and a way to reach you (email, WhatsApp or Telegram).")
    if len(strategy) < 30:
        raise HTTPException(400, "Please describe your strategy and entry rules in a few sentences.")
    role = body.role if body.role in ROLES else "other"
    now = datetime.now(timezone.utc).isoformat()
    with _db(request) as conn:
        rid = conn.execute(
            "INSERT INTO strategy_requests (created_at, name, contact, role, markets, timeframes, strategy, backtest_now, "
            "goal, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (now, name, contact, role, _clip(body.markets, 200), _clip(body.timeframes, 120), strategy,
             _clip(body.backtest_now, 600), _clip(body.goal, 600), now)).lastrowid
        owner = conn.execute("SELECT telegram_chat_id FROM users WHERE role = 'OWNER' AND telegram_chat_id IS NOT NULL "
                             "AND telegram_chat_id != '' LIMIT 1").fetchone()
    await _notify(request, owner[0] if owner else None, rid, name, role, body.markets, strategy)
    return {"ok": True}


async def _notify(request: Request, chat: Optional[str], rid: int, name: str, role: str, markets: str, strategy: str) -> None:
    """A Telegram note to the owner on the Job Hunt bot (her business bot), else the main bot."""
    if not chat:
        return
    import html
    cfg = request.app.state.config
    token = getattr(cfg, "jobs_bot_token", "") or cfg.telegram_bot_token
    text = (f"🧪 <b>New strategy request #{rid}</b>\n{html.escape(name)} · {role}"
            + (f" · {html.escape(markets[:80])}" if markets else "")
            + f"\n\n<i>{html.escape(strategy[:400])}{'…' if len(strategy) > 400 else ''}</i>\n\nOpen Requests to reply.")
    try:
        from alerts.job_digest import _send
        await _send(token, str(chat), text)
    except Exception:
        pass


@router.get("/strategy-requests")
def list_requests(request: Request):
    require_owner(request)
    with _db(request) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM strategy_requests ORDER BY id DESC")]
    return {"requests": rows, "statuses": STATUSES}


class Patch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.patch("/strategy-requests/{rid}")
def update_request(rid: int, body: Patch, request: Request):
    require_owner(request)
    with _db(request) as conn:
        if not conn.execute("SELECT 1 FROM strategy_requests WHERE id = ?", (rid,)).fetchone():
            raise HTTPException(404, "Request not found")
        now = datetime.now(timezone.utc).isoformat()
        if body.status is not None:
            if body.status not in STATUSES:
                raise HTTPException(400, "Unknown status")
            conn.execute("UPDATE strategy_requests SET status = ?, updated_at = ? WHERE id = ?", (body.status, now, rid))
        if body.notes is not None:
            conn.execute("UPDATE strategy_requests SET notes = ?, updated_at = ? WHERE id = ?", (body.notes[:4000], now, rid))
        return dict(conn.execute("SELECT * FROM strategy_requests WHERE id = ?", (rid,)).fetchone())


@router.delete("/strategy-requests/{rid}")
def delete_request(rid: int, request: Request):
    require_owner(request)
    with _db(request) as conn:
        conn.execute("DELETE FROM strategy_requests WHERE id = ?", (rid,))
    return {"ok": True}
