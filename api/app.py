from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.routes import router
from api.auth import auth_router
from api.middleware import auth_middleware
from api.tv_webhook import router as tv_webhook_router

app = FastAPI(title="MummyTKT's Bias Pointer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(tv_webhook_router, prefix="/api")
