"""Unit tests for artifact audit retrieval service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytest

from app.db.models import UserRole
from app.services.artifact import (
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    InvalidArtifactTypeError,
    get_artifact_audit_entries,
)
from tests.utils import fake_session_cm


@dataclass
class FakeArtifact:
    """Minimal artifact holder."""

    id: int
    type: str
    name: str


@dataclass
class FakeAuditLog:
    """Audit log row stand-in."""

    artifact_id: int
    artifact_type: str
    action: str
    user_id: Optional[str]
    occurred_at: datetime


@dataclass
class FakeUser:
    """User stand-in."""

    id: str
    username: str
    role: UserRole


def test_get_artifact_audit_entries_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return entries when artifact exists and types match."""
    artifact = FakeArtifact(id=1, type="model", name="artifact-a")
    audit_row = FakeAuditLog(
        artifact_id=1,
        artifact_type="model",
        action="CREATE",
        user_id="u1",
        occurred_at=datetime(2025, 1, 1, 0, 0, 0),
    )
    user = FakeUser(id="u1", username="alice", role=UserRole.admin)

    monkeypatch.setattr(
        "app.services.artifact.orm_session", lambda: fake_session_cm(object())
    )
    monkeypatch.setattr(
        "app.services.artifact.get_artifact_by_id", lambda session, aid: artifact
    )
    monkeypatch.setattr(
        "app.services.artifact.get_artifact_audit_log",
        lambda session, artifact_id, limit=50, offset=0: [audit_row],
    )
    monkeypatch.setattr(
        "app.services.artifact.get_user_by_id", lambda session, uid: user
    )

    entries = get_artifact_audit_entries("model", 1)

    assert len(entries) == 1
    entry = entries[0]
    assert entry["action"] == "CREATE"
    assert entry["artifact"]["id"] == 1
    assert entry["user"]["name"] == "alice"
    assert entry["user"]["is_admin"] is True
    assert entry["date"].startswith("2025-01-01")


def test_get_artifact_audit_entries_invalid_type() -> None:
    """Reject unsupported artifact type."""
    with pytest.raises(InvalidArtifactTypeError):
        get_artifact_audit_entries("unknown", 1)


def test_get_artifact_audit_entries_invalid_id() -> None:
    """Reject non-positive artifact id."""
    with pytest.raises(InvalidArtifactIdError):
        get_artifact_audit_entries("model", 0)


def test_get_artifact_audit_entries_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise when artifact missing."""
    monkeypatch.setattr(
        "app.services.artifact.orm_session", lambda: fake_session_cm(object())
    )
    monkeypatch.setattr(
        "app.services.artifact.get_artifact_by_id", lambda session, aid: None
    )

    with pytest.raises(ArtifactNotFoundError):
        get_artifact_audit_entries("model", 99)


def test_get_artifact_audit_entries_type_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise when artifact type mismatches requested type."""
    artifact = FakeArtifact(id=5, type="dataset", name="ds")
    monkeypatch.setattr(
        "app.services.artifact.orm_session", lambda: fake_session_cm(object())
    )
    monkeypatch.setattr(
        "app.services.artifact.get_artifact_by_id", lambda session, aid: artifact
    )

    with pytest.raises(InvalidArtifactTypeError):
        get_artifact_audit_entries("model", 5)
