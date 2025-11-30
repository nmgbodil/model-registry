"""API tests for artifact cost endpoint."""

from __future__ import annotations

from unittest import mock

import pytest
from flask import Flask

from app import create_app
from app.api import artifact as artifact_api
from app.schemas.artifact import ArtifactCost
from app.services.artifact_cost import (
    ArtifactCostError,
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    InvalidArtifactTypeError,
)


@pytest.fixture()
def flask_app() -> Flask:
    """Provide a test application instance."""
    app = create_app()
    app.config["TESTING"] = True
    return app


def test_get_artifact_cost_success(
    flask_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns cost payload when service succeeds."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        lambda artifact_type, artifact_id, include_dependencies=False: ArtifactCost(
            total_cost=123.0, standalone_cost=None
        ),
    )
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/5/cost")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["5"]["total_cost"] == 123.0
    assert "standalone_cost" not in payload["5"]


def test_get_artifact_cost_with_dependency_flag(
    flask_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Includes standalone_cost when dependency flag true."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        lambda artifact_type, artifact_id, include_dependencies=False: ArtifactCost(
            total_cost=200.0, standalone_cost=100.0
        ),
    )
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/5/cost?dependency=true")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["5"]["standalone_cost"] == 100.0


def test_get_artifact_cost_invalid_dependency(flask_app: Flask) -> None:
    """Returns 400 for invalid dependency flag."""
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/5/cost?dependency=maybe")
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "exc_class",
    [InvalidArtifactIdError, InvalidArtifactTypeError],
)
def test_get_artifact_cost_bad_request(
    flask_app: Flask, monkeypatch: pytest.MonkeyPatch, exc_class: type[Exception]
) -> None:
    """Returns 400 for invalid inputs."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        mock.MagicMock(side_effect=exc_class("bad input")),
    )
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/0/cost")
    assert resp.status_code == 400


def test_get_artifact_cost_not_found(
    flask_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Returns 404 when artifact missing."""
    monkeypatch.setattr(
        artifact_api,
        "compute_artifact_cost",
        mock.MagicMock(side_effect=ArtifactNotFoundError("Artifact does not exist.")),
    )
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/10/cost")
    assert resp.status_code == 404


def test_get_artifact_cost_unexpected_error(
    flask_app: Flask, monkeypatch: pytest.MonkeyPatch
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
    client = flask_app.test_client()
    resp = client.get("/api/artifact/model/10/cost")
    assert resp.status_code == 500
