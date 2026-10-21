from __future__ import annotations

import base64
import hashlib
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

try:
    from jose import jwt, JWTError
    _CRYPTO_OK = True
except ImportError:
    _CRYPTO_OK = False

ALGORITHM = "HS256"
TOKEN_DAYS = 60
auth_router = APIRouter(prefix="/auth", tags=["auth"])


# ── DB helpers ────────────────────────────────────────────────────────────────

@contextmanager
def _db(request: Request):
    path = request.app.state.config.db_path
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def _db_write(request: Request):
    path = request.app.state.config.db_path
    conn = sqlite3.connect(path, check_same_thread=False)
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


# ── JWT ───────────────────────────────────────────────────────────────────────

def _secret(app) -> str:
    secret = getattr(app.state, "jwt_secret", None)
    if not secret:
        # Never fall back to a known value — that would let anyone forge tokens.
        raise RuntimeError("JWT secret is not configured")
    return secret


def create_token(payload: dict, app) -> str:
    if not _CRYPTO_OK:
        raise RuntimeError("python-jose not installed")
    now = datetime.now(timezone.utc)
    data = {**payload, "iat": int(now.timestamp()), "exp": now + timedelta(days=TOKEN_DAYS)}
    return jwt.encode(data, _secret(app), algorithm=ALGORITHM)


def decode_token(token: str, app) -> Optional[dict]:
    if not _CRYPTO_OK:
        return None
    try:
        return jwt.decode(token, _secret(app), algorithms=[ALGORITHM])
    except Exception:
        return None


_ITERS = 260_000


def hash_pw(p: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), _ITERS)
    return f"pbkdf2:{salt}:{base64.b64encode(h).decode()}"


def verify_pw(plain: str, stored: str) -> bool:
    try:
        _, salt, b64 = stored.split(":", 2)
        h = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), _ITERS)
        return base64.b64decode(b64) == h
    except Exception:
        return False


# ── Rate limiting (single-machine, in-memory) ─────────────────────────────────
# Throttles password guessing. Keys are "email:<addr>" and "ip:<addr>".

_HITS: dict[str, list[float]] = {}
_HITS_LOCK = threading.Lock()


def client_ip(request: Request) -> str:
    # Fly's proxy puts the real client address in Fly-Client-IP.
    return request.headers.get("fly-client-ip") or (request.client.host if request.client else "unknown")


def rate_limited(key: str, max_hits: int, window_s: int) -> bool:
    now = time.time()
    with _HITS_LOCK:
        hits = [t for t in _HITS.get(key, []) if now - t < window_s]
        _HITS[key] = hits
        return len(hits) >= max_hits


def record_hit(key: str) -> None:
    with _HITS_LOCK:
        _HITS.setdefault(key, []).append(time.time())


def clear_hits(key: str) -> None:
    with _HITS_LOCK:
        _HITS.pop(key, None)


_LOGIN_WINDOW = 15 * 60


# ── Request helpers ───────────────────────────────────────────────────────────

def get_user(request: Request) -> Optional[dict]:
    return getattr(request.state, "user", None)


def require_user(request: Request) -> dict:
    u = get_user(request)
    if not u:
        raise HTTPException(401, "Not authenticated")
    return u


def require_owner(request: Request) -> dict:
    u = require_user(request)
    if u.get("role") != "OWNER":
        raise HTTPException(403, "Owner access required")
    return u


# ── Pydantic models ───────────────────────────────────────────────────────────

class SetupBody(BaseModel):
    email: str
    name: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


class ProfileBody(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class InviteBody(BaseModel):
    email: str
    name: str = ""
    plan: str = "30DAY"
    plan_days: int = 30


class RegisterBody(BaseModel):
    token: str
    name: str
    password: str


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_router.get("/status")
def auth_status(request: Request):
    return {
        "enabled": getattr(request.app.state, "auth_enabled", False),
        "crypto_available": _CRYPTO_OK,
    }


@auth_router.post("/setup")
def setup(body: SetupBody, request: Request):
    """Create the owner account — only works when no users exist yet."""
    if not _CRYPTO_OK:
        raise HTTPException(500, "Install python-jose and passlib[bcrypt] to enable auth")
    if getattr(request.app.state, "auth_enabled", False):
        raise HTTPException(400, "Auth is already configured")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if not body.email.strip() or "@" not in body.email:
        raise HTTPException(400, "Valid email required")
    if not body.name.strip():
        raise HTTPException(400, "Name is required")

    # Generate and persist JWT secret
    secret = secrets.token_hex(32)
    request.app.state.jwt_secret = secret
    with _db_write(request) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES ('jwt_secret', ?, datetime('now'))",
            (secret,),
        )
        conn.execute(
            "INSERT INTO users (email, name, password_hash, role, plan) VALUES (LOWER(?), ?, ?, 'OWNER', 'LIFETIME')",
            (body.email.strip(), body.name.strip(), hash_pw(body.password)),
        )

    request.app.state.auth_enabled = True

    with _db(request) as conn:
        row = conn.execute(
            "SELECT id, email, name, role, plan FROM users WHERE LOWER(email) = LOWER(?)",
            (body.email.strip(),),
        ).fetchone()

    token = create_token({"sub": str(row["id"]), "role": "OWNER"}, request.app)
    with _db_write(request) as conn:
        conn.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (row["id"],))

    return {
        "token": token,
        "user": {"id": row["id"], "email": row["email"], "name": row["name"],
                 "role": row["role"], "plan": row["plan"]},
    }


@auth_router.post("/login")
def login(body: LoginBody, request: Request):
    if not _CRYPTO_OK:
        raise HTTPException(500, "Auth dependencies not installed")
    email_key = "email:" + body.email.strip().lower()
    ip_key = "ip:" + client_ip(request)
    if rate_limited(email_key, 8, _LOGIN_WINDOW) or rate_limited(ip_key, 30, _LOGIN_WINDOW):
        raise HTTPException(429, "Too many sign-in attempts. Please wait 15 minutes and try again.")
    with _db(request) as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash, role, plan, plan_expires_at "
            "FROM users WHERE LOWER(email) = LOWER(?)",
            (body.email.strip(),),
        ).fetchone()
    if not row or not verify_pw(body.password, row["password_hash"] or ""):
        record_hit(email_key)
        record_hit(ip_key)
        raise HTTPException(401, "Invalid email or password")
    clear_hits(email_key)
    if row["plan"] not in ("LIFETIME",) and row["plan_expires_at"]:
        exp = datetime.fromisoformat(row["plan_expires_at"].replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(403, "Your access has expired")
    token = create_token({"sub": str(row["id"]), "role": row["role"]}, request.app)
    with _db_write(request) as conn:
        conn.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (row["id"],))
    return {
        "token": token,
        "user": {"id": row["id"], "email": row["email"], "name": row["name"] or "",
                 "role": row["role"], "plan": row["plan"]},
    }


@auth_router.get("/me")
def me(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(auth[7:], request.app)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    with _db(request) as conn:
        row = conn.execute(
            "SELECT id, email, name, role, plan, plan_expires_at, created_at, last_login_at "
            "FROM users WHERE id = ?",
            (int(payload["sub"]),),
        ).fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)


@auth_router.put("/profile")
def update_profile(body: ProfileBody, request: Request):
    u = require_user(request)
    with _db(request) as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (u["id"],)).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    updates, params = [], []
    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name.strip())
    if body.new_password:
        if not body.current_password or not verify_pw(body.current_password, row["password_hash"] or ""):
            raise HTTPException(400, "Current password is incorrect")
        if len(body.new_password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        updates.append("password_hash = ?")
        params.append(hash_pw(body.new_password))
    if not updates:
        raise HTTPException(400, "Nothing to update")
    new_token = None
    if body.new_password:
        # Signs out every other session; this one gets a fresh token below.
        updates.append("pw_changed_at = ?")
        params.append(int(datetime.now(timezone.utc).timestamp()))
    params.append(u["id"])
    with _db_write(request) as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    if body.new_password:
        new_token = create_token({"sub": str(u["id"]), "role": u["role"]}, request.app)
    return {"ok": True, "token": new_token}


@auth_router.get("/users")
def list_users(request: Request):
    require_owner(request)
    with _db(request) as conn:
        rows = conn.execute(
            "SELECT id, email, name, role, plan, plan_expires_at, invite_used, created_at, last_login_at, "
            "telegram_chat_id, password_hash, billing_mode "
            "FROM users ORDER BY created_at ASC"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        # expose only whether Telegram is linked / a password is set — never the values
        d["telegram_linked"] = bool((d.pop("telegram_chat_id", None) or "").strip())
        d["has_password"] = bool(d.pop("password_hash", None))
        out.append(d)
    return out


# ── Password reset ────────────────────────────────────────────────────────────

class ForgotBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    password: str


def _issue_reset_token(conn, user_id: int, minutes: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    conn.execute("UPDATE users SET reset_token = ?, reset_token_expires_at = ? WHERE id = ?",
                 (token, expires, user_id))
    return token


@auth_router.post("/forgot")
async def forgot_password(body: ForgotBody, request: Request):
    """Send a one-time reset link to the account's linked Telegram. Always answers the
    same way, so nobody can use this to find out which emails have accounts."""
    email = body.email.strip().lower()
    ip_key, email_key = "forgot-ip:" + client_ip(request), "forgot-email:" + email
    if rate_limited(ip_key, 5, 900) or rate_limited(email_key, 3, 3600):
        raise HTTPException(429, "Too many reset requests. Please wait a while and try again.")
    record_hit(ip_key)
    record_hit(email_key)

    config = request.app.state.config
    with _db_write(request) as conn:
        row = conn.execute("SELECT id, name, telegram_chat_id FROM users WHERE LOWER(email) = ?",
                           (email,)).fetchone()
        token = _issue_reset_token(conn, row["id"], 30) if row and row["telegram_chat_id"] else None

    if token and config.telegram_enabled:
        from alerts.telegram import send_alert
        link = f"{config.frontend_url}/reset?token={token}"
        await send_alert(
            config.telegram_bot_token, row["telegram_chat_id"],
            "🔐 Password reset for your MummyTKT's Bias Pointer account.\n\n"
            f"Tap to choose a new password (link works once, for 30 minutes):\n{link}\n\n"
            "Didn't ask for this? Ignore this message and your password stays the same.",
        )
    return {
        "ok": True,
        "message": "If that email has an account with Telegram linked, a reset link is on its way to that Telegram.",
    }


@auth_router.post("/reset")
def reset_password(body: ResetBody, request: Request):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    with _db_write(request) as conn:
        u = conn.execute(
            "SELECT id, email, name, role, plan, reset_token_expires_at FROM users WHERE reset_token = ?",
            (body.token,)).fetchone()
        if not u:
            raise HTTPException(400, "This reset link is invalid or has already been used.")
        exp = datetime.fromisoformat(u["reset_token_expires_at"]) if u["reset_token_expires_at"] else None
        if not exp or exp < datetime.now(timezone.utc):
            conn.execute("UPDATE users SET reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?", (u["id"],))
            raise HTTPException(400, "This reset link has expired. Request a new one.")
        conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires_at = NULL, "
            "set_password_token = NULL, pw_changed_at = ?, last_login_at = datetime('now') WHERE id = ?",
            (hash_pw(body.password), int(datetime.now(timezone.utc).timestamp()), u["id"]))
    clear_hits("email:" + u["email"].lower())
    token = create_token({"sub": str(u["id"]), "role": u["role"]}, request.app)
    return {"token": token, "user": {"id": u["id"], "email": u["email"], "name": u["name"] or "",
                                     "role": u["role"], "plan": u["plan"]}}


@auth_router.post("/users/{user_id}/reset-link")
def owner_reset_link(user_id: int, request: Request):
    """Owner-only: a 24-hour one-time link to send a subscriber who can't use Telegram
    reset (no Telegram linked, or never set a password after paying)."""
    require_owner(request)
    with _db_write(request) as conn:
        u = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not u:
            raise HTTPException(404, "User not found")
        if u["role"] == "OWNER":
            raise HTTPException(400, "Use Change password on your own account")
        token = _issue_reset_token(conn, user_id, 24 * 60)
    return {"link": f"{request.app.state.config.frontend_url}/reset?token={token}"}


@auth_router.post("/invite")
def create_invite(body: InviteBody, request: Request):
    require_owner(request)
    if not body.email.strip() or "@" not in body.email:
        raise HTTPException(400, "Valid email required")
    token = secrets.token_urlsafe(32)
    expires = None if body.plan == "LIFETIME" else (
        datetime.now(timezone.utc) + timedelta(days=body.plan_days)
    ).isoformat()
    with _db_write(request) as conn:
        try:
            conn.execute(
                "INSERT INTO users (email, name, role, plan, plan_expires_at, invite_token, invite_used) "
                "VALUES (LOWER(?), ?, 'SUBSCRIBER', ?, ?, ?, 0)",
                (body.email.strip(), body.name.strip(), body.plan, expires, token),
            )
        except Exception:
            raise HTTPException(400, "That email address already has an account")
    return {"token": token}


@auth_router.post("/register")
def register(body: RegisterBody, request: Request):
    if not _CRYPTO_OK:
        raise HTTPException(500, "Auth dependencies not installed")
    with _db(request) as conn:
        row = conn.execute(
            "SELECT id, invite_used FROM users WHERE invite_token = ?", (body.token,)
        ).fetchone()
    if not row:
        raise HTTPException(400, "Invalid or expired invite link")
    if row["invite_used"]:
        raise HTTPException(400, "This invite has already been used")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if not body.name.strip():
        raise HTTPException(400, "Name is required")
    with _db_write(request) as conn:
        conn.execute(
            "UPDATE users SET name = ?, password_hash = ?, invite_used = 1, invite_token = NULL WHERE id = ?",
            (body.name.strip(), hash_pw(body.password), row["id"]),
        )
        # The plan's days count from sign-up, not from when the invite was made
        u = conn.execute("SELECT plan_expires_at, created_at FROM users WHERE id = ?", (row["id"],)).fetchone()
        try:
            if u and u["plan_expires_at"] and u["created_at"]:
                exp = datetime.fromisoformat(str(u["plan_expires_at"]).replace("Z", "+00:00"))
                made = datetime.fromisoformat(str(u["created_at"]).replace("Z", "+00:00"))
                exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
                made = made if made.tzinfo else made.replace(tzinfo=timezone.utc)
                new_exp = datetime.now(timezone.utc) + (exp - made)
                if new_exp > exp:
                    conn.execute("UPDATE users SET plan_expires_at = ? WHERE id = ?", (new_exp.isoformat(), row["id"]))
        except Exception:
            pass   # keep the original expiry rather than fail sign-up
    with _db(request) as conn:
        row2 = conn.execute(
            "SELECT id, email, name, role, plan FROM users WHERE id = ?", (row["id"],)
        ).fetchone()
    token = create_token({"sub": str(row2["id"]), "role": row2["role"]}, request.app)
    with _db_write(request) as conn:
        conn.execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (row2["id"],))
    return {"token": token, "user": dict(row2)}


@auth_router.delete("/users/{user_id}")
def revoke_user(user_id: int, request: Request):
    owner = require_owner(request)
    if owner["id"] == user_id:
        raise HTTPException(400, "Cannot revoke your own access")
    with _db_write(request) as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ? AND role != 'OWNER'", (user_id,))
        if cur.rowcount:
            # Stop anything the revoked user set up from continuing to run.
            conn.execute("UPDATE price_alerts SET is_active = 0 WHERE user_id = ?", (user_id,))
            conn.execute("UPDATE entry_pattern_alerts SET is_active = 0 WHERE user_id = ?", (user_id,))
    return {"ok": True}
