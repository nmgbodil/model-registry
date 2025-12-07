"""API endpoints for artifact-related operations."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Tuple

from flask import Blueprint, Response, jsonify, request

from app.dals.artifacts import get_artifact_by_id
from app.db.session import orm_session
from app.schemas.artifact import ArtifactCost
from app.services.artifact_cost import (
    ArtifactCostError,
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    InvalidArtifactTypeError,
    compute_artifact_cost,
)
from app.services.artifacts.license_check import (
    ExternalLicenseError,
    RepoNotFound,
    fetch_github_license,
    is_license_compatible_for_finetune_inference,
    normalize_license_string,
)

bp_artifact = Blueprint("artifact", __name__)


def _parse_dependency_flag(raw: str | None) -> bool:
    """Parse dependency query flag from the request."""
    if raw is None:
        return False
    raw_lower = raw.lower()
    if raw_lower in {"true", "1", "yes"}:
        return True
    if raw_lower in {"false", "0", "no"}:
        return False
    raise InvalidArtifactTypeError(
        "There is missing field(s) in the artifact_type or artifact_id or it is formed "
        "improperly, or is invalid."
    )


@bp_artifact.get("/<artifact_type>/<int:artifact_id>/cost")
def get_artifact_cost(
    artifact_type: str, artifact_id: int
) -> tuple[Response, HTTPStatus]:
    """Return the cost for the given artifact."""
    try:
        allowed_types = {"model", "dataset", "code"}
        if (artifact_type or "").strip().lower() not in allowed_types:
            raise InvalidArtifactTypeError(
                "There is missing field(s) in the artifact_type or artifact_id or it "
                "is formed improperly, or is invalid."
            )

        include_dependencies = _parse_dependency_flag(request.args.get("dependency"))
        cost_map = compute_artifact_cost(
            artifact_id, include_dependencies=include_dependencies
        )
        payload: Dict[str, Any] = {}
        for art_id, cost in cost_map.items():
            payload[str(art_id)] = ArtifactCost(
                total_cost=cost.total_cost, standalone_cost=cost.standalone_cost
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
def check_model_license(artifact_id: int) -> Tuple[Response, HTTPStatus]:
    """Check license compatibility for a model artifact and a GitHub repo.

    This endpoint implements `/artifact/model/{id}/license-check` from the
    OpenAPI spec. It returns a bare boolean indicating whether the model's
    license is compatible with the GitHub repository for fine-tune +
    inference/generation usage.
    """
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    github_url = payload.get("github_url")

    if not isinstance(github_url, str) or not github_url:
        error_msg = (
            "The license check request is malformed or references an "
            "unsupported usage context."
        )
        return jsonify({"error": error_msg}), HTTPStatus.BAD_REQUEST

    with orm_session() as session:
        artifact = get_artifact_by_id(session, artifact_id)

        if artifact is None or artifact.type != "model":
            error_msg = "The artifact or GitHub project could not be found."
            return jsonify({"error": error_msg}), HTTPStatus.NOT_FOUND

        model_license_raw = artifact.license

    model_spdx = normalize_license_string(model_license_raw)
    if not model_spdx:
        error_msg = (
            "Artifact has no recognized license; " "cannot evaluate compatibility."
        )
        return jsonify({"error": error_msg}), HTTPStatus.BAD_REQUEST
    try:
        repo_license = fetch_github_license(github_url)
    except ValueError as exc:
        error_msg = (
            "The license check request is malformed or references an "
            f"unsupported usage context: {exc}"
        )
        return jsonify({"error": error_msg}), HTTPStatus.BAD_REQUEST
    except RepoNotFound:
        error_msg = "The artifact or GitHub project could not be found."
        return jsonify({"error": error_msg}), HTTPStatus.NOT_FOUND
    except ExternalLicenseError as exc:
        error_msg = str(exc) or "External license information could not be retrieved."
        return jsonify({"error": error_msg}), HTTPStatus.BAD_GATEWAY

    compatible = is_license_compatible_for_finetune_inference(
        model_spdx=model_spdx,
        repo_spdx=repo_license.spdx_id,
    )

    return jsonify(compatible), HTTPStatus.OK
