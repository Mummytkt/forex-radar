"""
Owner → subscriber updates, shown on the Tutorials page with an unread badge.

The owner posts an update (title + message) and can choose to also send it to
every active subscriber's Telegram. Each user's read position is their own.
"""

from __future__ import annotations

import asyncio
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_owner, require_user

router = APIRouter()

MAX_TITLE, MAX_BODY = 120, 3500


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


@router.get("/announcements")
def list_announcements(request: Request):
    u = require_user(request)
    with _db(request) as conn:
        items = [dict(r) for r in conn.execute(
            "SELECT id, title, body, sent_telegram, created_at FROM announcements ORDER BY id DESC LIMIT 50")]
        last = _last_read(conn, u["id"])
    unread = 0 if u["role"] == "OWNER" else sum(1 for i in items if i["id"] > last)
    return {"items": items, "last_read_id": last, "unread": unread}


@router.get("/announcements/unread")
def unread_count(request: Request):
    """Lightweight count for the sidebar badge."""
    u = require_user(request)
    if u["role"] == "OWNER":
        return {"unread": 0}
    with _db(request) as conn:
        last = _last_read(conn, u["id"])
        n = conn.execute("SELECT COUNT(*) FROM announcements WHERE id > ?", (last,)).fetchone()[0]
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
    send_telegram: bool = False


def _active_subscriber_chats(conn) -> list[str]:
    now = datetime.now(timezone.utc)
    chats = []
    for r in conn.execute(
            "SELECT plan, plan_expires_at, telegram_chat_id FROM users "
            "WHERE role != 'OWNER' AND telegram_chat_id IS NOT NULL AND telegram_chat_id != ''"):
        exp = None
        if r["plan_expires_at"]:
            try:
                exp = datetime.fromisoformat(r["plan_expires_at"].replace("Z", "+00:00"))
                exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
            except Exception:
                exp = None
        if r["plan"] == "LIFETIME" or exp is None or exp > now:
            chats.append(r["telegram_chat_id"])
    return chats


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

    config = request.app.state.config
    with _db(request) as conn:
        cur = conn.execute(
            "INSERT INTO announcements (title, body, sent_telegram, created_at) VALUES (?, ?, ?, ?)",
            (title, text, 1 if body.send_telegram else 0, datetime.now(timezone.utc).isoformat()))
        new_id = cur.lastrowid
        chats = _active_subscriber_chats(conn) if body.send_telegram else []

    sent = 0
    if chats and config.telegram_enabled:
        from alerts.telegram import send_alert
        msg = f"📣 {title}\n\n{text}\n\nOn the platform: {config.frontend_url}/strategy"
        for chat in chats:
            if await send_alert(config.telegram_bot_token, chat, msg):
                sent += 1
            await asyncio.sleep(0.05)  # stay well under Telegram's rate limit
    return {"id": new_id, "telegram_sent": sent, "telegram_targets": len(chats)}


@router.delete("/announcements/{ann_id}")
def delete_announcement(ann_id: int, request: Request):
    require_owner(request)
    with _db(request) as conn:
        conn.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
    return {"ok": True}
