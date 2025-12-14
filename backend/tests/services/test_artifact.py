"""Tests for artifact cost service."""

from __future__ import annotations

from types import SimpleNamespace, TracebackType
from typing import Any, Optional

import pytest

from app.db.models import Artifact
from app.services import artifact as cost_service


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
    """Returns cost values when artifact exists without deps."""
    artifact = Artifact(id=1, name="demo", type="model", source_url="http://x")
    artifact.size_bytes = 256
    fake_session = FakeSession()

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)

    costs = cost_service.compute_artifact_cost(1, include_dependencies=True)
    assert costs[1].total_cost == 256.0
    assert costs[1].standalone_cost == 256.0


def test_compute_artifact_cost_with_dependencies(monkeypatch: Any) -> None:
    """Sums dependency sizes when dependency flag set."""
    main = Artifact(
        id=1,
        name="demo",
        type="model",
        source_url="http://x",
        dataset_id=2,
        code_id=3,
    )
    dataset = Artifact(id=2, name="ds", type="dataset", source_url="http://ds")
    code = Artifact(id=3, name="code", type="code", source_url="http://code")
    main.size_bytes = 100
    dataset.size_bytes = 25
    code.size_bytes = 50
    main.dataset = dataset
    main.code = code
    fake_session = FakeSession()

    artifacts = {1: main, 2: dataset, 3: code}

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(
        cost_service, "get_artifact_by_id", lambda s, i: artifacts.get(i)
    )

    costs = cost_service.compute_artifact_cost(1, include_dependencies=True)
    assert costs[1].standalone_cost == 100
    assert costs[1].total_cost == 175
    assert costs[2].total_cost == 25
    assert costs[3].total_cost == 50


def test_compute_artifact_cost_invalid_type(monkeypatch: Any) -> None:
    """Raises when artifact type is invalid."""
    with pytest.raises(cost_service.InvalidArtifactIdError):
        cost_service.compute_artifact_cost(0)


def test_compute_artifact_cost_invalid_id(monkeypatch: Any) -> None:
    """Raises when artifact id is invalid."""
    with pytest.raises(cost_service.InvalidArtifactIdError):
        cost_service.compute_artifact_cost(0)


def test_compute_artifact_cost_not_found(monkeypatch: Any) -> None:
    """Raises not found when artifact missing."""
    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(FakeSession()))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: None)

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.compute_artifact_cost(1)


def test_compute_artifact_cost_type_mismatch(monkeypatch: Any) -> None:
    """Raises not found when stored artifact type mismatches because size missing."""
    artifact = Artifact(id=1, name="demo", type="dataset", source_url="http://x")
    artifact.size_bytes = None
    fake_session = FakeSession()

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.compute_artifact_cost(1)


def test_compute_artifact_cost_missing_size(monkeypatch: Any) -> None:
    """Raises not found when size is missing."""
    artifact = Artifact(id=1, name="demo", type="model", source_url="http://x")
    artifact.size_bytes = None
    fake_session = FakeSession()

    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.compute_artifact_cost(1)


# License checks


def _patch_license_session(
    monkeypatch: pytest.MonkeyPatch, artifact: Optional[Artifact]
) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(cost_service, "orm_session", lambda: FakeCtx(fake_session))
    monkeypatch.setattr(cost_service, "get_artifact_by_id", lambda s, i: artifact)


def test_check_license_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns True when licenses are compatible."""
    artifact = Artifact(id=1, name="m", type="model", source_url="http://x")
    artifact.license = "mit"
    _patch_license_session(monkeypatch, artifact)
    monkeypatch.setattr(
        cost_service,
        "fetch_github_license",
        lambda url: SimpleNamespace(spdx_id="apache-2.0"),
    )

    result = cost_service.check_model_license_compatibility(
        1, "https://github.com/org/repo"
    )
    assert result is True


def test_check_license_invalid_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raises on malformed github_url."""
    artifact = Artifact(id=1, name="m", type="model", source_url="http://x")
    artifact.license = "mit"
    _patch_license_session(monkeypatch, artifact)

    with pytest.raises(cost_service.InvalidLicenseRequestError):
        cost_service.check_model_license_compatibility(1, "")


def test_check_license_missing_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raises when artifact not found."""
    _patch_license_session(monkeypatch, None)

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.check_model_license_compatibility(
            99, "https://github.com/org/repo"
        )


def test_check_license_missing_license(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns False when artifact lacks license."""
    artifact = Artifact(id=1, name="m", type="model", source_url="http://x")
    artifact.license = None
    _patch_license_session(monkeypatch, artifact)

    result = cost_service.check_model_license_compatibility(
        1, "https://github.com/org/repo"
    )
    assert result is False


def test_check_license_repo_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """RepoNotFound surfaces as ArtifactNotFoundError."""  # noqa: D403
    artifact = Artifact(id=1, name="m", type="model", source_url="http://x")
    artifact.license = "mit"
    _patch_license_session(monkeypatch, artifact)
    monkeypatch.setattr(
        cost_service,
        "fetch_github_license",
        lambda url: (_ for _ in ()).throw(cost_service.RepoNotFound("nf")),
    )

    with pytest.raises(cost_service.ArtifactNotFoundError):
        cost_service.check_model_license_compatibility(1, "https://github.com/org/repo")


def test_check_license_incompatible(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns False when licenses conflict."""
    artifact = Artifact(id=1, name="m", type="model", source_url="http://x")
    artifact.license = "mit"
    _patch_license_session(monkeypatch, artifact)
    monkeypatch.setattr(
        cost_service,
        "fetch_github_license",
        lambda url: SimpleNamespace(spdx_id="gpl-3.0"),
    )

    result = cost_service.check_model_license_compatibility(
        1, "https://github.com/org/repo"
    )
    assert result is False
