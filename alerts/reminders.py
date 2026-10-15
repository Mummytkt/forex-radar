"""
Subscription reminders sent to each subscriber's own Telegram (runs every 6 hours).

  • 3 days before a paid plan ends with auto-renew off  → "your access ends on …"
  • 3 days before an auto-renew / trial charge           → "your card will be charged …"
  • once, when access has just ended                     → "renew any time"

Each notice is recorded in notices_sent keyed to the date it refers to, so every
event produces exactly one message, however often the job runs. Owners and
lifetime members are never messaged. Charge receipts and failed-charge notices
are sent from the billing cycle via notify_once().
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

LEAD = timedelta(days=3)
EXPIRED_GRACE = timedelta(days=2)   # only tell people whose access ended recently


def _parse(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def fmt_day(d: datetime) -> str:
    return d.strftime("%a %d %b %Y")


def claim_notice(conn, key: str) -> bool:
    """Record a notice as sent. True only the first time for this key."""
    cur = conn.execute("INSERT OR IGNORE INTO notices_sent (key, sent_at) VALUES (?, ?)",
                       (key, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return cur.rowcount == 1


async def notify_once(conn, config, key: str, chat_id: Optional[str], text: str) -> bool:
    """Send text to chat_id unless a notice with this key was already sent."""
    if not (chat_id and config.telegram_enabled and config.telegram_bot_token):
        return False
    if not claim_notice(conn, key):
        return False
    from alerts.telegram import send_alert
    ok = await send_alert(config.telegram_bot_token, chat_id, text)
    if not ok:  # let a later run try again
        conn.execute("DELETE FROM notices_sent WHERE key = ?", (key,))
        conn.commit()
    return ok


async def run_reminders(db_path: str, config) -> None:
    from api.billing import PLANS

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    now = datetime.now(timezone.utc)
    base = config.frontend_url
    sent = 0
    try:
        users = conn.execute(
            "SELECT id, name, plan, plan_expires_at, billing_mode, paystack_auth_code, renew_plan, "
            "renew_amount, next_charge_at, telegram_chat_id FROM users "
            "WHERE role != 'OWNER' AND plan != 'LIFETIME' "
            "AND telegram_chat_id IS NOT NULL AND telegram_chat_id != ''"
        ).fetchall()
        for u in users:
            chat = u["telegram_chat_id"]
            first = (u["name"] or "").split(" ")[0]
            hi = f"Hi {first}, " if first else "Hi, "
            expires = _parse(u["plan_expires_at"])
            auto = u["billing_mode"] == "auto" and bool(u["paystack_auth_code"])

            # Upcoming automatic charge (includes the end of a free trial). The charge is
            # due when the plan ends; keyed to that date so retries after a declined card
            # (which move next_charge_at forward daily) never repeat this message.
            if auto and expires and now < expires <= now + LEAD:
                charge_at = expires
                amount = u["renew_amount"] or PLANS.get(u["renew_plan"] or "30DAY", {}).get("usd", 10)
                label = PLANS.get(u["renew_plan"] or "30DAY", {}).get("label", "your plan")
                if u["plan"] == "TRIAL":
                    text = (f"{hi}your free trial of MummyTKT's Bias Pointer ends on {fmt_day(charge_at)}.\n\n"
                            f"Your card will then be charged ${amount:g} for {label}, and every period after that, "
                            "so you keep getting your bias alerts.\n\n"
                            f"Not continuing? Turn off auto-renew before then: {base}/account")
                else:
                    text = (f"{hi}a heads-up: your card will be charged ${amount:g} on {fmt_day(charge_at)} "
                            f"to renew {label}.\n\nNothing to do if you're staying. "
                            f"To stop renewing, turn off auto-renew: {base}/account")
                if await notify_once(conn, config, f"charge3:{u['id']}:{u['plan_expires_at']}", chat, text):
                    sent += 1
                continue

            # Access ending soon with no auto-renew
            if expires and not auto and now < expires <= now + LEAD:
                plan = u["plan"] if u["plan"] in PLANS and u["plan"] != "TRIAL" else "30DAY"
                text = (f"{hi}your MummyTKT's Bias Pointer access ends on {fmt_day(expires)}.\n\n"
                        f"Renew to keep your bias alerts coming: {base}/checkout?plan={plan}")
                if await notify_once(conn, config, f"expiry3:{u['id']}:{u['plan_expires_at']}", chat, text):
                    sent += 1
                continue

            # Access just ended
            if expires and expires <= now and now - expires <= EXPIRED_GRACE:
                text = (f"{hi}your MummyTKT's Bias Pointer access has ended, so bias alerts have stopped.\n\n"
                        f"You can come back any time: {base}/checkout")
                if await notify_once(conn, config, f"expired:{u['id']}:{u['plan_expires_at']}", chat, text):
                    sent += 1
    except Exception as exc:
        logger.exception("Reminder run failed: %s", exc)
    finally:
        conn.close()
    if sent:
        logger.info("Sent %d subscription reminder(s)", sent)
