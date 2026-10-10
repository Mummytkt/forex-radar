from __future__ import annotations

import base64
import hashlib
import secrets
import sqlite3
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
    return getattr(app.state, "jwt_secret", None) or "dev-only-secret"


def create_token(payload: dict, app) -> str:
    if not _CRYPTO_OK:
        raise RuntimeError("python-jose not installed")
    data = {**payload, "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)}
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
    with _db(request) as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash, role, plan, plan_expires_at "
            "FROM users WHERE LOWER(email) = LOWER(?)",
            (body.email.strip(),),
        ).fetchone()
    if not row or not verify_pw(body.password, row["password_hash"] or ""):
        raise HTTPException(401, "Invalid email or password")
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
    params.append(u["id"])
    with _db_write(request) as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    return {"ok": True}


@auth_router.get("/users")
def list_users(request: Request):
    require_owner(request)
    with _db(request) as conn:
        rows = conn.execute(
            "SELECT id, email, name, role, plan, plan_expires_at, invite_used, created_at, last_login_at "
            "FROM users ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


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
        conn.execute("DELETE FROM users WHERE id = ? AND role != 'OWNER'", (user_id,))
    return {"ok": True}
