"""API routes for artifact management (baseline spec coverage)."""

from __future__ import annotations

import os
import re
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Set, cast
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Blueprint, Response, jsonify, make_response, request
from flask.typing import ResponseReturnValue

from app.db.models import Artifact, ArtifactStatus
from app.db.session import orm_session
from app.utils import artifact_name_from_url
from app.workers.ingestion_worker.ingestion_logic import ingest_artifact

load_dotenv()

bp_artifacts = Blueprint("artifacts", __name__, url_prefix="/artifacts")
bp_artifact = Blueprint("artifact", __name__, url_prefix="/artifact")


def _to_metadata(artifact: Artifact) -> Dict[str, Any]:
    """Return ArtifactMetadata { name, id, type }."""
    art_type = getattr(artifact, "type", None) or "model"
    return {"name": artifact.name, "id": str(artifact.id), "type": art_type}


def _to_envelope(artifact: Artifact) -> Dict[str, Any]:
    """Return { metadata, data } envelope for an artifact."""
    url = artifact.source_url or ""
    show_url = url.startswith(("http://", "https://", "file://"))
    return {
        "metadata": _to_metadata(artifact),
        "data": {"url": url if show_url else None},
    }


def _validate_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _compute_duplicate(
    session: Any, artifact_type: str, name: str, url: str
) -> Optional[Artifact]:
    """Detect duplicates by same source_url or same name within a type."""
    query = session.query(Artifact).filter(Artifact.type == artifact_type)
    duplicate = (
        query.filter(Artifact.source_url == url).first()
        or query.filter(Artifact.name == name).first()
    )
    return cast(Optional[Artifact], duplicate)


def _trigger_ingestion_lambda(artifact_id: int) -> None:
    """Trigger async ingestion via Lambda in prod environments."""
    import json

    import boto3

    lambda_client = boto3.client(
        "lambda", region_name=os.environ.get("AWS_REGION", "us-east-2")
    )
    func_name = os.environ.get("INGESTION_LAMBDA_NAME")
    if not func_name:
        raise RuntimeError("INGESTION_LAMBDA_NAME not set for Lambda trigger")

    lambda_client.invoke(
        FunctionName=func_name,
        InvocationType="Event",
        Payload=json.dumps({"artifact_id": artifact_id}).encode("utf-8"),
    )


@bp_artifacts.post("")
def artifacts_list() -> ResponseReturnValue:
    """List artifacts matching the provided queries."""
    body: Any = request.get_json(silent=True)
    if body is None:
        raw = request.get_data(cache=False, as_text=True)
        if raw:
            try:
                import json

                body = json.loads(raw)
            except Exception:
                body = None

    if isinstance(body, dict):
        body = [body]

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

    offset_raw = request.args.get("offset")
    if offset_raw is None:
        offset_raw = request.headers.get("offset", "0")
    try:
        offset = max(0, int(offset_raw or "0"))
    except ValueError:
        return jsonify({"error": "bad offset"}), HTTPStatus.BAD_REQUEST

    names: List[str] = []
    types: Set[str] = set()
    for query in body:
        if not isinstance(query, dict) or "name" not in query:
            return jsonify({"error": "invalid ArtifactQuery"}), HTTPStatus.BAD_REQUEST
        names.append(str(query["name"]))
        for artifact_type in query.get("types") or []:
            types.add(str(artifact_type))

    with orm_session() as session:
        stmt = session.query(Artifact).order_by(Artifact.id.desc())
        if names and not (len(names) == 1 and names[0] == "*"):
            stmt = stmt.filter(Artifact.name.in_(names))
        if types:
            stmt = stmt.filter(Artifact.type.in_(list(types)))

        rows = stmt.offset(offset).limit(100).all()
        items: List[Dict[str, Any]] = [_to_metadata(artifact) for artifact in rows]

    resp = make_response(jsonify(items), HTTPStatus.OK)
    resp.headers["offset"] = str(offset + len(items))
    return resp


@bp_artifacts.get("/<artifact_type>/<int:artifact_id>")
def artifact_get(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
    """Return artifact envelope by type and ID."""
    with orm_session() as session:
        artifact = session.get(Artifact, artifact_id)
        if artifact is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND
        if artifact.type != artifact_type:
            return jsonify({"error": "type mismatch"}), HTTPStatus.BAD_REQUEST
        return jsonify(_to_envelope(artifact)), HTTPStatus.OK


@bp_artifacts.put("/<artifact_type>/<int:artifact_id>")
def artifact_put(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
    """Update artifact contents by type and ID."""
    body = cast(Dict[str, Any], request.get_json(force=True, silent=True) or {})
    metadata = cast(Dict[str, Any], body.get("metadata") or {})
    data = cast(Dict[str, Any], body.get("data") or {})

    ids_mismatch = str(metadata.get("id")) != str(artifact_id)
    type_mismatch = metadata.get("type") != artifact_type
    if ids_mismatch or type_mismatch:
        return jsonify({"error": "name/id/type mismatch"}), HTTPStatus.BAD_REQUEST

    with orm_session() as session:
        artifact = session.get(Artifact, artifact_id)
        if artifact is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        name = metadata.get("name")
        if isinstance(name, str) and name.strip():
            normalized = re.sub(r"\s+", "_", name.strip())
            artifact.name = normalized

        url = data.get("url")
        if isinstance(url, str) and url.strip():
            artifact.source_url = url

        session.flush()
        session.commit()
        return jsonify({"message": "updated"}), HTTPStatus.OK


@bp_artifacts.delete("/<artifact_type>/<int:artifact_id>")
def artifact_delete(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
    """Delete artifact by type and ID."""
    with orm_session() as session:
        artifact = session.get(Artifact, artifact_id)
        if artifact is None:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

        if artifact.type != artifact_type:
            return jsonify({"error": "type mismatch"}), HTTPStatus.BAD_REQUEST

        session.delete(artifact)
        session.commit()
        return jsonify({"message": "deleted"}), HTTPStatus.OK


@bp_artifact.post("/<artifact_type>")
def artifact_create(artifact_type: str) -> tuple[Response, HTTPStatus]:
    """Register a new artifact by providing a downloadable source url."""
    # auth_err = _require_auth()
    # if auth_err is not None:
    #     return auth_err

    body = cast(Dict[str, Any], request.get_json(force=True, silent=True) or {})
    url_raw = body.get("url")
    if not isinstance(url_raw, str) or not url_raw.strip():
        print(f"artifact_create: missing url for type={artifact_type}")
        return jsonify({"error": "missing url"}), HTTPStatus.BAD_REQUEST
    url = url_raw.strip()
    if not _validate_http_url(url):
        print(f"artifact_create: invalid url for type={artifact_type} url={url}")
        return jsonify({"error": "invalid url"}), HTTPStatus.BAD_REQUEST

    provided_name = body.get("name")
    if isinstance(provided_name, str) and provided_name:
        artifact_name = provided_name
    else:
        artifact_name = artifact_name_from_url(url)

    with orm_session() as session:
        duplicate = _compute_duplicate(session, artifact_type, artifact_name, url)
        if duplicate:
            print(
                f"artifact_create: duplicate detected type={artifact_type} "
                f"url={url} id={duplicate.id}"
            )
            return jsonify(_to_envelope(duplicate)), HTTPStatus.CONFLICT

        artifact = Artifact(
            name=artifact_name,
            type=artifact_type,
            source_url=url,
        )
        session.add(artifact)
        session.flush()
        session.commit()
        print(
            f"artifact_create: created artifact id={artifact.id} "
            f"type={artifact_type} name={artifact_name} url={url}"
        )

        env = os.getenv("APP_ENV", "dev").lower()
        status_code = HTTPStatus.CREATED
        response_body: Response = jsonify(_to_envelope(artifact))
        try:
            if env in {"dev", "test"}:
                status = ingest_artifact(
                    artifact.id
                )  # worker will manage status updates
                print(f"artifact_create: ingestion started locally id={artifact.id}")
                session.refresh(artifact)
                status = status or artifact.status
                if status == ArtifactStatus.rejected:
                    return (
                        jsonify(
                            {
                                "error": (
                                    "Artifact is not registered due to the "
                                    "disqualified rating."
                                )
                            }
                        ),
                        HTTPStatus.FAILED_DEPENDENCY,
                    )
            elif env == "prod":
                _trigger_ingestion_lambda(artifact.id)
                status_code = HTTPStatus.ACCEPTED
                print(f"artifact_create: ingestion lambda triggered id={artifact.id}")
        except Exception:
            raise
        return response_body, status_code


@bp_artifact.post("/byRegEx")
def artifact_by_regex() -> ResponseReturnValue:
    """Search artifacts by regex token over names."""
    body = cast(Dict[str, Any], request.get_json(force=True, silent=True) or {})
    regex_val = body.get("regex")
    if not isinstance(regex_val, str) or not regex_val.strip():
        return jsonify({"error": "missing regex"}), HTTPStatus.BAD_REQUEST

    token = regex_val.replace(".*", "").strip("%")
    with orm_session() as session:
        rows = (
            session.query(Artifact)
            .filter(Artifact.name.ilike(f"%{token}%"))
            .order_by(Artifact.id.desc())
            .limit(200)
            .all()
        )
        items: List[Dict[str, Any]] = [_to_metadata(artifact) for artifact in rows]
        return jsonify(items), HTTPStatus.OK


@bp_artifact.get("/byName/<name>")
def artifact_by_name(name: str) -> ResponseReturnValue:
    """List artifact metadata by exact name."""
    with orm_session() as session:
        rows = (
            session.query(Artifact)
            .filter(Artifact.name == name)
            .order_by(Artifact.id.desc())
            .all()
        )
        items: List[Dict[str, Any]] = [_to_metadata(artifact) for artifact in rows]
        if not items:
            return jsonify({"error": "no such artifact"}), HTTPStatus.NOT_FOUND
        return jsonify(items), HTTPStatus.OK
