"""
Saved posts on the owner's Job Hunt bot (owner request 2026-11-23).

The owner rephrases quotes and post ideas she sees, and posts them in batches later.
  • Any message to the bot that isn't a /command is saved as a post (several messages = several posts).
  • /posts lists every saved post as a tap-to-copy box with ✅ Posted and 🗑 Delete buttons; either one
    takes it off the list (like ✅ Applied on a job). Posted ones are kept in the table, marked posted.
  • The evening check mentions how many are waiting.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

MAX_LIST = 30   # /posts shows at most this many (oldest first), so a batch never floods the chat


def ensure_table(conn) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS post_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',      -- draft | posted | deleted
        created_at TEXT NOT NULL,
        done_at TEXT)""")
    conn.commit()


def save(conn, text: str) -> int:
    ensure_table(conn)
    cur = conn.execute("INSERT INTO post_drafts (text, created_at) VALUES (?, ?)",
                       (text.strip(), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return cur.lastrowid


def waiting(conn) -> list[tuple[int, str]]:
    ensure_table(conn)
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT id, text FROM post_drafts WHERE status = 'draft' ORDER BY id LIMIT ?", (MAX_LIST,))]


def count_waiting(conn) -> int:
    ensure_table(conn)
    return conn.execute("SELECT COUNT(*) FROM post_drafts WHERE status = 'draft'").fetchone()[0]


def mark(conn, pid: int, status: str) -> bool:
    ensure_table(conn)
    cur = conn.execute("UPDATE post_drafts SET status = ?, done_at = ? WHERE id = ? AND status = 'draft'",
                       (status, datetime.now(timezone.utc).isoformat(), pid))
    conn.commit()
    return cur.rowcount > 0


def buttons(pid: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Posted", callback_data=f"pd:p:{pid}"),
                                  InlineKeyboardButton("🗑 Delete", callback_data=f"pd:d:{pid}")]])


def post_text(pid: int, text: str, n: int | None = None) -> str:
    head = f"📝 <b>Post {n}</b>" if n else "📝 <b>Saved post</b>"
    return f"{head} · tap the box to copy\n<code>{html.escape(text, quote=False)}</code>"


async def send_list(conn, token: str, chat: str, send) -> None:
    rows = waiting(conn)
    total = count_waiting(conn)
    if not rows:
        await send(token, chat, "📝 No saved posts. Send me any text (not starting with /) and I'll keep it here "
                                "until you post it.")
        return
    more = f" (showing the first {len(rows)})" if total > len(rows) else ""
    await send(token, chat, f"📝 <b>{total} saved post{'s' if total != 1 else ''}</b>{more}\nTap a box to copy, "
                            "post it, then tap ✅ Posted and it leaves this list.")
    for n, (pid, text) in enumerate(rows, 1):
        await send(token, chat, post_text(pid, text, n), buttons(pid))


async def handle_callback(conn, bot, cq: dict, data: str) -> str:
    """pd:p:<id> = posted, pd:d:<id> = deleted. Replaces the buttons with the outcome; returns the toast."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.error import TelegramError
    parts = data.split(":")
    if len(parts) != 3 or parts[1] not in ("p", "d") or not parts[2].isdigit():
        return ""
    status = "posted" if parts[1] == "p" else "deleted"
    ok = mark(conn, int(parts[2]), status)
    try:
        await bot.edit_message_reply_markup(
            chat_id=cq["message"]["chat"]["id"], message_id=cq["message"]["message_id"],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                "✅ Posted" if status == "posted" else "🗑 Deleted", callback_data="pd:noop")]]))
    except TelegramError:
        pass
    if not ok:
        return "Already done."
    left = count_waiting(conn)
    return (("Posted! " if status == "posted" else "Deleted. ") +
            (f"{left} saved post{'s' if left != 1 else ''} left." if left else "No saved posts left."))
