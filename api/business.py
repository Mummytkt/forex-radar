"""
Owner-only Business dashboard data: subscribers, revenue, churn and affiliate payouts.

All amounts are USD as charged (payments.amount_usd). Free-trial card checks are
refunded, so trial payments are excluded from revenue.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_owner

router = APIRouter()


@contextmanager
def _db(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _parse(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


@router.get("/admin/business")
def business_overview(request: Request):
    require_owner(request)
    now = datetime.now(timezone.utc)
    d30, d7 = now - timedelta(days=30), now + timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    with _db(request) as conn:
        users = conn.execute(
            "SELECT id, name, email, plan, plan_expires_at, billing_mode, paystack_auth_code, created_at, "
            "telegram_chat_id, auto_renew_cancelled_at FROM users WHERE role != 'OWNER'"
        ).fetchall()
        payments = conn.execute(
            "SELECT plan, amount_usd, paid_at FROM payments WHERE status = 'paid' AND trial = 0 AND paid_at IS NOT NULL"
        ).fetchall()
        affiliates = conn.execute(
            "SELECT a.id, a.code, a.paid_customers, u.name, u.email FROM affiliates a "
            "LEFT JOIN users u ON u.id = a.user_id ORDER BY a.created_at"
        ).fetchall()
        comm = conn.execute(
            "SELECT affiliate_id, status, amount_usd FROM commissions"
        ).fetchall()

    def active(u):
        exp = _parse(u["plan_expires_at"])
        return u["plan"] == "LIFETIME" or exp is None or exp > now

    act = [u for u in users if active(u)]
    by_plan: dict[str, int] = {}
    for u in act:
        by_plan[u["plan"]] = by_plan.get(u["plan"], 0) + 1
    auto_on = [u for u in act if u["billing_mode"] == "auto" and u["paystack_auth_code"]]
    auto_ids = {u["id"] for u in auto_on}
    expiring = sorted(
        ({"name": u["name"] or "", "email": u["email"], "plan": u["plan"], "plan_expires_at": u["plan_expires_at"],
          "auto_renew": u["id"] in auto_ids}
         for u in act if u["plan"] != "LIFETIME" and _parse(u["plan_expires_at"]) and _parse(u["plan_expires_at"]) <= d7),
        key=lambda x: x["plan_expires_at"])
    expired_30 = [u for u in users if not active(u) and _parse(u["plan_expires_at"]) and _parse(u["plan_expires_at"]) >= d30]
    cancelled_30 = [u for u in users if _parse(u["auto_renew_cancelled_at"]) and _parse(u["auto_renew_cancelled_at"]) >= d30]
    new_30 = [u for u in users if _parse(u["created_at"]) and _parse(u["created_at"]) >= d30]

    def paid(p):
        return _parse(p["paid_at"])

    rev_month = sum(p["amount_usd"] for p in payments if paid(p) and paid(p) >= month_start)
    rev_30 = sum(p["amount_usd"] for p in payments if paid(p) and paid(p) >= d30)
    rev_all = sum(p["amount_usd"] for p in payments)

    # Last 6 calendar months (oldest first)
    months = []
    y, m = now.year, now.month
    for _ in range(6):
        months.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    months.reverse()
    monthly = []
    for (yy, mm) in months:
        total = sum(p["amount_usd"] for p in payments if paid(p) and paid(p).year == yy and paid(p).month == mm)
        monthly.append({"month": f"{yy}-{mm:02d}", "revenue_usd": round(total, 2)})

    aff_rows = []
    for a in affiliates:
        mine = [c for c in comm if c["affiliate_id"] == a["id"]]
        tot = lambda st: round(sum(c["amount_usd"] for c in mine if c["status"] == st), 2)
        aff_rows.append({
            "id": a["id"], "name": a["name"] or "", "email": a["email"] or "", "code": a["code"],
            "paid_customers": a["paid_customers"],
            "pending_usd": tot("pending"), "available_usd": tot("available"), "paid_usd": tot("paid"),
        })

    return {
        "subscribers": {
            "active": len(act),
            "by_plan": by_plan,
            "auto_renew_on": len(auto_on),
            "telegram_linked": sum(1 for u in act if (u["telegram_chat_id"] or "").strip()),
            "new_30d": len(new_30),
            "expired_30d": len(expired_30),
            "cancelled_auto_renew_30d": len(cancelled_30),
            "expiring_7d": expiring,
        },
        "revenue": {
            "this_month_usd": round(rev_month, 2),
            "last_30d_usd": round(rev_30, 2),
            "all_time_usd": round(rev_all, 2),
            "payments_all_time": len(payments),
            "monthly": monthly,
        },
        "affiliates": aff_rows,
        "commissions_owed_usd": round(sum(r["available_usd"] for r in aff_rows), 2),
    }


class MarkPaidBody(BaseModel):
    affiliate_id: int


@router.post("/admin/commissions/mark-paid")
def mark_commissions_paid(body: MarkPaidBody, request: Request):
    """Owner records that they've paid an affiliate everything currently available."""
    require_owner(request)
    with _db(request) as conn:
        if not conn.execute("SELECT 1 FROM affiliates WHERE id = ?", (body.affiliate_id,)).fetchone():
            raise HTTPException(404, "Affiliate not found")
        cur = conn.execute(
            "UPDATE commissions SET status = 'paid', paid_at = ? WHERE affiliate_id = ? AND status = 'available'",
            (datetime.now(timezone.utc).isoformat(), body.affiliate_id))
    return {"ok": True, "marked": cur.rowcount}
