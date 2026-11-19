"""Job Hunt (owner only): the tracker page's API and the Job Hunt bot's webhook. See alerts/job_digest.py."""

from __future__ import annotations

import hmac
import sqlite3
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from alerts.job_digest import GOAL, KINDS, STATUSES, add_manual, ensure_table, handle_update, run_job_digest, set_status
from api.auth import require_owner

router = APIRouter()


@contextmanager
def _conn(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        ensure_table(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


@router.post("/jobs-bot/update")
async def jobs_bot_update(request: Request):
    """Telegram webhook of the Job Hunt bot: verified by the secret header, like the main bot's."""
    config = request.app.state.config
    sent = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not config.jobs_bot_token or not config.telegram_webhook_secret or not hmac.compare_digest(
            sent.encode(), config.telegram_webhook_secret.encode()):
        raise HTTPException(status_code=401, detail="bad secret")
    try:
        update = await request.json()
    except Exception:
        return {"ok": True}
    with _conn(request) as conn:
        await handle_update(conn, config, update)
    return {"ok": True}


@router.get("/jobs/apps")
def list_apps(request: Request):
    require_owner(request)
    with _conn(request) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM job_apps ORDER BY sent_at DESC, id DESC LIMIT 500")]
    return {"apps": rows, "bot_on": bool(request.app.state.config.jobs_bot_token), "goal": GOAL}


class StatusBody(BaseModel):
    status: str | None = None
    kind: str | None = None


class AddBody(BaseModel):
    title: str
    company: str = ""
    url: str = ""
    source: str = ""
    kind: str = "job"
    status: str = "applied"


@router.post("/jobs/apps")
def add_app(body: AddBody, request: Request):
    """An application made outside the digest (LinkedIn, Jobberman, Upwork, Fiverr, a company site)."""
    require_owner(request)
    if not body.title.strip():
        raise HTTPException(400, "Give the job a title")
    if body.kind not in KINDS or body.status not in STATUSES:
        raise HTTPException(400, "Unknown type or status")
    with _conn(request) as conn:
        return add_manual(conn, body.title, body.company, body.url, body.source or "Added by you", body.kind, body.status)


@router.patch("/jobs/apps/{jid}")
def update_app(jid: int, body: StatusBody, request: Request):
    require_owner(request)
    if (body.status and body.status not in STATUSES) or (body.kind and body.kind not in KINDS):
        raise HTTPException(400, "Unknown status or type")
    with _conn(request) as conn:
        if body.kind:
            conn.execute("UPDATE job_apps SET kind = ? WHERE id = ?", (body.kind, jid))
            conn.commit()
        r = set_status(conn, jid, body.status) if body.status else \
            (dict(x) if (x := conn.execute("SELECT * FROM job_apps WHERE id = ?", (jid,)).fetchone()) else None)
    if not r:
        raise HTTPException(404, "Not found")
    return r


@router.post("/jobs/run")
async def run_now(request: Request):
    """Send the digest now (the first one, or a test)."""
    require_owner(request)
    config = request.app.state.config
    if not config.jobs_bot_token:
        raise HTTPException(400, "The Job Hunt bot isn't set up yet (JOBS_BOT_TOKEN).")
    n = await run_job_digest(config.db_path, config)
    return {"sent": n}
