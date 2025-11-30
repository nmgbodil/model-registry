"""Business logic for computing artifact costs."""

from __future__ import annotations

from app.dals.artifacts import (
    get_artifact_by_id,
    get_artifact_size,
)
from app.db.session import orm_session
from app.schemas.artifact import ArtifactCost


class ArtifactCostError(Exception):
    """Base exception for artifact cost errors."""


class InvalidArtifactTypeError(ArtifactCostError):
    """Raised when the artifact type is missing or invalid."""


class InvalidArtifactIdError(ArtifactCostError):
    """Raised when the artifact id is missing or invalid."""


class ArtifactNotFoundError(ArtifactCostError):
    """Raised when the artifact cannot be found."""


def compute_artifact_cost(
    artifact_type: str, artifact_id: int, include_dependencies: bool = False
) -> ArtifactCost:
    """Calculate cost for an artifact, optionally including dependencies."""
    allowed_types = {"model", "dataset", "code"}
    normalized_type = (artifact_type or "").strip().lower()

    if normalized_type not in allowed_types:
        raise InvalidArtifactTypeError(
            "There is missing field(s) in the artifact_type or artifact_id or it is "
            "formed improperly, or is invalid."
        )

    if not artifact_id or artifact_id <= 0:
        raise InvalidArtifactIdError(
            "There is missing field(s) in the artifact_type or artifact_id or it is "
            "formed improperly, or is invalid."
        )

    try:
        with orm_session() as session:
            artifact = get_artifact_by_id(session, artifact_id)
            if artifact is None:
                raise ArtifactNotFoundError("Artifact does not exist.")

            if (artifact.type or "").lower() != normalized_type:
                raise InvalidArtifactTypeError(
                    "There is missing field(s) in the artifact_type or artifact_id or "
                    "it is formed improperly, or is invalid."
                )

            size = get_artifact_size(session, artifact_id)
            if size is None:
                raise ArtifactNotFoundError("Artifact does not exist.")

            total_cost = float(size)
            standalone_cost = total_cost if include_dependencies else None
            return ArtifactCost(total_cost=total_cost, standalone_cost=standalone_cost)
    except ArtifactCostError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ArtifactCostError(
            "The artifact cost calculator encountered an error."
        ) from exc
