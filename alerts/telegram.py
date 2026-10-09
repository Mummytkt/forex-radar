"""
Telegram alert delivery.

Thin wrapper around python-telegram-bot's Bot.send_message.
Uses HTML parse mode, which is safer than MarkdownV2 for dynamic text
(no special-character escaping required for standard alert content).

Retries once on transient errors with a short backoff.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

_RETRY_DELAY_S = 5.0


async def send_alert(bot_token: str, chat_id: str, text: str) -> bool:
    """
    Send a plain-text alert message to the given Telegram chat.
    Returns True on success, False after a failed retry.

    text is sent as plain text (no HTML/Markdown parse mode) to avoid
    formatting errors from special characters in instrument names or prices.
    """
    bot = Bot(token=bot_token)
    for attempt in range(2):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
            )
            logger.info("Alert sent to chat %s", chat_id)
            return True
        except TelegramError as e:
            if attempt == 0:
                logger.warning("Telegram send failed (attempt 1): %s — retrying in %ss", e, _RETRY_DELAY_S)
                await asyncio.sleep(_RETRY_DELAY_S)
            else:
                logger.error("Telegram send failed after retry: %s", e)
                return False
    return False


def send_alert_sync(bot_token: str, chat_id: str, text: str) -> bool:
    """Synchronous wrapper around send_alert for use outside async contexts."""
    return asyncio.run(send_alert(bot_token, chat_id, text))
