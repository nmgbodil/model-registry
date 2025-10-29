"""Artifacts API routes."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ..config import get_settings
from ..db import get_session
from ..models import Artifact
from ..storage import save_file

bp_artifacts = Blueprint("artifacts", __name__, url_prefix="/artifacts")
settings = get_settings()


def _allowed(filename: str) -> bool:
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext in settings.ALLOWED_EXTENSIONS


@bp_artifacts.post("")
def upload_artifact() -> tuple[Response, int]:
    """Upload a new artifact (multipart/form-data: file=<blob>)."""
    if "file" not in request.files:
        return jsonify({"error": "missing file field"}), HTTPStatus.BAD_REQUEST

    file = request.files["file"]
    fname = file.filename
    if fname is None or fname == "":
        return jsonify({"error": "empty filename"}), HTTPStatus.BAD_REQUEST

    if not _allowed(fname):
        return jsonify({"error": "file type not allowed"}), HTTPStatus.BAD_REQUEST

    safe_client_name = secure_filename(fname)

    stored_path, digest, size = save_file(file, settings.UPLOAD_DIR)

    with get_session() as s:
        art = Artifact(
            filename=safe_client_name,
            stored_path=str(stored_path),
            content_type=file.mimetype,
            size_bytes=size,
            checksum_sha256=digest,
        )
        s.add(art)
        s.flush()
        payload: dict[str, Any] = {
            "id": art.id,
            "filename": art.filename,
            "size_bytes": art.size_bytes,
            "checksum_sha256": art.checksum_sha256,
            "content_type": art.content_type,
            "created_at": art.created_at.isoformat() + "Z",
        }
        return jsonify(payload), HTTPStatus.CREATED


@bp_artifacts.get("")
def list_artifacts() -> Response:
    """List artifacts (simple latest-first, limit & offset for the UI)."""
    try:
        limit = max(1, min(100, int(request.args.get("limit", "20"))))
    except ValueError:
        limit = 20
    try:
        offset = max(0, int(request.args.get("offset", "0")))
    except ValueError:
        offset = 0

    with get_session() as s:
        rows = (
            s.query(Artifact)
            .order_by(Artifact.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    data = [
        {
            "id": a.id,
            "filename": a.filename,
            "size_bytes": a.size_bytes,
            "checksum_sha256": a.checksum_sha256,
            "content_type": a.content_type,
            "created_at": a.created_at.isoformat() + "Z",
        }
        for a in rows
    ]
    return jsonify({"items": data, "limit": limit, "offset": offset})


@bp_artifacts.get("/<int:artifact_id>")
def get_artifact(artifact_id: int) -> tuple[Response, int] | Response:
    """Fetch artifact metadata by id."""
    with get_session() as s:
        art = s.get(Artifact, artifact_id)
        if art is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        return jsonify(
            {
                "id": art.id,
                "filename": art.filename,
                "size_bytes": art.size_bytes,
                "checksum_sha256": art.checksum_sha256,
                "content_type": art.content_type,
                "created_at": art.created_at.isoformat() + "Z",
            }
        )


@bp_artifacts.get("/<int:artifact_id>/download")
def download_artifact(artifact_id: int) -> tuple[Response, int] | Response:
    """Stream the artifact file."""
    with get_session() as s:
        art = s.get(Artifact, artifact_id)
        if art is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

    path = Path(art.stored_path)
    if not path.exists():
        return (
            jsonify({"error": "file missing on disk"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    as_attachment = request.args.get("download", "1") != "0"
    return send_file(
        path,
        mimetype=art.content_type or "application/octet-stream",
        as_attachment=as_attachment,
        download_name=art.filename,
        max_age=0,
        etag=art.checksum_sha256 if art.checksum_sha256 else False,
        conditional=True,
        last_modified=None,
    )
