"""API endpoints for artifact-related operations."""

from http import HTTPStatus
from typing import Any, Dict, Tuple

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required

from app.auth.api_request_limiter import enforce_api_limits
from app.db.models import ArtifactStatus
from app.schemas.artifact import ArtifactCost
from app.services.artifact import (
    ArtifactCostError,
    ArtifactNotFoundError,
    ExternalLicenseError,
    InvalidArtifactIdError,
    InvalidArtifactTypeError,
    InvalidLicenseRequestError,
    check_model_license_compatibility,
    compute_artifact_cost,
)
from app.utils import (
    _wait_for_ingestion,
    get_user_id_from_token,
    role_allowed,
)

bp_artifact = Blueprint("artifact_cost", __name__, url_prefix="/artifact")


def _parse_dependency_flag(raw: str | None) -> bool:
    """Parse dependency query flag from the request."""
    if raw is None:
        return False
    raw_lower = raw.lower()
    if raw_lower in {"true", "1", "yes"}:
        return True
    if raw_lower in {"false", "0", "no"}:
        return False
    raise InvalidArtifactTypeError("Missing or invalid artifact_type or artifact_id.")


@bp_artifact.get("/<artifact_type>/<int:artifact_id>/cost")
@jwt_required()  # type: ignore[misc]
@enforce_api_limits
def get_artifact_cost(
    artifact_type: str, artifact_id: int
) -> tuple[Response, HTTPStatus]:
    """Return the cost for the given artifact."""
    get_user_id_from_token()
    if not role_allowed({"uploader", "downloader", "searcher"}):
        return jsonify({"error": "forbidden"}), HTTPStatus.FORBIDDEN
    try:
        allowed_types = {"model", "dataset", "code"}
        if artifact_type not in allowed_types:
            raise InvalidArtifactTypeError(
                "There is missing field(s) in the artifact_type or "
                "artifact_id or it is formed improperly, or is invalid."
            )

        # Wait until artifact ingestion is complete
        status = _wait_for_ingestion(artifact_id)
        if status == ArtifactStatus.pending:
            raise ArtifactNotFoundError(
                "Artifact ingestion is still in progress; timed out waiting."
            )
        elif status is None:
            raise ArtifactNotFoundError("Artifact does not exist.")

        include_dependencies = _parse_dependency_flag(request.args.get("dependency"))
        cost_map = compute_artifact_cost(
            artifact_id, include_dependencies=include_dependencies
        )
        payload: Dict[str, Any] = {}
        for art_id, cost in cost_map.items():
            payload[str(art_id)] = ArtifactCost(
                total_cost=cost.total_cost,
                standalone_cost=cost.standalone_cost,
            ).model_dump(exclude_none=True)
        return jsonify(payload), HTTPStatus.OK
    except (InvalidArtifactIdError, InvalidArtifactTypeError) as exc:
        return (
            jsonify({"error": str(exc)}),
            HTTPStatus.BAD_REQUEST,
        )
    except ArtifactNotFoundError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
    except ArtifactCostError as exc:
        return (
            jsonify(
                {
                    "error": str(exc)
                    or "The artifact cost calculator encountered an error."
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )


@bp_artifact.post("/model/<int:artifact_id>/license-check")
@jwt_required()  # type: ignore[misc]
@enforce_api_limits
def check_model_license(artifact_id: int) -> Tuple[Response, HTTPStatus]:
    """Check license compatibility for a model artifact and a GitHub repo.

    This endpoint implements `/artifact/model/{id}/license-check` from the
    OpenAPI spec. It returns a bare boolean indicating whether the model's
    license is compatible with the GitHub repository for fine-tune +
    inference/generation usage.
    """
    get_user_id_from_token()
    if not role_allowed({"uploader", "downloader", "searcher"}):
        return jsonify({"error": "forbidden"}), HTTPStatus.FORBIDDEN
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    raw_github_url = payload.get("github_url")
    github_url: str = raw_github_url if isinstance(raw_github_url, str) else ""
    try:
        # Wait until artifact ingestion is complete
        status = _wait_for_ingestion(artifact_id)
        if status == ArtifactStatus.pending:
            raise ArtifactNotFoundError(
                "Artifact ingestion is still in progress; timed out waiting."
            )
        elif status is None:
            raise ArtifactNotFoundError("Artifact does not exist.")

        compatible = check_model_license_compatibility(artifact_id, github_url)
        return jsonify(compatible), HTTPStatus.OK
    except InvalidLicenseRequestError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except ArtifactNotFoundError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
    except ExternalLicenseError as exc:
        msg = str(exc) or "External license information could not be retrieved."
        return jsonify({"error": msg}), HTTPStatus.BAD_GATEWAY
    except Exception as exc:
        msg = str(exc) or "An unexpected error occurred during license evaluation."
        return jsonify({"error": msg}), HTTPStatus.INTERNAL_SERVER_ERROR
