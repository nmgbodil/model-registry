"""API endpoints for artifact-related operations."""

from http import HTTPStatus
from typing import Any, Dict

from flask import Blueprint, Response, jsonify, request

from app.schemas.artifact import ArtifactCost
from app.services.artifact_cost import (
    ArtifactCostError,
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    InvalidArtifactTypeError,
    compute_artifact_cost,
)

bp_artifact = Blueprint("artifact", __name__, url_prefix="/artifact")


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
        include_dependencies = _parse_dependency_flag(request.args.get("dependency"))
        cost = compute_artifact_cost(
            artifact_type, artifact_id, include_dependencies=include_dependencies
        )
        payload: Dict[str, Any] = {
            str(artifact_id): ArtifactCost(
                total_cost=cost.total_cost, standalone_cost=cost.standalone_cost
            ).model_dump(exclude_none=True)
        }
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
