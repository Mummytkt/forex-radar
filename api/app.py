import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.routes import router
from api.auth import auth_router
from api.middleware import auth_middleware
from api.tv_webhook import router as tv_webhook_router
from api.billing import router as billing_router
from api.business import router as business_router
from api.announcements import router as announcements_router
from api.entry_tests import router as entry_tests_router

app = FastAPI(title="MummyTKT's Bias Pointer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)


async def _time_webhooks(request, call_next):
    """TradingView gives up on a webhook after a few seconds: log any that are slow."""
    if request.url.path != "/api/tv-webhook":
        return await call_next(request)
    t0 = time.monotonic()
    response = await call_next(request)
    ms = (time.monotonic() - t0) * 1000
    if ms > 1000:
        logging.getLogger("api.tv_webhook").warning("TV webhook took %.0f ms to answer", ms)
    return response


app.add_middleware(BaseHTTPMiddleware, dispatch=_time_webhooks)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(tv_webhook_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(business_router, prefix="/api")
app.include_router(announcements_router, prefix="/api")
app.include_router(entry_tests_router, prefix="/api")
