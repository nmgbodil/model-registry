"""Registry reset endpoint."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue
from flask_jwt_extended import jwt_required

from app.db.models import Artifact, Rating, User, UserRole
from app.db.session import orm_session
from app.services.storage import delete_all_objects
from app.utils import role_allowed

bp_reset = Blueprint("reset", __name__)


@bp_reset.delete("/reset")
@jwt_required()  # type: ignore[misc]
def reset_registry() -> ResponseReturnValue:
    """Reset the registry: purge S3 artifacts, artifacts, and ratings."""
    if not role_allowed({"admin"}):
        return jsonify({"error": "forbidden"}), HTTPStatus.FORBIDDEN
    try:
        delete_all_objects()
    except Exception:
        # Best-effort: if S3 is not configured, proceed with DB reset.
        pass

    with orm_session() as session:
        session.query(Rating).delete()
        session.query(Artifact).delete()
        session.query(User).filter(User.role != UserRole.admin).delete()
        session.commit()
    return jsonify({"message": "reset"}), HTTPStatus.OK
