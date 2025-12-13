"""API endpoints for retrieving model ratings."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify
from flask_jwt_extended import jwt_required

from app.auth.api_request_limiter import enforce_api_limits
from app.db.models import ArtifactStatus
from app.services.ratings import (
    ArtifactNotFoundError,
    ArtifactNotModelError,
    InvalidArtifactIdError,
    RatingNotFoundError,
    get_model_rating,
)
from app.utils import (
    _wait_for_ingestion,
    get_user_id_from_token,
    role_allowed,
)

bp_ratings = Blueprint("ratings", __name__, url_prefix="/artifact")


@bp_ratings.get("/model/<int:artifact_id>/rate")
@jwt_required()  # type: ignore[misc]
@enforce_api_limits
def rate_model(artifact_id: int) -> tuple[Response, HTTPStatus]:
    """Return a rating for the given model artifact."""
    get_user_id_from_token()
    if not role_allowed({"uploader", "downloader", "searcher"}):
        return (
            jsonify({"error": "forbidden"}),
            HTTPStatus.FORBIDDEN,
        )

    try:
        # Wait until artifact ingestion is complete
        status = _wait_for_ingestion(artifact_id)
        if status == ArtifactStatus.pending:
            raise ArtifactNotFoundError(
                "Artifact ingestion is still in progress; timed out waiting."
            )
        elif status is None:
            raise ArtifactNotFoundError("Artifact does not exist.")

        rating = get_model_rating(artifact_id)
        return jsonify(rating.model_dump()), HTTPStatus.OK
    except InvalidArtifactIdError:
        return (
            jsonify(
                {
                    "error": (
                        "There is missing field(s) in the artifact_id or it is formed "
                        "improperly, or is invalid."
                    )
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )
    except (ArtifactNotFoundError, RatingNotFoundError, ArtifactNotModelError) as exc:
        return (
            jsonify(
                {
                    "error": str(exc)
                    or "Rating not found for artifact or artifact not eligible."
                }
            ),
            HTTPStatus.NOT_FOUND,
        )
    except Exception as e:
        print(e)
        return (
            jsonify({"error": "Rating system encountered an error."}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
