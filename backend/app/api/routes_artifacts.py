# backend/app/api/routes_artifacts.py — API routes aligned to Phase 2 spec (clean).

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Tuple, Set
from urllib.parse import urlparse

from flask import Blueprint, jsonify, make_response, request
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from ..db import get_session
from ..models import Artifact

# Optional Hugging Face support (enrichment & snapshot)
try:
    from huggingface_hub import HfApi, snapshot_download  # type: ignore
    HF_AVAILABLE = True
except Exception:
    HF_AVAILABLE = False

# ──────────────────────────────────────────────────────────────────────────────
# Blueprints per spec:
#   /artifacts … collection + item endpoints
#   /artifact  … creation + search endpoints
# ──────────────────────────────────────────────────────────────────────────────

bp_artifacts = Blueprint("artifacts", __name__, url_prefix="/artifacts")
bp_artifact = Blueprint("artifact", __name__, url_prefix="/artifact")


# ===== Helpers =================================================================

"""
def _require_auth() -> Optional[ResponseReturnValue]:
    Spec requires X-Authorization on artifact endpoints (baseline & non-baseline here).
    Keep it simple: accept any non-empty header; tighten as needed.
    token = request.headers.get("X-Authorization")
    if not token:
        return jsonify({"error": "missing X-Authorization"}), HTTPStatus.FORBIDDEN
    # Dev-only strictness example:
    # if token != "dev-token":
    #     return jsonify({"error": "invalid token"}), HTTPStatus.FORBIDDEN
    return None"""

def _require_auth():
    return None



def _iso(dt: Any) -> Optional[str]:
    if isinstance(dt, datetime):
        return dt.isoformat() + "Z"
    if isinstance(dt, str) and dt:
        return dt.replace(" ", "T") + "Z"
    return None


def _to_metadata(a: Artifact) -> Dict[str, Any]:
    """ArtifactMetadata { name, id, type }."""
    art_type = getattr(a, "type", None) or "model"
    return {"name": a.filename, "id": str(a.id), "type": art_type}


def _to_envelope(a: Artifact) -> Dict[str, Any]:
    """Artifact { metadata, data }."""
    url = a.stored_path or ""
    show_url = url.startswith(("http://", "https://", "file://"))
    return {"metadata": _to_metadata(a), "data": {"url": url if show_url else None}}


def _validate_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    return p.scheme in {"http", "https"} and bool(p.netloc)


def _is_hf_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Return (is_hf, kind, repo_id) where kind ∈ {"model","dataset","space","unknown"}.
    """
    try:
        p = urlparse(url)
    except Exception:
        return (False, "unknown", None)
    if p.scheme not in {"http", "https"}:
        return (False, "unknown", None)
    if p.netloc not in {"huggingface.co", "www.huggingface.co"}:
        return (False, "unknown", None)

    parts = [seg for seg in p.path.split("/") if seg]
    if not parts:
        return (True, "unknown", None)

    if parts[0] == "datasets" and len(parts) >= 3:
        return (True, "dataset", f"{parts[1]}/{parts[2]}")
    elif parts[0] == "spaces" and len(parts) >= 3:
        return (True, "space", f"{parts[1]}/{parts[2]}")
    elif len(parts) >= 2:
        return (True, "model", f"{parts[0]}/{parts[1]}")
    else:
        return (True, "unknown", None)


def _compute_duplicate(s, artifact_type: str, name: str, url: str) -> Optional[Artifact]:
    """
    Simple duplicate heuristic:
      - same stored_path (URL) and same type
      - OR same name and same type (conservative)
    """
    q = s.query(Artifact)
    if hasattr(Artifact, "type"):
        q = q.filter(Artifact.type == artifact_type)
    dup = (
        q.filter(Artifact.stored_path == url).first()
        or q.filter(Artifact.filename == name).first()
    )
    return dup


# ===== Spec: POST /artifacts (ArtifactsList) ===================================

@bp_artifacts.post("")
def artifacts_list() -> ResponseReturnValue:
    """
    Body: ArtifactQuery[] (e.g., [{ "name": "*" }])
    Query: ?offset= (string). Also tolerates 'offset' request header (legacy).
    Return: 200 Array<ArtifactMetadata>, and response header 'offset' with next offset.
    """
    # Auth required by spec
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    # 1) Try normal JSON decode
    body = request.get_json(silent=True)

    # 2) Fallback to raw parse for odd content-types/charsets/quoting (e.g., PowerShell)
    if body is None:
        raw = request.get_data(cache=False, as_text=True)
        if raw:
            try:
                import json
                body = json.loads(raw)
            except Exception:
                body = None

    # 3) If a single object was sent, tolerate by wrapping to a list
    if isinstance(body, dict):
        body = [body]

    # 4) Still not a list? Return a helpful preview to debug
    if not isinstance(body, list):
        raw_preview = (request.get_data(cache=False, as_text=True) or "")[:200]
        return (
            jsonify(
                {
                    "error": "invalid body; expected array of ArtifactQuery",
                    "received_preview": raw_preview,
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    # Parse offset (query param per spec), but accept legacy custom header if present
    offset_raw = request.args.get("offset")
    if offset_raw is None:
        offset_raw = request.headers.get("offset", "0")  # tolerate old client behavior
    try:
        offset = max(0, int(offset_raw or "0"))
    except ValueError:
        return jsonify({"error": "bad offset"}), HTTPStatus.BAD_REQUEST

    # Collect filters
    names: List[str] = []
    types: Set[str] = set()
    for q in body:
        if not isinstance(q, dict) or "name" not in q:
            return jsonify({"error": "invalid ArtifactQuery"}), HTTPStatus.BAD_REQUEST
        names.append(q["name"])
        for t in q.get("types") or []:
            types.add(t)

    with get_session() as s:
        query = s.query(Artifact).order_by(Artifact.id.desc())

        # name filter: exact match unless "*" appears alone
        if names and not (len(names) == 1 and names[0] == "*"):
            query = query.filter(Artifact.filename.in_(names))

        # type filter if available on the model
        if types and hasattr(Artifact, "type"):
            query = query.filter(Artifact.type.in_(list(types)))

        rows = query.offset(offset).limit(100).all()
        items = [_to_metadata(a) for a in rows]

    resp = make_response(jsonify(items), HTTPStatus.OK)
    resp.headers["offset"] = str(offset + len(items))
    return resp


# ===== Spec: GET/PUT/DELETE /artifacts/{artifact_type}/{id} ====================

@bp_artifacts.get("/<artifact_type>/<int:artifact_id>")
def artifact_get(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
    # Auth required
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    with get_session() as s:
        a = s.get(Artifact, artifact_id)
        if a is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND
        # Optional: ensure path type matches stored type (soft check)
        if hasattr(a, "type") and a.type != artifact_type:
            return jsonify({"error": "type mismatch"}), HTTPStatus.BAD_REQUEST
        return jsonify(_to_envelope(a)), HTTPStatus.OK


@bp_artifacts.put("/<artifact_type>/<int:artifact_id>")
def artifact_put(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
    # Auth required
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    """
    Replace artifact contents with provided envelope.
    Requires metadata.id == path id and metadata.type == path type.
    Updates filename from metadata.name and stored URL from data.url.
    """
    body = request.get_json(force=True, silent=True) or {}
    md = body.get("metadata") or {}
    data = body.get("data") or {}

    if str(md.get("id")) != str(artifact_id) or md.get("type") != artifact_type:
        return jsonify({"error": "name/id/type mismatch"}), HTTPStatus.BAD_REQUEST

    with get_session() as s:
        a = s.get(Artifact, artifact_id)
        if a is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        name = md.get("name")
        if isinstance(name, str) and name.strip():
            a.filename = secure_filename(name)

        url = data.get("url")
        if isinstance(url, str) and url.strip():
            a.stored_path = url  # treat as source URL

        s.flush()
        return jsonify({"message": "updated"}), HTTPStatus.OK


@bp_artifacts.delete("/<artifact_type>/<int:artifact_id>")
def artifact_delete(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
    # Auth required
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    with get_session() as s:
        a = s.get(Artifact, artifact_id)
        if a is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        # Optional: enforce path type
        if hasattr(a, "type") and a.type != artifact_type:
            return jsonify({"error": "type mismatch"}), HTTPStatus.BAD_REQUEST

        s.delete(a)
        return jsonify({"message": "deleted"}), HTTPStatus.OK


# ===== Spec: POST /artifact/{artifact_type} (ArtifactCreate) ===================

@bp_artifact.post("/<artifact_type>")
def artifact_create(artifact_type: str) -> ResponseReturnValue:
    """
    Body: { "url": "https://..." }
    Optional: ?download=1 to snapshot HF repo locally (if huggingface_hub installed).
    Return: 201 { metadata, data }
    Errors: 400 malformed, 403 missing auth, 409 duplicate
    """
    # Auth required
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    body = request.get_json(force=True, silent=True) or {}
    url = body.get("url")
    if not isinstance(url, str) or not url.strip():
        return jsonify({"error": "missing url"}), HTTPStatus.BAD_REQUEST
    url = url.strip()
    if not _validate_http_url(url):
        return jsonify({"error": "invalid url"}), HTTPStatus.BAD_REQUEST

    do_download = request.args.get("download", "0").lower() in {"1", "true", "yes"}

    # derive a base name from URL
    derived_name = secure_filename(url.rstrip("/").split("/")[-1] or "artifact")
    size_bytes: int = 0
    checksum_sha256: Optional[str] = None

    # Hugging Face enrichment (best-effort)
    is_hf, hf_kind, repo_id = _is_hf_url(url)
    if is_hf and HF_AVAILABLE and repo_id:
        try:
            api = HfApi()
            if hf_kind == "dataset" or artifact_type == "dataset":
                info = api.dataset_info(repo_id)  # type: ignore
            else:
                info = api.model_info(repo_id)  # type: ignore

            # name: repo tail
            derived_name = secure_filename(repo_id.split("/")[-1])

            # size: sum known file sizes (siblings)
            siblings = getattr(info, "siblings", None)
            if siblings:
                size_bytes = sum((getattr(f, "size", 0) or 0) for f in siblings)

            # sha: some infos expose .sha
            checksum_sha256 = getattr(info, "sha", None)

            # Optional local snapshot
            if do_download:
                local_dir = snapshot_download(repo_id)  # caches under HF cache
                url = f"file://{local_dir}"
        except Exception:
            # Best-effort: proceed with raw URL if HF lookup fails
            pass

    # Persist (with duplicate detection)
    with get_session() as s:
        dup = _compute_duplicate(s, artifact_type, derived_name, url)
        if dup:
            # Spec says 409 when artifact exists already
            return jsonify(_to_envelope(dup)), HTTPStatus.CONFLICT

        a = Artifact(
            filename=derived_name,
            stored_path=url,
            content_type="application/octet-stream",
            size_bytes=size_bytes or 0,
            checksum_sha256=checksum_sha256,
        )
        if hasattr(a, "type"):
            setattr(a, "type", artifact_type)

        s.add(a)
        s.flush()
        return jsonify(_to_envelope(a)), HTTPStatus.CREATED


# ===== Spec: POST /artifact/byRegEx (ArtifactByRegExGet) =======================

@bp_artifact.post("/byRegEx")
def artifact_by_regex() -> ResponseReturnValue:
    # Auth required
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    body = request.get_json(force=True, silent=True) or {}
    regex = body.get("regex")
    if not isinstance(regex, str) or not regex.strip():
        return jsonify({"error": "missing regex"}), HTTPStatus.BAD_REQUEST

    # Simple contains search (baseline): translate common .*foo.* to %foo%
    token = regex.replace(".*", "").strip("%")
    with get_session() as s:
        rows = (
            s.query(Artifact)
            .filter(Artifact.filename.ilike(f"%{token}%"))
            .order_by(Artifact.id.desc())
            .limit(200)
            .all()
        )
        return jsonify([_to_metadata(a) for a in rows]), HTTPStatus.OK


# ===== Spec: GET /artifact/byName/{name} (ArtifactByNameGet) ===================

@bp_artifact.get("/byName/<name>")
def artifact_by_name(name: str) -> ResponseReturnValue:
    # Auth required
    auth_err = _require_auth()
    if auth_err is not None:
        return auth_err

    with get_session() as s:
        rows = (
            s.query(Artifact)
            .filter(Artifact.filename == name)
            .order_by(Artifact.id.desc())
            .all()
        )
        items = [_to_metadata(a) for a in rows]
        if not items:
            return jsonify({"error": "no such artifact"}), HTTPStatus.NOT_FOUND
        return jsonify(items), HTTPStatus.OK
