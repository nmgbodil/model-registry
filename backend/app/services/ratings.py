"""Business logic for rating artifacts."""

from __future__ import annotations

from app.dals.ratings import get_artifact_by_id, get_rating_by_artifact
from app.db.models import ArtifactStatus
from app.db.session import orm_session
from app.schemas.model_rating import ModelRating
from app.utils import build_model_rating_from_record


class RatingServiceError(Exception):
    """Base exception for rating service errors."""


class InvalidArtifactIdError(RatingServiceError):
    """Raised when the artifact id is missing or invalid."""


class ArtifactNotFoundError(RatingServiceError):
    """Raised when the artifact cannot be found."""


class ArtifactNotModelError(RatingServiceError):
    """Raised when the artifact exists but is not a model."""


class RatingNotFoundError(RatingServiceError):
    """Raised when a rating row cannot be found for the artifact."""


def get_model_rating(artifact_id: int) -> ModelRating:
    """Return the rating for an artifact if it already exists."""
    if not artifact_id or artifact_id <= 0:
        raise InvalidArtifactIdError(
            "There is missing field(s) in the artifact_id or it is formed improperly, "
            "or is invalid."
        )

    try:
        with orm_session() as session:
            artifact = get_artifact_by_id(session, artifact_id)
            if artifact is None:
                raise ArtifactNotFoundError("Artifact not found.")
            if not artifact.type or artifact.type != "model":
                raise ArtifactNotModelError("Artifact is not a model.")
            if artifact.status != ArtifactStatus.accepted:
                raise RatingNotFoundError(
                    "Rating not found for artifact or artifact not eligible."
                )

            existing_rating = get_rating_by_artifact(session, artifact_id)
            if existing_rating is None:
                raise RatingNotFoundError(
                    "Rating not found for artifact or artifact not eligible."
                )

            return build_model_rating_from_record(artifact, existing_rating)
    except RatingServiceError:
        raise
    except Exception as exc:
        print(exc)
        raise RatingServiceError("Rating system encountered an error.") from exc
