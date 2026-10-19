"""
Telegram alert delivery.

Thin wrapper around python-telegram-bot's Bot.send_message.
Uses HTML parse mode, which is safer than MarkdownV2 for dynamic text
(no special-character escaping required for standard alert content).

Every send goes through one shared pace-keeper (about 25 messages a second, under
Telegram's ~30/s bot limit). When Telegram answers "retry after N seconds" every
send pauses for N seconds and the message is retried; blocked/missing chats are
skipped without retrying.
"""

from __future__ import annotations

import asyncio
import logging
import time

from telegram import Bot
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

logger = logging.getLogger(__name__)

_RATE_PER_S = 25.0          # all bot messages together
_MAX_ATTEMPTS = 3           # network/server errors
_MAX_RATE_LIMIT_WAITS = 6   # "retry after" answers for one message
_next_slot = 0.0            # monotonic time of the next free send slot


def _reserve_slot() -> float:
    """Seconds to wait before this send may go. Runs without awaiting, so on the
    single event loop no two sends can take the same slot."""
    global _next_slot
    now = time.monotonic()
    slot = max(now, _next_slot)
    _next_slot = slot + 1.0 / _RATE_PER_S
    return slot - now


def _pause_all(seconds: float) -> None:
    global _next_slot
    _next_slot = max(_next_slot, time.monotonic() + seconds)


def _retry_after_seconds(e: RetryAfter) -> float:
    ra = e.retry_after
    return ra.total_seconds() if hasattr(ra, "total_seconds") else float(ra)

_RETRY_DELAY_S = 5.0


async def send_alert(bot_token: str, chat_id: str, text: str) -> bool:
    """
    Send a plain-text message to one Telegram chat, paced with every other send.
    Returns True on success, False if it could not be delivered.

    text is sent as plain text (no HTML/Markdown parse mode) to avoid
    formatting errors from special characters in instrument names or prices.
    """
    bot = Bot(token=bot_token)
    errors = 0
    waits = 0
    while True:
        delay = _reserve_slot()
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            logger.info("Alert sent to chat %s", chat_id)
            return True
        except RetryAfter as e:
            waits += 1
            secs = _retry_after_seconds(e)
            _pause_all(secs + 0.5)
            if waits > _MAX_RATE_LIMIT_WAITS:
                logger.error("Telegram kept rate-limiting chat %s — giving up", chat_id)
                return False
            logger.warning("Telegram rate limit — pausing all sends %.1fs", secs)
        except Forbidden as e:  # user blocked the bot / left
            logger.warning("Telegram chat %s refused the message: %s", chat_id, e)
            return False
        except BadRequest as e:  # chat not found, bad id
            logger.warning("Telegram rejected chat %s: %s", chat_id, e)
            return False
        except TelegramError as e:
            errors += 1
            if errors >= _MAX_ATTEMPTS:
                logger.error("Telegram send to %s failed after %d tries: %s", chat_id, errors, e)
                return False
            logger.warning("Telegram send failed (try %d): %s — retrying", errors, e)
            await asyncio.sleep(2.0 * errors)


async def send_many(bot_token: str, chat_ids: list[str], text: str, concurrency: int = 20) -> int:
    """Send the same text to many chats. Up to `concurrency` sends are in flight at
    once, all paced by send_alert. Returns how many were delivered."""
    sem = asyncio.Semaphore(concurrency)

    async def one(cid: str) -> bool:
        async with sem:
            return await send_alert(bot_token, cid, text)

    results = await asyncio.gather(*(one(c) for c in chat_ids))
    return sum(1 for r in results if r)


async def send_document(bot_token: str, chat_id: str, path: str, filename: str, caption: str = "") -> int | None:
    """Send a file (e.g. the encrypted nightly backup) to a Telegram chat.
    Returns the Telegram message id on success, None on failure."""
    bot = Bot(token=bot_token)
    try:
        with open(path, "rb") as f:
            msg = await bot.send_document(chat_id=chat_id, document=f, filename=filename,
                                          caption=caption[:1024], read_timeout=120, write_timeout=120)
        logger.info("Document %s sent to chat %s", filename, chat_id)
        return msg.message_id
    except TelegramError as e:
        logger.error("Telegram document send failed: %s", e)
        return None


async def delete_message(bot_token: str, chat_id: str, message_id: int) -> tuple[bool, str]:
    """Delete one of the bot's messages. Returns (ok, error text). A message that is
    already gone (e.g. deleted by hand) counts as success."""
    bot = Bot(token=bot_token)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True, ""
    except TelegramError as e:
        err = str(e)
        if "not found" in err.lower():
            return True, ""
        return False, err


def send_alert_sync(bot_token: str, chat_id: str, text: str) -> bool:
    """Synchronous wrapper around send_alert for use outside async contexts."""
    return asyncio.run(send_alert(bot_token, chat_id, text))


async def get_bot_username(bot_token: str) -> str | None:
    """Return the bot's @username (without the @), or None on failure."""
    try:
        bot = Bot(token=bot_token)
        me = await bot.get_me()
        return me.username
    except TelegramError as e:
        logger.warning("get_me failed: %s", e)
        return None
