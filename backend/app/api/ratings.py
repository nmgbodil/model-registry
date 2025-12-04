"""API endpoints for retrieving model ratings."""

from __future__ import annotations

import os
import time
from http import HTTPStatus
from typing import Optional

from flask import Blueprint, Response, jsonify

from app.db.models import Artifact, ArtifactStatus
from app.db.session import orm_session
from app.services.ratings import (
    ArtifactNotFoundError,
    ArtifactNotModelError,
    InvalidArtifactIdError,
    RatingNotFoundError,
    get_model_rating,
)

bp_ratings = Blueprint("ratings", __name__, url_prefix="/artifact")


def _wait_for_ingestion(
    artifact_id: int,
    timeout_seconds: float = float(os.getenv("RATING_WAIT_TIMEOUT_SECONDS", "300")),
    poll_seconds: float = float(os.getenv("RATING_WAIT_POLL_SECONDS", "1")),
) -> Optional[ArtifactStatus]:
    """Poll for artifact ingestion to finish or until timeout."""
    start = time.monotonic()
    while True:
        with orm_session() as session:
            artifact = session.get(Artifact, artifact_id)
            if artifact is None:
                return None
            status = artifact.status

        if status != ArtifactStatus.pending:
            return status

        if time.monotonic() - start >= timeout_seconds:
            return ArtifactStatus.pending

        time.sleep(poll_seconds)


@bp_ratings.get("/model/<int:artifact_id>/rate")
def rate_model(artifact_id: int) -> tuple[Response, HTTPStatus]:
    """Return a rating for the given model artifact."""
    status = _wait_for_ingestion(artifact_id)
    if status == ArtifactStatus.pending:
        return (
            jsonify(
                {
                    "error": (
                        "Artifact ingestion is still in progress; timed out waiting."
                    ),
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    try:
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
