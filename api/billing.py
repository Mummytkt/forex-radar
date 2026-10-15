"""
Paystack checkout + auto-provisioning + affiliate programme.

Public (no-auth) routes:
  POST /api/public/checkout          — start a Paystack transaction, returns authorization_url
  GET  /api/public/checkout/verify   — success-page verification + set-password token
  POST /api/public/set-password      — set a password after checkout, returns a JWT
  POST /api/paystack/webhook         — Paystack charge.success → provision + credit affiliate

Authenticated routes:
  GET  /api/affiliate                — affiliate status, link, code, earnings
  POST /api/affiliate/join           — join the programme (generates link + code)
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from api.auth import hash_pw, create_token, client_ip, rate_limited, record_hit
from api import paystack
from api.exchange_rate import get_ngn_rate

logger = logging.getLogger(__name__)
router = APIRouter()

# plan → price (USD) + access length (days). TRIAL = 7 days free then monthly $10.
PLANS: dict[str, dict] = {
    "30DAY":  {"label": "30 Days",   "usd": 10, "days": 30},
    "6MONTH": {"label": "6 Months",  "usd": 48, "days": 182},
    "9MONTH": {"label": "9 Months",  "usd": 63, "days": 273},
    "12MONTH":{"label": "12 Months", "usd": 72, "days": 365},
    "TRIAL":  {"label": "7-Day Free Trial", "usd": 10, "days": 7, "renew_plan": "30DAY"},
}

_COMMISSION_TIER1 = 0.10   # first 10 paying customers
_COMMISSION_TIER2 = 0.15   # 11th onward
_PAYOUT_DELAY_DAYS = 7


@contextmanager
def _db_write(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _uid(request: Request) -> Optional[int]:
    u = getattr(request.state, "user", None)
    return u["id"] if u else None


# ── Provisioning + affiliate crediting (shared by webhook + verify fallback) ──

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def link_and_maybe_credit(conn, pay: sqlite3.Row, customer_uid: int, credit: bool) -> None:
    """Attribute a referral (always) and create a commission (only on real,
    non-refunded charges). Shared by checkout provisioning and renewals."""
    code = (pay["referral_code"] or "").strip().upper()
    if not code:
        return
    aff = conn.execute("SELECT id, user_id, paid_customers FROM affiliates WHERE code = ?", (code,)).fetchone()
    if not aff or aff["user_id"] == customer_uid:
        return
    conn.execute("UPDATE users SET referred_by = ? WHERE id = ? AND referred_by IS NULL", (aff["user_id"], customer_uid))
    if not credit:
        return
    prior = conn.execute(
        "SELECT COUNT(*) FROM commissions WHERE affiliate_id = ? AND customer_email = ?",
        (aff["id"], pay["email"].lower()),
    ).fetchone()[0]
    rate = _COMMISSION_TIER1 if aff["paid_customers"] < 10 else _COMMISSION_TIER2
    amount = round(rate * pay["amount_usd"], 2)
    available = (datetime.now(timezone.utc) + timedelta(days=_PAYOUT_DELAY_DAYS)).isoformat()
    conn.execute(
        "INSERT INTO commissions (affiliate_id, payment_id, customer_email, rate, amount_usd, status, available_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (aff["id"], pay["id"], pay["email"].lower(), rate, amount, available),
    )
    if prior == 0:
        conn.execute("UPDATE affiliates SET paid_customers = paid_customers + 1 WHERE id = ?", (aff["id"],))


def _provision(conn, pay: sqlite3.Row, authorization: Optional[dict], customer_code: Optional[str]) -> Optional[str]:
    """Create or extend the subscriber account for a paid payment. Returns a
    set-password token when a brand-new account was created, else None."""
    email = pay["email"].lower()
    now = datetime.now(timezone.utc)
    days = pay["duration_days"]
    billing = pay["billing_mode"]

    existing = conn.execute("SELECT id, plan_expires_at FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
    set_token: Optional[str] = None

    if existing:
        uid = existing["id"]
        base = max(now, _parse_dt(existing["plan_expires_at"]) or now)
        new_exp = base + timedelta(days=days)
        conn.execute("UPDATE users SET plan = ?, plan_expires_at = ? WHERE id = ?",
                     (pay["plan"], new_exp.isoformat(), uid))
    else:
        set_token = secrets.token_urlsafe(24)
        new_exp = now + timedelta(days=days)
        conn.execute(
            "INSERT INTO users (email, name, role, plan, plan_expires_at, set_password_token) "
            "VALUES (LOWER(?), ?, 'SUBSCRIBER', ?, ?, ?)",
            (email, pay["name"] or "", pay["plan"], new_exp.isoformat(), set_token),
        )
        uid = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,)).fetchone()["id"]

    # Save the card + schedule renewal / trial charge
    if authorization and billing in ("auto", "trial"):
        plan_def = PLANS.get(pay["plan"], {})
        if billing == "trial":
            renew_plan = plan_def.get("renew_plan", "30DAY")
            renew_amount = PLANS[renew_plan]["usd"]
            next_charge = now + timedelta(days=7)
        else:
            renew_plan = pay["plan"]
            renew_amount = pay["amount_usd"]
            next_charge = new_exp
        conn.execute(
            "UPDATE users SET paystack_auth_code = ?, paystack_customer_code = ?, billing_mode = 'auto', "
            "renew_plan = ?, renew_amount = ?, next_charge_at = ? WHERE id = ?",
            (authorization.get("authorization_code"), customer_code, renew_plan, renew_amount, next_charge.isoformat(), uid),
        )

    conn.execute("UPDATE payments SET status = 'paid', user_id = ?, paid_at = ? WHERE id = ?",
                 (uid, now.isoformat(), pay["id"]))

    # Always attribute the referral; commission only on real (non-trial) charges
    link_and_maybe_credit(conn, pay, uid, credit=not pay["trial"])
    return set_token


# ── Checkout ──────────────────────────────────────────────────────────────────

class CheckoutBody(BaseModel):
    plan: str
    name: str
    email: str
    billing: str = "once"            # 'once' | 'auto'
    referral_code: Optional[str] = None


@router.post("/public/checkout")
async def start_checkout(body: CheckoutBody, request: Request):
    config = request.app.state.config
    if not config.paystack_secret_key:
        raise HTTPException(503, "Payments are not configured yet.")
    ip_key = "checkout:" + client_ip(request)
    if rate_limited(ip_key, 20, 3600):
        raise HTTPException(429, "Too many checkout attempts. Please try again later.")
    record_hit(ip_key)
    plan = PLANS.get(body.plan.upper())
    if not plan:
        raise HTTPException(400, "Unknown plan.")
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "A valid email is required.")

    trial = body.plan.upper() == "TRIAL"
    if trial:
        # One free trial per email: no trial for existing accounts or repeat trials.
        with _db_write(request) as conn:
            has_account = conn.execute(
                "SELECT 1 FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
            had_trial = conn.execute(
                "SELECT 1 FROM payments WHERE LOWER(email) = ? AND trial = 1 AND status = 'paid'",
                (email,)).fetchone()
        if has_account or had_trial:
            raise HTTPException(400, "The free trial is for new members only. Please choose a plan.")
    billing = "trial" if trial else ("auto" if body.billing == "auto" else "once")
    usd = plan["usd"]
    reference = "mbp_" + secrets.token_hex(12)

    # Convert USD to the correct subunit amount for the charge currency
    if config.paystack_currency == "NGN":
        ngn_rate = await asyncio.to_thread(get_ngn_rate, config)
        amount_subunits = round(usd * ngn_rate * 100)  # kobo
    else:
        amount_subunits = round(usd * 100)  # cents

    with _db_write(request) as conn:
        conn.execute(
            "INSERT INTO payments (reference, email, name, plan, billing_mode, amount_usd, currency, "
            "duration_days, trial, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (reference, email, body.name.strip(), body.plan.upper(), billing, usd, config.paystack_currency,
             plan["days"], 1 if trial else 0, (body.referral_code or "").strip().upper() or None),
        )

    try:
        data = await asyncio.to_thread(
            paystack.initialize_transaction,
            config.paystack_secret_key,
            email=email,
            amount_subunits=amount_subunits,
            currency=config.paystack_currency,
            reference=reference,
            callback_url=f"{config.frontend_url}/checkout/success?reference={reference}",
            metadata={"plan": body.plan.upper(), "billing": billing, "trial": trial, "name": body.name.strip(), "usd_amount": usd},
            channels=["card", "bank", "ussd", "bank_transfer"],
        )
    except paystack.PaystackError as e:
        raise HTTPException(502, f"Could not start checkout: {e}")

    return {"authorization_url": data["authorization_url"], "reference": reference}


async def _process_paid(request: Request, reference: str, data: dict) -> None:
    """Apply a successful charge: refund trial token, provision, credit affiliate."""
    config = request.app.state.config
    authorization = data.get("authorization") or {}
    customer_code = (data.get("customer") or {}).get("customer_code")

    with _db_write(request) as conn:
        pay = conn.execute("SELECT * FROM payments WHERE reference = ?", (reference,)).fetchone()
        if not pay or pay["status"] == "paid":
            return
        is_trial = bool(pay["trial"])

    if is_trial:
        # Make the 7-day trial genuinely free: refund the tokenisation charge.
        try:
            await asyncio.to_thread(paystack.refund, config.paystack_secret_key, reference)
        except paystack.PaystackError as e:
            logger.warning("Trial refund failed for %s: %s", reference, e)

    with _db_write(request) as conn:
        pay = conn.execute("SELECT * FROM payments WHERE reference = ?", (reference,)).fetchone()
        if pay and pay["status"] != "paid":
            _provision(conn, pay, authorization, customer_code)


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    config = request.app.state.config
    raw = await request.body()
    sig = request.headers.get("x-paystack-signature", "")
    if not paystack.verify_webhook_signature(config.paystack_secret_key, raw, sig):
        raise HTTPException(401, "bad signature")
    try:
        event = json.loads(raw)
    except Exception:
        return {"status": "ignored"}
    if event.get("event") == "charge.success":
        data = event.get("data", {})
        ref = data.get("reference")
        if ref:
            await _process_paid(request, ref, data)
    return {"status": "ok"}


@router.get("/public/checkout/verify")
async def verify_checkout(reference: str, request: Request):
    """Success page calls this. Verifies with Paystack as a fallback to the
    webhook, then returns status + a set-password token for new accounts."""
    config = request.app.state.config
    with _db_write(request) as conn:
        pay = conn.execute("SELECT * FROM payments WHERE reference = ?", (reference,)).fetchone()
    if not pay:
        raise HTTPException(404, "Unknown reference.")

    if pay["status"] != "paid":
        try:
            data = await asyncio.to_thread(paystack.verify_transaction, config.paystack_secret_key, reference)
            if data.get("status") == "success":
                await _process_paid(request, reference, data)
        except paystack.PaystackError as e:
            logger.warning("verify failed for %s: %s", reference, e)

    with _db_write(request) as conn:
        pay = conn.execute("SELECT * FROM payments WHERE reference = ?", (reference,)).fetchone()
        user = None
        if pay["user_id"]:
            user = conn.execute("SELECT id, email, password_hash, set_password_token FROM users WHERE id = ?",
                                (pay["user_id"],)).fetchone()
    needs_pw = bool(user and not user["password_hash"] and user["set_password_token"])
    return {
        "status": pay["status"],
        "email": pay["email"],
        "plan": PLANS.get(pay["plan"], {}).get("label", pay["plan"]),
        "trial": bool(pay["trial"]),
        "set_password_token": user["set_password_token"] if needs_pw else None,
    }


class SetPwBody(BaseModel):
    token: str
    password: str


@router.post("/public/set-password")
def set_password(body: SetPwBody, request: Request):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    with _db_write(request) as conn:
        u = conn.execute("SELECT id, email, name, role, plan FROM users WHERE set_password_token = ?",
                         (body.token,)).fetchone()
        if not u:
            raise HTTPException(400, "This link has expired. Please sign in or reset your password.")
        conn.execute("UPDATE users SET password_hash = ?, set_password_token = NULL, last_login_at = datetime('now') WHERE id = ?",
                     (hash_pw(body.password), u["id"]))
    token = create_token({"sub": str(u["id"]), "role": u["role"]}, request.app)
    return {"token": token, "user": {"id": u["id"], "email": u["email"], "name": u["name"] or "", "role": u["role"], "plan": u["plan"]}}


# ── Affiliate programme ─────────────────────────────────────────────────────────

def _mask_email(email: str) -> str:
    """Affiliates see that a referral paid, not who: jo***@gmail.com."""
    local, _, domain = (email or "").partition("@")
    if not domain:
        return "***"
    return f"{local[:2]}***@{domain}"


def _affiliate_payload(conn, request: Request, aff: sqlite3.Row) -> dict:
    base = request.app.state.config.frontend_url
    rows = conn.execute(
        "SELECT status, amount_usd FROM commissions WHERE affiliate_id = ?", (aff["id"],)
    ).fetchall()
    now = datetime.now(timezone.utc)
    pending = available = paid = lifetime = 0.0
    for r in rows:
        lifetime += r["amount_usd"]
        if r["status"] == "paid":
            paid += r["amount_usd"]
        elif r["status"] == "available":
            available += r["amount_usd"]
        else:
            pending += r["amount_usd"]
    recent = conn.execute(
        "SELECT customer_email, rate, amount_usd, status, created_at FROM commissions "
        "WHERE affiliate_id = ? ORDER BY created_at DESC LIMIT 20", (aff["id"],)
    ).fetchall()
    return {
        "joined": True,
        "code": aff["code"],
        "link": f"{base}/checkout?ref={aff['code']}",
        "paid_customers": aff["paid_customers"],
        "next_rate": _COMMISSION_TIER1 if aff["paid_customers"] < 10 else _COMMISSION_TIER2,
        "totals": {
            "pending": round(pending, 2), "available": round(available, 2),
            "paid": round(paid, 2), "lifetime": round(lifetime, 2),
        },
        "recent": [{**dict(r), "customer_email": _mask_email(r["customer_email"])} for r in recent],
    }


@router.get("/affiliate")
def get_affiliate(request: Request):
    uid = _uid(request)
    if not uid:
        raise HTTPException(401, "Not authenticated")
    with _db_write(request) as conn:
        aff = conn.execute("SELECT * FROM affiliates WHERE user_id = ?", (uid,)).fetchone()
        if not aff:
            return {"joined": False}
        return _affiliate_payload(conn, request, aff)


@router.post("/affiliate/join")
def join_affiliate(request: Request):
    uid = _uid(request)
    if not uid:
        raise HTTPException(401, "Not authenticated")
    with _db_write(request) as conn:
        aff = conn.execute("SELECT * FROM affiliates WHERE user_id = ?", (uid,)).fetchone()
        if not aff:
            # unique, friendly code: MBP + 6 hex
            for _ in range(5):
                code = "MBP" + secrets.token_hex(3).upper()
                if not conn.execute("SELECT 1 FROM affiliates WHERE code = ?", (code,)).fetchone():
                    break
            conn.execute("INSERT INTO affiliates (user_id, code) VALUES (?, ?)", (uid, code))
            aff = conn.execute("SELECT * FROM affiliates WHERE user_id = ?", (uid,)).fetchone()
        return _affiliate_payload(conn, request, aff)
