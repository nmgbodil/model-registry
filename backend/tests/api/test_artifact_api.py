"""API tests for artifact cost endpoint."""

from __future__ import annotations

from typing import Any, cast
from unittest import mock

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import create_app
from app.api import artifact as artifact_api
from app.db.models import ArtifactStatus
from app.schemas.artifact import ArtifactCost
from app.services.artifact import (
    ArtifactCostError,
    ArtifactNotFoundError,
    ExternalLicenseError,
    InvalidArtifactIdError,
    InvalidArtifactTypeError,
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
    return {"Authorization": f"Bearer {token}"}  # noqa: E501


@pytest.fixture(autouse=True)
def disable_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass JWT verification for API tests."""
    monkeypatch.setattr(
        "flask_jwt_extended.view_decorators.verify_jwt_in_request",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("app.utils.get_user_role_from_token", lambda: "admin")
    monkeypatch.setattr("app.utils.get_user_id_from_token", lambda: "test-user")
    monkeypatch.setattr(
        "app.auth.api_request_limiter.get_jwt",
        lambda: {"tid": "test-token"},
    )


def test_get_artifact_cost_success(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns cost payload when service succeeds."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        lambda artifact_id, include_dependencies=False: {
            5: ArtifactCost(total_cost=123.0, standalone_cost=None)
        },
    )

    def _accepted(
        _artifact_id: int,
        _timeout_seconds: float = 0,
        _poll_seconds: float = 0,
    ) -> ArtifactStatus:
        return ArtifactStatus.accepted

    monkeypatch.setattr(cast(Any, artifact_api), "_wait_for_ingestion", _accepted)
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/5/cost", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["5"]["total_cost"] == 123.0
    assert "standalone_cost" not in payload["5"]


def test_get_artifact_cost_with_dependency_flag(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Includes standalone_cost when dependency flag true."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        lambda artifact_id, include_dependencies=False: {
            5: ArtifactCost(total_cost=1255.0, standalone_cost=412.5),
            4628173590: ArtifactCost(total_cost=280.0, standalone_cost=280.0),
            5738291045: ArtifactCost(total_cost=562.5, standalone_cost=562.5),
        },
    )

    def _accepted(
        _artifact_id: int,
        _timeout_seconds: float = 0,
        _poll_seconds: float = 0,
    ) -> ArtifactStatus:
        return ArtifactStatus.accepted

    monkeypatch.setattr(cast(Any, artifact_api), "_wait_for_ingestion", _accepted)
    client = flask_app.test_client()
    resp = client.get(
        "/api/artifact/model/5/cost?dependency=true", headers=auth_headers
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["5"]["standalone_cost"] == 412.5
    assert payload["5"]["total_cost"] == 1255.0
    assert "4628173590" in payload and "5738291045" in payload


def test_get_artifact_cost_invalid_dependency(
    flask_app: Flask, auth_headers: dict[str, str]
) -> None:
    """Returns 400 for invalid dependency flag."""

    def _accepted(
        _artifact_id: int,
        _timeout_seconds: float = 0,
        _poll_seconds: float = 0,
    ) -> ArtifactStatus:
        return ArtifactStatus.accepted

    cast(Any, artifact_api)._wait_for_ingestion = _accepted
    client = flask_app.test_client()
    resp = client.get(
        "/api/artifact/model/5/cost?dependency=maybe", headers=auth_headers
    )
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "exc_class",
    [InvalidArtifactIdError, InvalidArtifactTypeError],
)
def test_get_artifact_cost_bad_request(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    exc_class: type[Exception],
) -> None:
    """Returns 400 for invalid inputs."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        mock.MagicMock(side_effect=exc_class("bad input")),
    )

    def _accepted(
        _artifact_id: int,
        _timeout_seconds: float = 0,
        _poll_seconds: float = 0,
    ) -> ArtifactStatus:
        return ArtifactStatus.accepted

    monkeypatch.setattr(cast(Any, artifact_api), "_wait_for_ingestion", _accepted)
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/0/cost", headers=auth_headers)
    assert resp.status_code == 400


def test_get_artifact_cost_not_found(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns 404 when artifact missing."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        mock.MagicMock(side_effect=ArtifactNotFoundError("Artifact does not exist.")),
    )
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/10/cost", headers=auth_headers)
    assert resp.status_code == 404


def test_get_artifact_cost_unexpected_error(
    flask_app: Flask,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns 500 when service raises unexpected cost error."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        mock.MagicMock(
            side_effect=ArtifactCostError(
                "The artifact cost calculator encountered an error."
            )
        ),
    )

    def _accepted(
        _artifact_id: int,
        _timeout_seconds: float = 0,
        _poll_seconds: float = 0,
    ) -> ArtifactStatus:
        return ArtifactStatus.accepted

    monkeypatch.setattr(cast(Any, artifact_api), "_wait_for_ingestion", _accepted)
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/10/cost", headers=auth_headers)
    assert resp.status_code == 500


def _setup_fake_model_artifact(
    monkeypatch: pytest.MonkeyPatch,
    license_name: str,
) -> None:
    """Patch license compatibility checks for a fake artifact."""
    monkeypatch.setattr(
        artifact_api,
        "check_model_license_compatibility",
        mock.MagicMock(return_value=True),
    )
    monkeypatch.setattr(
        artifact_api,
        "_wait_for_ingestion",
        lambda artifact_id: ArtifactStatus.accepted,
    )


def test_license_check_success_returns_boolean_true(
    flask_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """License check returns True for compatible licenses."""
    _setup_fake_model_artifact(monkeypatch, license_name="mit")

    client = flask_app.test_client()
    resp = client.post(
        "/api/artifact/model/1/license-check",
        json={"github_url": "https://github.com/google-research/bert"},
    )

    assert resp.status_code == 200
    assert resp.is_json
    assert resp.get_json() is True


def test_license_check_missing_github_url_returns_400(
    flask_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    """License check returns 400 when github_url is invalid."""
    client = flask_app.test_client()
    # ensure ingestion check passes to reach validation
    monkeypatch.setattr(
        cast(Any, artifact_api),
        "_wait_for_ingestion",
        lambda artifact_id, _timeout_seconds=0.0, _poll_seconds=0.0: (
            ArtifactStatus.accepted
        ),
    )

    resp = client.post(
        "/api/artifact/model/1/license-check",
        json={},
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/artifact/model/1/license-check",
        json={"github_url": 123},
    )
    assert resp.status_code == 400


def test_license_check_artifact_not_found_returns_404(
    flask_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """License check returns 404 when artifact does not exist."""
    monkeypatch.setattr(
        cast(Any, artifact_api),
        "_wait_for_ingestion",
        lambda artifact_id, _timeout_seconds=0.0, _poll_seconds=0.0: (
            ArtifactStatus.accepted
        ),
    )
    monkeypatch.setattr(
        artifact_api,
        "check_model_license_compatibility",
        mock.MagicMock(side_effect=ArtifactNotFoundError("Artifact does not exist.")),
    )

    client = flask_app.test_client()
    resp = client.post(
        "/api/artifact/model/999/license-check",
        json={"github_url": "https://github.com/google-research/bert"},
    )

    assert resp.status_code == 404
    assert resp.is_json
    assert "error" in resp.get_json()


def test_license_check_external_license_error_returns_502(
    flask_app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """License check returns 502 when GitHub license fetch fails."""
    monkeypatch.setattr(
        cast(Any, artifact_api),
        "_wait_for_ingestion",
        lambda artifact_id, _timeout_seconds=0.0, _poll_seconds=0.0: (
            ArtifactStatus.accepted
        ),
    )
    monkeypatch.setattr(
        artifact_api,
        "check_model_license_compatibility",
        mock.MagicMock(
            side_effect=ExternalLicenseError(
                "External license information could not be retrieved."
            )
        ),
    )

    client = flask_app.test_client()
    resp = client.post(
        "/api/artifact/model/1/license-check",
        json={"github_url": "https://github.com/google-research/bert"},
    )

    assert resp.status_code == 502
    assert resp.is_json
    body = resp.get_json()
    assert "error" in body
    assert "External license information could not be retrieved" in body["error"]
