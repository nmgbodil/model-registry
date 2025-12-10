"""Tests for health endpoints."""

from __future__ import annotations

import json

from flask import Flask

from app import create_app


def _disable_jwt(app: Flask) -> None:
    from flask_jwt_extended import view_decorators

    view_decorators.verify_jwt_in_request = lambda *args, **kwargs: None
    # ensure role checks succeed
    import app.utils as utils

    utils.get_user_role_from_token = lambda: "admin"
    utils.role_allowed = lambda allowed: True  # type: ignore[assignment]


def test_health_ok() -> None:
    """Test the /health endpoint returns expected data."""
    app = create_app()
    _disable_jwt(app)
    client = app.test_client()

    response = client.get("/api/health")
    assert response.status_code == 200

    body = json.loads(response.data.decode("utf-8"))
    assert body["status"] == "ok"
    assert "uptime_s" in body
