"""Data access helpers for artifacts."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import Artifact


def get_artifact_by_id(session: Session, artifact_id: int) -> Optional[Artifact]:
    """Fetch an artifact by its primary key."""
    return session.get(Artifact, artifact_id)


def update_artifact_attributes(
    session: Session, artifact: Artifact, **attrs: Any
) -> Artifact:
    """Update arbitrary attributes on an artifact."""
    for key, value in attrs.items():
        setattr(artifact, key, value)
    session.add(artifact)
    session.flush()
    return artifact
