"""Registry reset endpoint."""

from __future__ import annotations

from http import HTTPStatus
from typing import Optional

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

from app.db.models import Artifact, Rating
from app.db.session import orm_session
from app.services.storage import delete_all_objects

bp_reset = Blueprint("reset", __name__)


def _require_auth() -> Optional[ResponseReturnValue]:
    """Placeholder auth hook; allow all for now."""
    return None


@bp_reset.delete("/reset")
def reset_registry() -> ResponseReturnValue:
    """Reset the registry: purge S3 artifacts, artifacts, and ratings."""
    auth_err = _require_auth()
    if auth_err is not None:
        print("Reset endpoint: authentication failed.")
        return auth_err

    try:
        delete_all_objects()
        print("Reset endpoint: S3 objects deleted.")
    except Exception:
        # Best-effort: if S3 is not configured, proceed with DB reset.
        print("Reset endpoint: S3 delete failed; proceeding with DB cleanup.")
        pass

    with orm_session() as session:
        session.query(Rating).delete()
        session.query(Artifact).delete()
        session.commit()
    print("Reset endpoint: database tables cleared.")
    return jsonify({"message": "reset"}), HTTPStatus.OK
