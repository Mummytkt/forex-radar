"""
Scheduled billing cycle (runs every 6 hours):

  1. Charge due subscriptions — users with billing_mode='auto', a saved card
     and next_charge_at <= now. This also fires the 7-day trial's first real
     charge. Success → extend access, schedule the next charge, credit the
     referring affiliate. Failure → retry on the next cycle.
  2. Release commissions — flip 'pending' commissions to 'available' once their
     7-day hold (available_at) has passed.

Opens its own SQLite connection (WAL-safe). Paystack calls run in a thread.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta

from api import paystack
from api.billing import PLANS, link_and_maybe_credit

logger = logging.getLogger(__name__)


def _parse(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def run_billing_cycle(db_path: str, config) -> None:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    try:
        # ── 1. Release matured commissions ──────────────────────────────────
        conn.execute(
            "UPDATE commissions SET status = 'available' "
            "WHERE status = 'pending' AND available_at IS NOT NULL AND available_at <= ?",
            (now_iso,),
        )
        conn.commit()

        if not config.paystack_secret_key:
            return

        # ── 2. Charge due subscriptions / trial first charges ───────────────
        due = conn.execute(
            "SELECT id, email, name, renew_plan, renew_amount, paystack_auth_code, referred_by "
            "FROM users WHERE billing_mode = 'auto' AND paystack_auth_code IS NOT NULL "
            "AND next_charge_at IS NOT NULL AND next_charge_at <= ?",
            (now_iso,),
        ).fetchall()

        for u in due:
            plan = PLANS.get(u["renew_plan"] or "30DAY", PLANS["30DAY"])
            amount = u["renew_amount"] or plan["usd"]
            days = plan["days"]
            reference = "mbp_" + secrets.token_hex(12)

            # the affiliate code that referred this customer (for renewal commission)
            ref_code = None
            if u["referred_by"]:
                arow = conn.execute("SELECT code FROM affiliates WHERE user_id = ?", (u["referred_by"],)).fetchone()
                ref_code = arow["code"] if arow else None

            conn.execute(
                "INSERT INTO payments (reference, email, name, plan, billing_mode, amount_usd, currency, "
                "duration_days, trial, referral_code, status) VALUES (?, ?, ?, ?, 'auto', ?, ?, ?, 0, ?, 'pending')",
                (reference, u["email"], u["name"] or "", u["renew_plan"] or "30DAY", amount,
                 config.paystack_currency, days, ref_code),
            )
            conn.commit()

            if config.paystack_currency == "NGN":
                charge_subunits = round(amount * config.paystack_ngn_rate * 100)
            else:
                charge_subunits = round(amount * 100)

            try:
                data = await asyncio.to_thread(
                    paystack.charge_authorization,
                    config.paystack_secret_key,
                    email=u["email"],
                    amount_subunits=charge_subunits,
                    currency=config.paystack_currency,
                    authorization_code=u["paystack_auth_code"],
                    reference=reference,
                    metadata={"renewal": True, "plan": u["renew_plan"], "usd_amount": amount},
                )
            except paystack.PaystackError as e:
                logger.warning("Renewal charge failed for %s: %s", u["email"], e)
                conn.execute("UPDATE payments SET status = 'failed' WHERE reference = ?", (reference,))
                # retry on the next cycle
                conn.execute("UPDATE users SET next_charge_at = ? WHERE id = ?",
                             (( now + timedelta(days=1)).isoformat(), u["id"]))
                conn.commit()
                continue

            if data.get("status") == "success":
                base = max(now, _parse(_current_expiry(conn, u["id"])) or now)
                new_exp = base + timedelta(days=days)
                conn.execute(
                    "UPDATE users SET plan = ?, plan_expires_at = ?, next_charge_at = ? WHERE id = ?",
                    (u["renew_plan"] or "30DAY", new_exp.isoformat(), new_exp.isoformat(), u["id"]),
                )
                conn.execute("UPDATE payments SET status = 'paid', user_id = ?, paid_at = ? WHERE reference = ?",
                             (u["id"], now_iso, reference))
                pay = conn.execute("SELECT * FROM payments WHERE reference = ?", (reference,)).fetchone()
                link_and_maybe_credit(conn, pay, u["id"], credit=True)
                conn.commit()
                logger.info("Renewed %s on %s (+%d days)", u["email"], u["renew_plan"], days)
            else:
                conn.execute("UPDATE payments SET status = 'failed' WHERE reference = ?", (reference,))
                conn.execute("UPDATE users SET next_charge_at = ? WHERE id = ?",
                             ((now + timedelta(days=1)).isoformat(), u["id"]))
                conn.commit()

    except Exception as exc:
        logger.exception("Billing cycle failed: %s", exc)
    finally:
        conn.close()


def _current_expiry(conn, uid: int):
    row = conn.execute("SELECT plan_expires_at FROM users WHERE id = ?", (uid,)).fetchone()
    return row["plan_expires_at"] if row else None
