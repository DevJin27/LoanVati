"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.routes import limiter, router

app = FastAPI(title="Credit Risk AI API", version="2.0.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.include_router(router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):  # type: ignore[override]
    """Return a stable 429 response when the limiter is exceeded."""
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
