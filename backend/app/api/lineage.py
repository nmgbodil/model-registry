"""API endpoint for artifact lineage."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify
from flask_jwt_extended import jwt_required

from app.schemas.lineage import ArtifactLineageGraph
from app.services.lineage import (
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    LineageServiceError,
    get_lineage_graph,
)
from app.utils import get_user_id_from_token, role_allowed

bp_lineage = Blueprint("artifact_lineage", __name__, url_prefix="/artifact")


@bp_lineage.get("/model/<int:artifact_id>/lineage")
@jwt_required()  # type: ignore[misc]
def get_artifact_lineage(artifact_id: int) -> tuple[Response, HTTPStatus]:
    """Return the lineage graph for the given model artifact."""
    get_user_id_from_token()
    if not role_allowed({"uploader", "downloader", "searcher"}):
        return jsonify({"error": "forbidden"}), HTTPStatus.FORBIDDEN
    try:
        graph: ArtifactLineageGraph = get_lineage_graph(artifact_id)
        return jsonify(graph.model_dump()), HTTPStatus.OK
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
    except ArtifactNotFoundError as exc:
        return (
            jsonify({"error": str(exc) or "Artifact does not exist."}),
            HTTPStatus.NOT_FOUND,
        )
    except LineageServiceError:
        return (
            jsonify({"error": "The lineage system encountered an error."}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
