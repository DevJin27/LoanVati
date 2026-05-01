"""FastAPI application entry point."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.auth import router as auth_router
from src.api.product_routes import router as product_router
from src.api.routes import limiter, router

app = FastAPI(title="LoanVati Phase 3 API", version="3.0.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(product_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):  # type: ignore[override]
    """Return a stable 429 response when the limiter is exceeded."""
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
