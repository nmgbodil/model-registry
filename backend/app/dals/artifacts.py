"""Data access helpers for artifacts."""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import or_, select
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


def get_artifact_id_by_ref(
    session: Session, ref: str, *, exclude_id: Optional[int] = None
) -> Optional[int]:
    """Return the id of an artifact whose name or source_url matches ref."""
    stmt = select(Artifact.id).where(
        or_(Artifact.name == ref, Artifact.source_url == ref)
    )
    if exclude_id is not None:
        stmt = stmt.where(Artifact.id != exclude_id)

    return session.execute(stmt).scalar_one_or_none()


def get_artifacts_with_parent_ref(
    session: Session, ref: str, *, exclude_id: Optional[int] = None
) -> List[Artifact]:
    """Return artifacts whose parent_artifact_ref matches the given ref."""
    stmt = select(Artifact).where(Artifact.parent_artifact_ref == ref)
    if exclude_id is not None:
        stmt = stmt.where(Artifact.id != exclude_id)

    return list(session.scalars(stmt).all())
