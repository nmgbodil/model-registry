"""Tests for artifact cost service."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Optional

import pytest

from app.db.models import Artifact
from app.services import artifact_cost as cost_service


class FakeSession:
    """Simple fake session placeholder."""


class FakeCtx:
    """Context manager that yields a provided session."""

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def __enter__(self) -> FakeSession:
        """Enter context."""
        return self.session

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        """Exit context."""
        return None


def test_compute_artifact_cost_success(monkeypatch: Any) -> None:
    """Returns cost values when artifact exists."""
    artifact = Artifact(id=1, name="demo", type="model", source_url="http://x")
    fake_session = FakeSession()

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)
    monkeypatch.setattr(cost_service, "get_artifact_size", lambda s, i: 256)

    cost = cost_service.compute_artifact_cost("model", 1, include_dependencies=True)
    assert cost.total_cost == 256.0
    assert cost.standalone_cost == 256.0


def test_compute_artifact_cost_invalid_type(monkeypatch: Any) -> None:
    """Raises when artifact type is invalid."""
    with pytest.raises(cost_service.InvalidArtifactTypeError):
        cost_service.compute_artifact_cost("invalid", 1)


def test_compute_artifact_cost_invalid_id(monkeypatch: Any) -> None:
    """Raises when artifact id is invalid."""
    with pytest.raises(cost_service.InvalidArtifactIdError):
        cost_service.compute_artifact_cost("model", 0)


def test_compute_artifact_cost_not_found(monkeypatch: Any) -> None:
    """Raises not found when artifact missing."""
    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(FakeSession()))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: None)

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.compute_artifact_cost("model", 1)


def test_compute_artifact_cost_type_mismatch(monkeypatch: Any) -> None:
    """Raises invalid type when stored artifact type mismatches."""
    artifact = Artifact(id=1, name="demo", type="dataset", source_url="http://x")
    fake_session = FakeSession()

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)

    with pytest.raises(cost_service.InvalidArtifactTypeError):
        cost_service.compute_artifact_cost("model", 1)


def test_compute_artifact_cost_missing_size(monkeypatch: Any) -> None:
    """Raises not found when size is missing."""
    artifact = Artifact(id=1, name="demo", type="model", source_url="http://x")
    fake_session = FakeSession()

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)
    monkeypatch.setattr(cost_service, "get_artifact_size", lambda s, i: None)

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.compute_artifact_cost("model", 1)
