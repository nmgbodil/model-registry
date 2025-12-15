"""Tests for artifact audit endpoints and audit logging hooks."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import create_app
from app.db.models import ArtifactStatus


@pytest.fixture()
def flask_app() -> Flask:
    """Provide a test application instance."""
    import os

    os.environ["JWT_SECRET_KEY"] = "test-secret"
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def auth_headers(flask_app: Flask) -> dict[str, str]:
    """Provide authorization headers with a test JWT."""
    with flask_app.app_context():
        token = create_access_token(identity="test-user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def disable_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass JWT verification and limiter for audit tests."""
    monkeypatch.setattr(
        "flask_jwt_extended.view_decorators.verify_jwt_in_request",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("app.utils.get_user_role_from_token", lambda: "admin")
    monkeypatch.setattr("app.utils.get_user_id_from_token", lambda: "test-user")
    monkeypatch.setattr("app.auth.api_request_limiter.get_jwt", lambda: {"tid": "t"})
    monkeypatch.setattr(
        "app.auth.api_request_limiter.APIRequestLimiter.increment", lambda self, tid: 1
    )


def test_get_artifact_audit_success(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns audit entries when service succeeds."""
    sample_entries = [
        {
            "user": {"name": "alice", "is_admin": False},
            "date": "2025-01-01T00:00:00",
            "artifact": {"name": "model-a", "id": 1, "type": "model"},
            "action": "CREATE",
        }
    ]
    monkeypatch.setattr("app.api.artifact.role_allowed", lambda roles: True)
    monkeypatch.setattr(
        "app.api.artifact.get_artifact_audit_entries",
        lambda *args, **kwargs: sample_entries,
    )

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/1/audit", headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json() == sample_entries


def test_get_artifact_audit_forbidden(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns 403 when user not admin."""
    monkeypatch.setattr("app.api.artifact.role_allowed", lambda roles: False)

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/1/audit", headers=auth_headers)

    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert resp.get_json()["error"] == "forbidden"


def test_get_artifact_audit_bad_request(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns 400 for invalid artifact input."""
    from app.services.artifact import InvalidArtifactIdError

    monkeypatch.setattr("app.api.artifact.role_allowed", lambda roles: True)
    monkeypatch.setattr(
        "app.api.artifact.get_artifact_audit_entries",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(InvalidArtifactIdError("bad")),
    )

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/0/audit", headers=auth_headers)

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_get_artifact_audit_not_found(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns 404 when audit target missing."""
    from app.services.artifact import ArtifactNotFoundError

    monkeypatch.setattr("app.api.artifact.role_allowed", lambda roles: True)
    monkeypatch.setattr(
        "app.api.artifact.get_artifact_audit_entries",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ArtifactNotFoundError("missing")
        ),
    )

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/99/audit", headers=auth_headers)

    assert resp.status_code == HTTPStatus.NOT_FOUND


# --- Logging side effects on artifact endpoints ---


class FakeSession:
    """Minimal session to support artifact endpoints."""

    def __init__(self, artifact: Any) -> None:
        self.artifact = artifact
        self.deleted: list[Any] = []
        self.committed = False

    def get(self, model: object, artifact_id: int) -> Any:
        """Return artifact by id."""
        return self.artifact

    def delete(self, obj: Any) -> None:
        """Record deleted artifact."""
        self.deleted.append(obj)

    def add(self, obj: Any) -> None:
        """Assign artifact."""
        self.artifact = obj

    def flush(self) -> None:
        """Assign an id when missing."""
        if getattr(self.artifact, "id", None) is None:
            setattr(self.artifact, "id", 1)

    def begin(self) -> "FakeSession":
        """Context manager entry."""
        return self

    def __enter__(self) -> "FakeSession":
        """Enter context."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[object],
    ) -> None:
        """Exit context."""
        return None

    def refresh(self, obj: Any) -> None:
        """No-op refresh for compatibility."""
        return None

    def commit(self) -> None:
        """No-op commit for compatibility."""
        return None


class FakeArtifact:
    """Simple artifact holder with mutable fields."""

    def __init__(
        self,
        artifact_id: int = 1,
        artifact_type: str = "model",
        name: str = "artifact-a",
        source_url: str = "https://example.com",
        created_by: str | None = "test-user",
    ) -> None:
        self.id = artifact_id
        self.type = artifact_type
        self.name = name
        self.source_url = source_url
        self.created_by = created_by
        self.status = ArtifactStatus.accepted
        self.s3_key = "key"


def _common_monkeypatches(
    monkeypatch: pytest.MonkeyPatch, log_sink: List[Dict[str, Any]]
) -> None:
    """Patch shared helpers for artifact API calls."""
    monkeypatch.setattr("app.api.routes_artifacts.role_allowed", lambda roles: True)
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_user_id_from_token", lambda: "test-user"
    )
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_request_context",
        lambda: {"request_ip": "1.1.1.1", "user_agent": "ua"},
    )
    monkeypatch.setattr(
        "app.api.routes_artifacts._wait_for_ingestion",
        lambda _aid, _timeout_seconds=0, _poll_seconds=0: ArtifactStatus.accepted,
    )
    monkeypatch.setattr(
        "app.api.routes_artifacts.generate_presigned_url",
        lambda key: "https://download" if key else None,
    )
    monkeypatch.setattr(
        "app.api.routes_artifacts.ingest_artifact", lambda aid: ArtifactStatus.accepted
    )
    monkeypatch.setattr(
        "app.api.routes_artifacts._compute_duplicate", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("app.auth.api_request_limiter.get_jwt", lambda: {"tid": "t"})
    monkeypatch.setattr(
        "app.auth.api_request_limiter.APIRequestLimiter.increment", lambda self, tid: 1
    )

    def _log_event(**kwargs: Any) -> None:
        log_sink.append(kwargs)

    monkeypatch.setattr("app.api.routes_artifacts.log_artifact_event", _log_event)


def test_artifact_create_emits_audit(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """CREATE action logged on artifact creation."""
    logs: List[Dict[str, Any]] = []
    artifact = FakeArtifact(artifact_id=1)
    monkeypatch.setattr(
        "app.api.routes_artifacts.orm_session", lambda: FakeSession(artifact)
    )
    _common_monkeypatches(monkeypatch, logs)

    client = flask_app.test_client()
    resp = client.post(
        "/api/artifact/model",
        json={"url": "https://example.com", "name": "artifact-a"},
        headers=auth_headers,
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert any(
        log["action"] == "CREATE" and log["artifact_id"] == artifact.id for log in logs
    )


def test_artifact_put_logs_updates(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """UPDATE_NAME and UPDATE_CONTENT actions logged on update."""
    logs: List[Dict[str, Any]] = []
    artifact = FakeArtifact(artifact_id=2, name="old-name")

    monkeypatch.setattr(
        "app.api.routes_artifacts.orm_session", lambda: FakeSession(artifact)
    )
    _common_monkeypatches(monkeypatch, logs)

    client = flask_app.test_client()
    resp = client.put(
        "/api/artifacts/model/2",
        json={
            "metadata": {"id": 2, "type": "model", "name": "new-name"},
            "data": {"url": "https://new", "refresh": True},
        },
        headers=auth_headers,
    )

    assert resp.status_code == HTTPStatus.OK
    assert {"UPDATE_NAME", "UPDATE_CONTENT"} <= {log["action"] for log in logs}
    assert all(log["artifact_id"] == artifact.id for log in logs)


def test_artifact_delete_logs_delete(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """DELETE action logged on removal."""
    logs: List[Dict[str, Any]] = []
    artifact = FakeArtifact(artifact_id=3)
    monkeypatch.setattr(
        "app.api.routes_artifacts.orm_session", lambda: FakeSession(artifact)
    )
    _common_monkeypatches(monkeypatch, logs)

    client = flask_app.test_client()
    resp = client.delete("/api/artifacts/model/3", headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert any(
        log["action"] == "DELETE" and log["artifact_id"] == artifact.id for log in logs
    )


def test_artifact_get_logs_download(
    flask_app: Flask, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """DOWNLOAD action logged when download_url present."""
    logs: List[Dict[str, Any]] = []
    artifact = FakeArtifact(artifact_id=4)
    monkeypatch.setattr(
        "app.api.routes_artifacts.orm_session", lambda: FakeSession(artifact)
    )
    _common_monkeypatches(monkeypatch, logs)

    client = flask_app.test_client()
    resp = client.get("/api/artifacts/model/4", headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert any(
        log["action"] == "DOWNLOAD" and log["artifact_id"] == artifact.id
        for log in logs
    )
