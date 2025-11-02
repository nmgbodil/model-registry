"""app/models.py SQLAlchemy models for the application."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base  # re-exported via __all__


class Artifact(Base):
    """ORM model for an artifact (uploaded file)."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Relaxed: allow missing checksum (URL-only ingests, best-effort metadata)
    checksum_sha256: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        default="",           # Python-side default
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


__all__ = ["Base", "Artifact"]
