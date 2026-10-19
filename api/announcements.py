"""
Owner → subscriber updates, shown on the Tutorials & Updates page with an unread badge.

The owner posts an update (title + message) to everyone or to chosen plans
(any combination), and can also send it to that same audience's Telegram.
Subscribers only see updates addressed to their current plan; each user's
read position is their own.
"""

from __future__ import annotations

import asyncio
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_owner, require_user

router = APIRouter()

MAX_TITLE, MAX_BODY = 120, 3500
PLANS = ("TRIAL", "30DAY", "6MONTH", "9MONTH", "12MONTH", "LIFETIME")


@contextmanager
def _db(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _last_read(conn, uid: int) -> int:
    row = conn.execute("SELECT last_read_id FROM announcement_reads WHERE user_id = ?", (uid,)).fetchone()
    return row[0] if row else 0


def _plan_of(conn, uid: int) -> Optional[str]:
    row = conn.execute("SELECT plan FROM users WHERE id = ?", (uid,)).fetchone()
    return row[0] if row else None


def _visible(audience: Optional[str], plan: Optional[str]) -> bool:
    return not audience or (plan is not None and plan in audience.split(","))


def _is_active(plan, plan_expires_at, now) -> bool:
    if plan == "LIFETIME" or not plan_expires_at:
        return True
    try:
        exp = datetime.fromisoformat(plan_expires_at.replace("Z", "+00:00"))
        exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        return exp > now
    except Exception:
        return True


def _subscribers(conn):
    now = datetime.now(timezone.utc)
    return [r for r in conn.execute(
        "SELECT plan, plan_expires_at, telegram_chat_id FROM users WHERE role != 'OWNER'")
        if _is_active(r["plan"], r["plan_expires_at"], now)]


def _visible_items(conn, u) -> list[dict]:
    items = [dict(r) for r in conn.execute(
        "SELECT id, title, body, sent_telegram, audience, created_at FROM announcements ORDER BY id DESC LIMIT 100")]
    if u["role"] == "OWNER":
        return items
    plan = _plan_of(conn, u["id"])
    return [i for i in items if _visible(i["audience"], plan)]


@router.get("/announcements")
def list_announcements(request: Request):
    u = require_user(request)
    with _db(request) as conn:
        items = _visible_items(conn, u)
        last = _last_read(conn, u["id"])
        out = {"items": items[:50], "last_read_id": last,
               "unread": 0 if u["role"] == "OWNER" else sum(1 for i in items if i["id"] > last)}
        if u["role"] == "OWNER":
            counts = {p: 0 for p in PLANS}
            linked = {p: 0 for p in PLANS}
            for s in _subscribers(conn):
                if s["plan"] in counts:
                    counts[s["plan"]] += 1
                    linked[s["plan"]] += 1 if (s["telegram_chat_id"] or "").strip() else 0
            out["plan_counts"] = counts
            out["plan_telegram"] = linked
    return out


@router.get("/announcements/unread")
def unread_count(request: Request):
    """Lightweight count for the sidebar badge (only updates addressed to this user)."""
    u = require_user(request)
    if u["role"] == "OWNER":
        return {"unread": 0}
    with _db(request) as conn:
        last = _last_read(conn, u["id"])
        n = sum(1 for i in _visible_items(conn, u) if i["id"] > last)
    return {"unread": n}


class ReadBody(BaseModel):
    last_id: int


@router.post("/announcements/read")
def mark_read(body: ReadBody, request: Request):
    u = require_user(request)
    with _db(request) as conn:
        newest = conn.execute("SELECT COALESCE(MAX(id), 0) FROM announcements").fetchone()[0]
        last_id = max(0, min(body.last_id, newest))
        conn.execute(
            "INSERT INTO announcement_reads (user_id, last_read_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET last_read_id = MAX(last_read_id, excluded.last_read_id)",
            (u["id"], last_id))
    return {"ok": True}


class PostBody(BaseModel):
    title: str
    body: str
    plans: Optional[list[str]] = None   # None / empty = everyone
    send_telegram: bool = False


@router.post("/announcements")
async def post_announcement(body: PostBody, request: Request):
    require_owner(request)
    title, text = body.title.strip(), body.body.strip()
    if not title or not text:
        raise HTTPException(400, "Add a title and a message.")
    if len(title) > MAX_TITLE:
        raise HTTPException(400, f"Keep the title under {MAX_TITLE} characters.")
    if len(text) > MAX_BODY:
        raise HTTPException(400, f"Keep the message under {MAX_BODY} characters.")
    chosen = {p.upper() for p in (body.plans or [])}
    if any(p not in PLANS for p in chosen):
        raise HTTPException(400, "Unknown plan selected.")
    plans = sorted(chosen, key=PLANS.index)
    audience = ",".join(plans) if plans and len(plans) < len(PLANS) else None

    config = request.app.state.config
    with _db(request) as conn:
        cur = conn.execute(
            "INSERT INTO announcements (title, body, sent_telegram, audience, created_at) VALUES (?, ?, ?, ?, ?)",
            (title, text, 1 if body.send_telegram else 0, audience, datetime.now(timezone.utc).isoformat()))
        new_id = cur.lastrowid
        chats = [s["telegram_chat_id"] for s in _subscribers(conn)
                 if (s["telegram_chat_id"] or "").strip() and _visible(audience, s["plan"])] if body.send_telegram else []

    sent = 0
    if chats and config.telegram_enabled:
        from alerts.telegram import send_many
        msg = f"📣 {title}\n\n{text}\n\nOn the platform: {config.frontend_url}/strategy"
        sent = await send_many(config.telegram_bot_token, chats, msg)  # paced under Telegram's limit
    return {"id": new_id, "audience": audience, "telegram_sent": sent, "telegram_targets": len(chats)}


@router.delete("/announcements/{ann_id}")
def delete_announcement(ann_id: int, request: Request):
    require_owner(request)
    with _db(request) as conn:
        conn.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
    return {"ok": True}
