"""backend/app/models.py` defines the database models for the application."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Typed SQLAlchemy declarative base."""

    pass


class Artifact(Base):
    """Artifact metadata persisted in the database."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str]
    stored_path: Mapped[str]
    content_type: Mapped[Optional[str]]
    size_bytes: Mapped[int]
    checksum_sha256: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
