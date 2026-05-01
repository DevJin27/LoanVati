"""Database engine and session helpers for the Phase 3 product API."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _load_backend_env() -> None:
    """Load backend/.env with python-dotenv when available, otherwise a fallback parser."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
        return
    except Exception:
        # Fallback for environments missing python-dotenv.
        pass

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_backend_env()


def get_database_url() -> str:
    """Return the required PostgreSQL URL for Phase 3."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the Phase 3 backend")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError("DATABASE_URL must point to PostgreSQL")
    return database_url


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base."""


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Yield one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
