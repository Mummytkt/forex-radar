"""
The bot's command menu (the "Menu" button in the bot's chat).

Page commands answer with a button that opens that page of the platform inside
Telegram as a Mini App; the website signs the person in from Telegram itself
(see api/auth.py telegram_login), so no browser or password is needed.
/news is switched on/off right in the chat; /help explains the alert words.
Only private chats are answered (Mini App buttons don't work in groups).

To keep the chat tidy the typed command is deleted, each menu reply replaces
the previous one, and every reply has a ✕ Close button (callback "chx", which
deletes the message it sits on).
"""

from __future__ import annotations

import logging

from telegram import Bot, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonCommands, WebAppInfo
from telegram.error import TelegramError

from alerts.telegram import answer_button, delete_message, send_message_id

logger = logging.getLogger(__name__)

# command → (menu description, page, button label, reply text)
PAGES = {
    "board": ("Live Bias Board", "/dashboard", "📈 Open Bias Board",
              "The live Bias Board: every pair's Daily bias and where it stands."),
    "alerts": ("Your latest alerts", "/alerts", "🧾 Open Signal Log",
               "Every alert sent to you, newest first."),
    "pricealerts": ("Open price alerts", "/price-alerts", "🎯 Open Level Watch",
                    "Set a price level and get pinged here when price reaches it."),
    "confirmations": ("Open confirmation alerts", "/preferences", "🎛 Open Alert Filters",
                      "Choose which confirmation alerts reach you, the message style and the engulfing type."),
    "settings": ("Your pairs and account", "/settings", "⚙️ Open Settings",
                 "Choose your pairs and manage your account."),
}

COMMANDS = [
    ("start", "Open the Bias Pointer"),
    *[(c, v[0]) for c, v in PAGES.items()],
    ("news", "High-impact news reminders"),
    ("help", "What the words in an alert mean"),
]

HELP_TEXT = """📖 What the words in an alert mean

BUY / SELL CONFIRMED (Origin): the first 4H confirmation after a Daily breakout. Look for an entry in that direction.

CONTINUATION CONFIRMED: the Daily direction is still on and 4H confirmed again (in-line breakout, Breaker retest, OC reaction, back in line or engulfing).

Daily breakout: a Daily candle closed beyond the last Daily high or low. This sets the direction.

Reaction: price came back to a Daily level (Breaker, OC, or a level inside the range) and held.

External / Internal: whether the 4H structure that broke formed before (External) or after (Internal) price reached the Daily level.

Breaker: the level that was broken. A retest of it from the other side is a Breaker reaction.

OC: two candles in the same direction; the level is where the first closed and the second opened.

H4 back in line: 4H had gone against the Daily, then broke back in the Daily direction after a fresh Daily reaction.

H4 engulfing: a 4H candle covered the previous opposite candle, in the Daily direction.

Weekly — in line / AGAINST: whether the Daily direction agrees with the Weekly reaction.

📊 View chart under an alert shows the levels on a Daily and 4H picture."""

NOT_LINKED = ("This Telegram isn't linked to a Bias Pointer account yet.\n\n"
              "Log in on the website, open Settings → Connect Telegram, and tap the link it gives you.")


_CLOSE = InlineKeyboardButton("✕ Close", callback_data="chx")


def _page_markup(base_url: str, label: str, path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, web_app=WebAppInfo(url=base_url.rstrip("/") + path))],
                                 [_CLOSE]])


def _news_markup(on: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔕 Turn news off" if on else "🔔 Turn news on",
                                                       callback_data="nw:0" if on else "nw:1")], [_CLOSE]])


async def _reply(conn, token: str, chat_id: str, text: str, markup=None) -> None:
    """Send a menu reply in place of the last one, so only one is ever in the chat."""
    key = f"menu_msg:{chat_id}"
    old = conn.execute("SELECT value FROM user_config WHERE key = ?", (key,)).fetchone()
    if old and old[0].isdigit():
        await delete_message(token, chat_id, int(old[0]))
    mid = await send_message_id(token, chat_id, text, reply_markup=markup or InlineKeyboardMarkup([[_CLOSE]]))
    if mid:
        conn.execute("INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                     (key, str(mid)))


def _news_text(on: bool) -> str:
    return ("📰 High-impact news is ON.\n\nEach morning you get the day's high-impact events for your pairs, "
            "and a reminder 30 minutes before each one." if on else
            "📰 High-impact news is OFF.\n\nTurn it on to get the day's high-impact events for your pairs "
            "each morning and a reminder 30 minutes before each one.")


def linked_user(conn, chat_id) -> dict | None:
    row = conn.execute("SELECT id, name, role FROM users WHERE telegram_chat_id = ?", (str(chat_id),)).fetchone()
    return dict(row) if row else None


async def setup_bot_menu(bot_token: str) -> None:
    """Publish the command list and show it behind the chat's Menu button."""
    bot = Bot(token=bot_token)
    try:
        await bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except TelegramError as e:
        logger.warning("Could not set the bot's command menu: %s", e)


async def handle_command(conn, config, chat: dict, text: str, message_id: int | None = None) -> bool:
    """Answer a menu command. Returns False if the text isn't one of ours
    (so /start <link token> still goes to the account-linking flow)."""
    if chat.get("type", "private") != "private":
        return False
    cmd = text.split(maxsplit=1)[0].lstrip("/").split("@")[0].lower()
    if cmd == "start" and len(text.split()) > 1:
        return False
    if cmd not in PAGES and cmd not in ("start", "news", "help"):
        return False

    token, chat_id, base = config.telegram_bot_token, str(chat["id"]), config.frontend_url
    if message_id:
        await delete_message(token, chat_id, message_id)   # the typed /command
    if cmd == "help":
        await _reply(conn, token, chat_id, HELP_TEXT)
        return True

    user = linked_user(conn, chat_id)
    if not user:
        await _reply(conn, token, chat_id, NOT_LINKED, InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔑 Log in", web_app=WebAppInfo(url=base.rstrip("/") + "/login"))], [_CLOSE]]))
        return True

    if cmd == "start":
        hi = f"Hi {user['name']}! " if user["name"] else ""
        await _reply(conn, token, chat_id,
                     f"{hi}Your alerts come to this chat.\n\nTap Menu for shortcuts, or open the Bias Pointer here:",
                     _page_markup(base, "📈 Open Bias Pointer", "/hub"))
    elif cmd == "news":
        from api.alert_prefs import get_alert_prefs
        on = get_alert_prefs(conn, user["id"], user["role"]).get("news", True)
        await _reply(conn, token, chat_id, _news_text(on), _news_markup(on))
    else:
        _, path, label, blurb = PAGES[cmd]
        await _reply(conn, token, chat_id, blurb, _page_markup(base, label, path))
    return True


async def handle_news_button(conn, config, cq: dict) -> None:
    """'Turn news on/off' under the /news reply: save the choice and update the message."""
    from api.alert_prefs import set_alert_pref
    token = config.telegram_bot_token
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    user = linked_user(conn, chat_id) if chat_id is not None else None
    if not user:
        return await answer_button(token, cq.get("id", ""), "Link your account first.")
    on = cq.get("data") == "nw:1"
    set_alert_pref(conn, user["id"], "news", on)
    try:
        await Bot(token=token).edit_message_text(chat_id=chat_id, message_id=msg.get("message_id"),
                                                 text=_news_text(on), reply_markup=_news_markup(on))
    except TelegramError:
        pass
    await answer_button(token, cq.get("id", ""), "News on" if on else "News off")
