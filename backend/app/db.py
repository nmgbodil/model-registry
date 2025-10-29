"""docstring for backend/app/db.py."""

# app/db.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Final, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


_engine: Final = create_engine(
    settings.DATABASE_URL,
    future=True,
    echo=False,
)

SessionLocal: Final = sessionmaker(
    bind=_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)

# Keep this alias for places that import `engine`
engine = _engine


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a SQLAlchemy Session with commit/rollback handling."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = ["Base", "engine", "get_session"]
