from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from api.auth import decode_token

_ALWAYS_PUBLIC = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/setup",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/forgot",      # request a reset link (sent to the account's Telegram)
    "/api/auth/reset",       # complete a reset with the one-time token
    "/api/tv-webhook",   # TradingView Pine Script webhook (uses its own secret)
    "/api/telegram/update",  # Telegram bot webhook (uses its own secret header)
    "/api/paystack/webhook", # Paystack webhook (verified by HMAC signature)
}
_PUBLIC_PREFIXES = ("/api/videos/", "/api/public/")


def _load_live_user(app, user_id: int, issued_at: int = 0):
    """Re-read the user from the DB on every request so revocation, plan
    expiry and password changes take effect immediately — not only at the
    next login. Returns (ok, role_or_detail). ok=False means reject."""
    path = app.state.config.db_path
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT role, plan, plan_expires_at, pw_changed_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    # Account no longer exists (revoked/deleted) — token must stop working now.
    if row is None:
        return False, "Account no longer exists"

    # Password changed after this token was issued — sign this session out.
    if row["pw_changed_at"] and int(issued_at or 0) < int(row["pw_changed_at"]):
        return False, "Your password was changed. Please sign in again."

    role = row["role"]
    # Owners and lifetime accounts never expire. Everyone else is enforced
    # per-request: when the plan expires, access ends immediately.
    if role != "OWNER" and row["plan"] != "LIFETIME" and row["plan_expires_at"]:
        try:
            exp = datetime.fromisoformat(row["plan_expires_at"].replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                return False, "Your subscription has expired"
        except Exception:
            # Unparseable expiry → treat as non-blocking rather than lock out.
            pass
    return True, role


async def auth_middleware(request: Request, call_next):
    # CORS preflight must always pass through
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path

    # Only gate /api/ routes
    if not path.startswith("/api/"):
        return await call_next(request)

    # Public routes — no token needed
    if path in _ALWAYS_PUBLIC or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)

    # If auth hasn't been set up yet, let everything through
    if not getattr(request.app.state, "auth_enabled", False):
        return await call_next(request)

    # Require a valid Bearer token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    payload = decode_token(auth[7:], request.app)
    if not payload:
        return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

    user_id = int(payload["sub"])

    # Re-validate against the live DB every request: enforces revocation and
    # plan expiry the moment they happen, regardless of the 60-day token life.
    ok, role_or_detail = _load_live_user(request.app, user_id, payload.get("iat", 0))
    if not ok:
        # 401 for a signed-out session (frontend sends the user to sign in);
        # 403 for revoked / expired access.
        status = 401 if role_or_detail.startswith("Your password was changed") else 403
        return JSONResponse({"detail": role_or_detail}, status_code=status)

    # Use the authoritative role from the DB, not the (possibly stale) token.
    request.state.user = {"id": user_id, "role": role_or_detail}
    return await call_next(request)
