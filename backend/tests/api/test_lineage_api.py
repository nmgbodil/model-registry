"""API tests for artifact lineage endpoint."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import create_app
from app.auth.api_request_limiter import MAX_CALLS
from app.schemas.lineage import Edge, Graph, Node
from app.services.lineage import (
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    LineageServiceError,
)


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
    """Bypass JWT and limiter for lineage API tests."""
    monkeypatch.setattr(
        "flask_jwt_extended.view_decorators.verify_jwt_in_request",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("app.utils.get_user_role_from_token", lambda: "admin")
    monkeypatch.setattr("app.utils.get_user_id_from_token", lambda: "test-user")
    monkeypatch.setattr("app.auth.api_request_limiter.get_jwt", lambda: {"tid": "t"})
    monkeypatch.setattr(
        "app.auth.api_request_limiter.APIRequestLimiter.increment",
        lambda self, token_id: 1 if token_id else MAX_CALLS + 1,
    )


def test_get_lineage_success(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns lineage graph when service succeeds."""
    graph = Graph(
        nodes=[
            Node(artifact_id=7, name="parent", source="config_json", metadata=None),
            Node(artifact_id=8, name="child", source="config_json", metadata=None),
        ],
        edges=[
            Edge(
                from_node_artifact_id=7,
                to_node_artifact_id=8,
                relationship="child",
            )
        ],
    )
    monkeypatch.setattr("app.api.lineage.role_allowed", lambda roles: True)
    monkeypatch.setattr("app.api.lineage.get_lineage_graph", lambda _aid: graph)

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/7/lineage", headers=auth_headers)

    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json() == graph.model_dump()


def test_get_lineage_forbidden(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns 403 when role is not allowed."""
    monkeypatch.setattr("app.api.lineage.role_allowed", lambda roles: False)

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/7/lineage", headers=auth_headers)

    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert resp.get_json()["error"] == "forbidden"


def test_get_lineage_invalid_id(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns 400 for invalid artifact id."""
    monkeypatch.setattr("app.api.lineage.role_allowed", lambda roles: True)

    def raise_invalid(_aid: int) -> Graph:
        raise InvalidArtifactIdError("bad id")

    monkeypatch.setattr("app.api.lineage.get_lineage_graph", raise_invalid)

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/0/lineage", headers=auth_headers)

    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert "invalid" in resp.get_json()["error"].lower()


def test_get_lineage_not_found(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns 404 when artifact is missing."""
    monkeypatch.setattr("app.api.lineage.role_allowed", lambda roles: True)

    def raise_not_found(_aid: int) -> Graph:
        raise ArtifactNotFoundError("Artifact not found.")

    monkeypatch.setattr("app.api.lineage.get_lineage_graph", raise_not_found)

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/9/lineage", headers=auth_headers)

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.get_json()["error"] == "Artifact not found."


def test_get_lineage_service_error(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns 500 on lineage service failure."""
    monkeypatch.setattr("app.api.lineage.role_allowed", lambda roles: True)

    def raise_service_error(_aid: int) -> Graph:
        raise LineageServiceError("boom")

    monkeypatch.setattr("app.api.lineage.get_lineage_graph", raise_service_error)

    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/3/lineage", headers=auth_headers)

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "lineage system" in resp.get_json()["error"].lower()
