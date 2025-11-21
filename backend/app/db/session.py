"""Helpers for creating and safely managing SQLAlchemy sessions."""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker

from .core import engine
from .models import Base

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def orm_session() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_local_db() -> None:
    """Create tables with ORM schemas if they do not exist."""
    Base.metadata.create_all(bind=engine)
