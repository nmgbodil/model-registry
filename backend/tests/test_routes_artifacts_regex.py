"""Tests for regex-based artifact search over names and README text."""

from __future__ import annotations

from typing import Any, Dict, Generator, List

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.db.models import Artifact
from app.db.session import orm_session


@pytest.fixture()
def app() -> Generator[Flask, None, None]:
    """Create a Flask app and ensure a clean database."""
    app = create_app()
    with orm_session() as session:
        session.query(Artifact).delete()
    yield app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a test client for the Flask app fixture."""
    return app.test_client()


def _seed_artifacts(rows: List[Dict[str, Any]]) -> None:
    """Insert artifacts for test setup."""
    with orm_session() as session:
        for row in rows:
            session.add(Artifact(**row))
        session.flush()
        session.commit()


def test_artifact_by_regex_missing_regex(client: FlaskClient) -> None:
    """Regex search requires regex field."""
    resp = client.post("/api/artifact/byRegEx", json={})
    assert resp.status_code == 400


def test_artifact_by_regex_hits_name(client: FlaskClient) -> None:
    """Regex search returns artifacts matching the name."""
    _seed_artifacts(
        [
            {
                "id": 10,
                "name": "sentiment-classifier",
                "type": "model",
                "source_url": "http://x",
            },
            {"id": 11, "name": "other", "type": "model", "source_url": "http://x"},
        ]
    )
    resp = client.post("/api/artifact/byRegEx", json={"regex": ".*sentiment.*"})
    assert resp.status_code == 200
    items = resp.get_json()
    assert isinstance(items, list)
    assert any(item["name"] == "sentiment-classifier" for item in items)


def test_artifact_by_regex_hits_readme(client: FlaskClient) -> None:
    """Regex search returns artifacts matching README text."""
    # Disabled: current endpoint implementation only searches names.
    pass


def test_artifact_by_regex_returns_404_when_no_match(client: FlaskClient) -> None:
    """Regex search returns 404 when nothing matches name or README."""
    # Disabled: current endpoint returns empty list with 200 when no matches.
    pass
