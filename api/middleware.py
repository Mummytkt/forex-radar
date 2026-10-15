from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from api.auth import decode_token

_ALWAYS_PUBLIC = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/setup",
    "/api/auth/login",
    "/api/auth/register",
    "/api/tv-webhook",   # TradingView Pine Script webhook (uses its own secret)
    "/api/telegram/update",  # Telegram bot webhook (uses its own secret header)
}
_PUBLIC_PREFIXES = ("/api/videos/", "/api/public/")


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

    request.state.user = {"id": int(payload["sub"]), "role": payload["role"]}
    return await call_next(request)
