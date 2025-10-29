"""backend/app/api/routes_artifacts.py API routes for artifact management."""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, Optional

from flask import Blueprint, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from ..config import get_settings
from ..db import get_session
from ..models import Artifact
from ..storage import save_file

bp_artifacts = Blueprint("artifacts", __name__, url_prefix="/artifacts")
settings = get_settings()


def _allowed(filename: str) -> bool:
    """Return True if the filename has an allowed extension."""
    ext = Path(filename).suffix.lstrip(".").lower()
    return ext in settings.ALLOWED_EXTENSIONS


def _serialize(a: Artifact) -> dict[str, Any]:
    """Convert an Artifact row to its API representation."""
    created_val = a.created_at
    if isinstance(created_val, datetime):
        created = created_val.isoformat() + "Z"
    elif isinstance(created_val, str) and created_val:
        # "YYYY-MM-DD HH:MM:SS" -> "YYYY-MM-DDTHH:MM:SSZ"
        created = created_val.replace(" ", "T") + "Z"
    else:
        created = None

    return {
        "id": a.id,
        "filename": a.filename,
        "size_bytes": a.size_bytes,
        "checksum_sha256": a.checksum_sha256,
        "content_type": a.content_type,
        "created_at": created,
    }


# ── CREATE (upload) ─────────────────────────────────────────────────────────────
@bp_artifacts.post("")
def upload_artifact() -> ResponseReturnValue:
    """Upload a new artifact (multipart/form-data: file=<blob>)."""
    if "file" not in request.files:
        return jsonify({"error": "missing file field"}), HTTPStatus.BAD_REQUEST

    file = request.files["file"]
    fname: Optional[str] = file.filename
    if not fname:
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
        return jsonify(_serialize(art)), HTTPStatus.CREATED


# ── READ (list) ────────────────────────────────────────────────────────────────
@bp_artifacts.get("")
def list_artifacts() -> ResponseReturnValue:
    """List artifacts with pagination."""
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
        data = [_serialize(a) for a in rows]  # serialize while session is open

    return jsonify({"items": data, "limit": limit, "offset": offset})


# ── READ (search) ──────────────────────────────────────────────────────────────
@bp_artifacts.get("/search")
def search_artifacts() -> ResponseReturnValue:
    """Search artifacts by filename substring (case-insensitive)."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "missing q"}), HTTPStatus.BAD_REQUEST

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
            .filter(Artifact.filename.ilike(f"%{q}%"))
            .order_by(Artifact.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        data = [_serialize(a) for a in rows]

    return jsonify({"items": data, "limit": limit, "offset": offset, "q": q})


# ── READ (single) ──────────────────────────────────────────────────────────────
@bp_artifacts.get("/<int:artifact_id>")
def get_artifact(artifact_id: int) -> ResponseReturnValue:
    """Fetch artifact metadata by id."""
    with get_session() as s:
        art = s.get(Artifact, artifact_id)
        if art is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND
        return jsonify(_serialize(art))


# ── UPDATE (patch limited metadata) ────────────────────────────────────────────
@bp_artifacts.patch("/<int:artifact_id>")
def patch_artifact(artifact_id: int) -> ResponseReturnValue:
    """Partially update an artifact.

    Supported fields:
      - filename: str (validated extension; does not rename the stored file)
    """
    # force=True avoids edge cases where PATCH+JSON isn't detected
    body = request.get_json(force=True, silent=True) or {}
    new_filename = body.get("filename")

    if new_filename is None:
        return (
            jsonify({"error": "no updatable fields supplied"}),
            HTTPStatus.BAD_REQUEST,
        )

    if not isinstance(new_filename, str) or not new_filename.strip():
        return jsonify({"error": "invalid filename"}), HTTPStatus.BAD_REQUEST

    if not _allowed(new_filename):
        return jsonify({"error": "file type not allowed"}), HTTPStatus.BAD_REQUEST

    safe_name = secure_filename(new_filename)

    with get_session() as s:
        art = s.get(Artifact, artifact_id)
        if art is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        art.filename = safe_name
        s.flush()
        return jsonify(_serialize(art)), HTTPStatus.OK


# ── DOWNLOAD (stream) ─────────────────────────────────────────────────────────
@bp_artifacts.get("/<int:artifact_id>/download")
def download_artifact(artifact_id: int) -> ResponseReturnValue:
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


# ── DELETE ────────────────────────────────────────────────────────────────────
@bp_artifacts.delete("/<int:artifact_id>")
def delete_artifact(artifact_id: int) -> ResponseReturnValue:
    """Delete an artifact and its file from disk."""
    with get_session() as s:
        art = s.get(Artifact, artifact_id)
        if art is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        try:
            path = Path(art.stored_path)
            if path.exists():
                path.unlink()
        except OSError:
            pass

        s.delete(art)
        return "", HTTPStatus.NO_CONTENT
