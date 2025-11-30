"""Tests for ingestion worker Lambda handler."""

from __future__ import annotations

from typing import Any, Dict

from app.db.models import ArtifactStatus
from app.workers.ingestion_worker import handler


class _FakeContext:
    """Placeholder context object."""


def test_lambda_handler_success(monkeypatch: Any) -> None:
    """Returns status when ingestion succeeds."""
    called_with: Dict[str, Any] = {}

    def fake_ingest(artifact_id: int) -> ArtifactStatus:
        called_with["artifact_id"] = artifact_id
        return ArtifactStatus.accepted

    monkeypatch.setattr(handler, "ingest_artifact", fake_ingest)

    event = {"artifact_id": "123"}
    result = handler.lambda_handler(event, _FakeContext())

    assert result == {"artifact_id": 123, "status": ArtifactStatus.accepted.value}
    assert called_with["artifact_id"] == 123


def test_lambda_handler_missing_artifact_id(monkeypatch: Any) -> None:
    """Errors when artifact_id missing."""
    monkeypatch.setattr(handler, "ingest_artifact", lambda _: ArtifactStatus.accepted)

    result = handler.lambda_handler({}, _FakeContext())

    assert result == {"error": "artifact_id is required"}


def test_lambda_handler_invalid_artifact_id(monkeypatch: Any) -> None:
    """Errors when artifact_id is not an int."""
    result = handler.lambda_handler({"artifact_id": "not-an-int"}, _FakeContext())

    assert result["artifact_id"] == "not-an-int"
    assert "error" in result


def test_lambda_handler_value_error(monkeypatch: Any) -> None:
    """Returns ValueError message when ingest raises ValueError."""

    def fake_ingest(_: int) -> ArtifactStatus:
        raise ValueError("boom")

    monkeypatch.setattr(handler, "ingest_artifact", fake_ingest)

    result = handler.lambda_handler({"artifact_id": 5}, _FakeContext())

    assert result == {"artifact_id": 5, "error": "boom"}
