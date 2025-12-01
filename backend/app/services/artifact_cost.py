"""Business logic for computing artifact costs."""

from __future__ import annotations

from typing import Dict

from app.dals.artifacts import get_artifact_by_id
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
    artifact_id: int, include_dependencies: bool = False
) -> Dict[int, ArtifactCost]:
    """Calculate cost for an artifact, optionally including dependencies."""
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

            def _size_from_art(art: object) -> float:
                if not art or getattr(art, "size_bytes", None) is None:
                    raise ArtifactNotFoundError("Artifact does not exist.")
                return float(getattr(art, "size_bytes"))

            costs: Dict[int, ArtifactCost] = {}
            base_total = _size_from_art(artifact)
            costs[artifact.id] = ArtifactCost(
                total_cost=base_total,
                standalone_cost=base_total if include_dependencies else None,
            )

            if include_dependencies:
                deps = [
                    artifact.dataset
                    or (
                        get_artifact_by_id(session, artifact.dataset_id)
                        if artifact.dataset_id
                        else None
                    ),
                    artifact.code
                    or (
                        get_artifact_by_id(session, artifact.code_id)
                        if artifact.code_id
                        else None
                    ),
                ]
                for dep in deps:
                    if dep is None:
                        continue
                    dep_size = _size_from_art(dep)
                    costs[dep.id] = ArtifactCost(
                        total_cost=dep_size, standalone_cost=dep_size
                    )
                    base_total += dep_size
                costs[artifact.id].total_cost = base_total

            return costs
    except ArtifactCostError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ArtifactCostError(
            "The artifact cost calculator encountered an error."
        ) from exc
