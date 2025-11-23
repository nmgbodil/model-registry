"""Data access helpers for ratings-related queries."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Artifact, Rating


def get_artifact_by_id(session: Session, artifact_id: int) -> Optional[Artifact]:
    """Fetch an artifact by its primary key."""
    return session.get(Artifact, artifact_id)


def get_rating_by_artifact(session: Session, artifact_id: int) -> Optional[Rating]:
    """Fetch the rating row for a given artifact id."""
    return session.query(Rating).filter(Rating.artifact_id == artifact_id).one_or_none()
