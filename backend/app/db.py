"""
SQLite-Anbindung (SQLAlchemy 2.0, sync Engine + Sessions).

Die Engine ist bewusst synchron gehalten — Zugriffe laufen über
``asyncio.to_thread`` im Event-Loop. Bei sehr vielen Findings kann später auf
``aiosqlite`` + async Session umgestellt werden.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base


def _ensure_parent(path: str) -> None:
    parent = Path(path).parent
    if str(parent) and not parent.exists():
        os.makedirs(parent, exist_ok=True)


_ensure_parent(settings.database_path)

engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Legt alle Tabellen an (idempotent)."""
    Base.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI-Dependency für eine Session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
