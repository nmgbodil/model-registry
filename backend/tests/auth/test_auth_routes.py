"""Integration-style tests for auth HTTP routes."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest
from flask import Flask, testing

from app import create_app
from app.auth.auth_services import AuthenticationFailedError, UsernameTakenError


@pytest.fixture()
def flask_app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    """Create a Flask app configured for testing."""
    app = create_app()
    app.config.update({"TESTING": True})

    # Avoid hitting real Redis in tests by stubbing the limiter.
    class DummyLimiter:
        def increment(self, token_id: str) -> int:
            return 1

    app.config["API_REQUEST_LIMITER"] = DummyLimiter()
    return app


@pytest.fixture()
def client(flask_app: Flask) -> testing.FlaskClient:
    """Provide a test client."""
    return flask_app.test_client()


def test_register_endpoint_success(
    client: testing.FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return created user on successful registration."""
    expected = {"id": "u1", "username": "newuser"}
    monkeypatch.setattr("app.auth.routes.register_user", lambda u, p: expected)

    resp = client.post(
        "/api/register", json={"username": "newuser", "password": "GoodP@ss1"}
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.get_json() == expected


def test_register_endpoint_bad_payload(client: testing.FlaskClient) -> None:
    """Reject missing password."""
    resp = client.post("/api/register", json={"username": "missingpass"})

    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "Invalid registration payload."


def test_register_endpoint_conflict(
    client: testing.FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return conflict when username taken."""

    def raise_conflict(username: str, password: str) -> dict[str, Any]:
        raise UsernameTakenError("taken")

    monkeypatch.setattr("app.auth.routes.register_user", raise_conflict)

    resp = client.post(
        "/api/register", json={"username": "new", "password": "GoodP@ss1"}
    )

    assert resp.status_code == HTTPStatus.CONFLICT
    assert resp.get_json()["error"] == "taken"


def test_authenticate_endpoint_success(
    client: testing.FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return token when authentication succeeds."""
    monkeypatch.setattr(
        "app.auth.routes.authenticate_user", lambda u, p: "bearer token123"
    )

    resp = client.put(
        "/api/authenticate",
        json={"user": {"name": "u"}, "secret": {"password": "p"}},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json() == "bearer token123"


def test_authenticate_endpoint_bad_payload(client: testing.FlaskClient) -> None:
    """Reject malformed auth payload."""
    resp = client.put("/api/authenticate", json={"user": {}, "secret": {}})

    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "Invalid authentication payload."


def test_authenticate_endpoint_failure(
    client: testing.FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return 401 when authentication fails."""

    def raise_auth(username: str, password: str) -> str:
        raise AuthenticationFailedError("bad creds")

    monkeypatch.setattr("app.auth.routes.authenticate_user", raise_auth)

    resp = client.put(
        "/api/authenticate",
        json={"user": {"name": "u"}, "secret": {"password": "p"}},
    )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert resp.get_json()["error"] == "bad creds"
