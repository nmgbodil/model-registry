"""Tests for ingestion workflow logic."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Generator, Mapping, Optional, Tuple

from app.db.models import ArtifactStatus
from app.services.artifacts.model_fetcher import MODEL_PREVIEW_ALLOW
from app.workers.ingestion_worker import ingestion_logic as logic
from app.workers.ingestion_worker import metadata as ingestion_metadata
from tests.utils import make_artifact


class FakeSession:
    """Fake SQLAlchemy session for ingestion logic tests."""

    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        """Simulate commit."""
        self.committed = True

    def rollback(self) -> None:
        """Simulate rollback."""
        pass

    def close(self) -> None:
        """Simulate close."""
        pass


@contextmanager
def fake_session_cm(fake_session: FakeSession) -> Generator[FakeSession, None, None]:
    """Yield a provided fake session."""
    yield fake_session


def _good_rating() -> Mapping[str, Any]:
    """Return an ingestible rating payload."""
    return {
        "net_score": 0.9,
        "size_score": {
            "raspberry_pi": 1.0,
            "jetson_nano": 1.0,
            "desktop_pc": 1.0,
            "aws_server": 1.0,
        },
    }


def _bad_rating() -> Mapping[str, Any]:
    """Return a non-ingestible rating payload."""
    return {
        "net_score": 0.1,
        "size_score": {
            "raspberry_pi": 0.1,
            "jetson_nano": 0.1,
            "desktop_pc": 0.1,
            "aws_server": 0.1,
        },
    }


def test_collect_preview_metadata_skips_non_models(monkeypatch: Any) -> None:
    """Non-model artifacts should skip preview fetch."""
    artifact = make_artifact(type_="dataset", status=ArtifactStatus.pending)
    assert logic._collect_preview_metadata(artifact) == {}


def test_collect_preview_metadata_hf_model(monkeypatch: Any) -> None:
    """HF model preview should use README-only fetch and parse dataset/code."""
    artifact = make_artifact(
        type_="model",
        status=ArtifactStatus.pending,
        source_url="https://huggingface.co/org/model",
    )

    class FakeRepo:
        def __init__(self) -> None:
            self.read_text_calls = 0

    class FakeFetcher:
        def __init__(
            self, repo_id: str, allow_patterns: Optional[Tuple[str, ...]] = None
        ) -> None:
            self.repo_id = repo_id
            self.allow_patterns = allow_patterns
            assert list(allow_patterns or []) == list(MODEL_PREVIEW_ALLOW)

        def __enter__(self) -> FakeRepo:
            return FakeRepo()

        def __exit__(
            self,
            exc_type: Optional[type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
        ) -> None:
            return None

    def fake_get_dataset_and_code(
        repo: Any,
    ) -> Tuple[Optional[str], Optional[str]]:
        return ("dataset-url", "code-url")

    monkeypatch.setattr(logic, "HFModelFetcher", FakeFetcher)
    monkeypatch.setattr(
        ingestion_metadata, "get_dataset_and_code", fake_get_dataset_and_code
    )

    meta = logic._collect_preview_metadata(artifact)
    assert meta == {"dataset_url": "dataset-url", "code_url": "code-url"}


def test_build_urlset_populates_optional_links() -> None:
    """UrlSet should contain provided dataset/code links when present."""  # noqa: D403
    urlset = logic._build_urlset_for_artifact(
        "https://huggingface.co/org/model",
        dataset_url="https://huggingface.co/datasets/org/data",
        code_url="https://github.com/org/repo",
    )
    assert urlset.model.link.endswith("/model")
    assert urlset.dataset is not None
    assert urlset.dataset.link.endswith("/data")
    assert urlset.code is not None
    assert urlset.code.link.endswith("/repo")


def test_is_ingestible_handles_invalid_payload() -> None:
    """Invalid payloads or sub-threshold scores are non-ingestible."""
    assert logic._is_ingestible({"net_score": "bad"}) is False
    assert (
        logic._is_ingestible(
            {
                "size_score": {
                    "raspberry_pi": 0.4,
                    "jetson_nano": 0.4,
                    "desktop_pc": 0.4,
                    "aws_server": 0.4,
                }
            },
            threshold=0.5,
        )
        is False
    )


def test_ingest_artifact_accepts_model(monkeypatch: Any, tmp_path: Any) -> None:
    """Model artifacts should be accepted when rating passes thresholds."""
    artifact = make_artifact(
        artifact_id=1,
        type_="model",
        status=ArtifactStatus.pending,
        source_url="https://huggingface.co/org/model",
    )

    fake_session = FakeSession()
    monkeypatch.setattr(logic, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(logic, "get_artifact_by_id", lambda s, i: artifact)
    monkeypatch.setattr(
        logic,
        "_collect_preview_metadata",
        lambda a: {"dataset_ref": "ds", "code_url": "code"},
    )
    monkeypatch.setattr(logic, "calculate_scores", lambda urlset: _good_rating())
    monkeypatch.setattr(
        logic,
        "_fetch_artifact_archive",
        lambda a: (
            str(tmp_path / "a.zip"),
            {
                "parent_artifact_ref": "parent-ref",
                "checksum_sha256": "abc",
                "size_bytes": 10,
                "license": "apache-2.0",
            },
        ),
    )
    monkeypatch.setattr(
        logic, "upload_artifact", lambda path, artifact_id: "s3://bucket/key"
    )
    monkeypatch.setattr(
        logic, "get_artifact_id_by_ref", lambda s, ref, exclude_id=None: 99
    )
    monkeypatch.setattr(
        logic, "_upload_dependencies", lambda s, a, p: {"dataset_id": 7, "code_id": 8}
    )

    updated_attrs: Dict[str, Any] = {}

    def fake_update(session: Any, art: Any, **attrs: Any) -> None:
        updated_attrs.update(attrs)

    monkeypatch.setattr(logic, "update_artifact_attributes", fake_update)
    monkeypatch.setattr(logic, "_persist_rating", lambda s, a, r: None)
    monkeypatch.setattr(logic, "_backfill_children", lambda s, a: None)

    status = logic.ingest_artifact(artifact.id)

    assert status is ArtifactStatus.accepted
    assert updated_attrs["status"] == ArtifactStatus.accepted
    assert updated_attrs["s3_key"] == "s3://bucket/key"
    assert updated_attrs["parent_artifact_id"] == 99
    assert updated_attrs["dataset_id"] == 7
    assert updated_attrs["code_id"] == 8
    assert updated_attrs["checksum_sha256"] == "abc"
    assert updated_attrs["license"] == "apache-2.0"
    assert fake_session.committed is True


def test_ingest_artifact_rejects_on_low_rating(monkeypatch: Any) -> None:
    """Model artifacts with poor ratings should be rejected."""
    artifact = make_artifact(
        artifact_id=2,
        type_="model",
        status=ArtifactStatus.pending,
        source_url="https://huggingface.co/org/model",
    )

    fake_session = FakeSession()
    monkeypatch.setattr(logic, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(logic, "get_artifact_by_id", lambda s, i: artifact)
    monkeypatch.setattr(logic, "_collect_preview_metadata", lambda a: {})
    monkeypatch.setattr(logic, "calculate_scores", lambda urlset: _bad_rating())
    monkeypatch.setattr(
        logic,
        "_fetch_artifact_archive",
        lambda a: (_ for _ in ()).throw(AssertionError("should not fetch")),
    )
    monkeypatch.setattr(
        logic,
        "upload_artifact",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("upload should not run")
        ),
    )

    updated_attrs: Dict[str, Any] = {}

    def fake_update(session: Any, art: Any, **attrs: Any) -> None:
        updated_attrs.update(attrs)

    monkeypatch.setattr(logic, "update_artifact_attributes", fake_update)
    monkeypatch.setattr(
        logic,
        "_persist_rating",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no rating")),
    )
    monkeypatch.setattr(
        logic,
        "_backfill_children",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no backfill")),
    )

    status = logic.ingest_artifact(artifact.id)

    assert status == ArtifactStatus.rejected
    assert updated_attrs["status"] == ArtifactStatus.rejected
    assert fake_session.committed is True


def test_ingest_artifact_accepts_non_model_without_rating(
    monkeypatch: Any, tmp_path: Any
) -> None:
    """Non-model artifacts bypass rating and are accepted."""
    artifact = make_artifact(
        artifact_id=3,
        type_="dataset",
        status=ArtifactStatus.pending,
        source_url="https://example.com/dataset.zip",
    )

    fake_session = FakeSession()
    monkeypatch.setattr(logic, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(logic, "get_artifact_by_id", lambda s, i: artifact)
    monkeypatch.setattr(logic, "_collect_preview_metadata", lambda a: {})
    monkeypatch.setattr(
        logic,
        "calculate_scores",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("no rating for non-model")
        ),
    )
    monkeypatch.setattr(
        logic,
        "_fetch_artifact_archive",
        lambda a: (
            str(tmp_path / "d.zip"),
            {"parent_artifact_ref": None, "checksum_sha256": "xyz", "size_bytes": 5},
        ),
    )
    monkeypatch.setattr(
        logic, "upload_artifact", lambda path, artifact_id: "s3://bucket/dataset"
    )
    monkeypatch.setattr(logic, "get_artifact_id_by_ref", lambda *args, **kwargs: None)

    updated_attrs: Dict[str, Any] = {}

    def fake_update(session: Any, art: Any, **attrs: Any) -> None:
        updated_attrs.update(attrs)

    monkeypatch.setattr(logic, "update_artifact_attributes", fake_update)
    monkeypatch.setattr(
        logic,
        "_persist_rating",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no rating")),
    )
    monkeypatch.setattr(logic, "_backfill_children", lambda *args, **kwargs: None)

    status = logic.ingest_artifact(artifact.id)

    assert status == ArtifactStatus.accepted
    assert updated_attrs["status"] == ArtifactStatus.accepted
    assert updated_attrs["s3_key"] == "s3://bucket/dataset"
    assert updated_attrs["checksum_sha256"] == "xyz"
    assert fake_session.committed is True


def test_fetch_artifact_archive_includes_license(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """_fetch_artifact_archive should include license metadata for models."""
    artifact = make_artifact(
        artifact_id=4,
        type_="model",
        status=ArtifactStatus.pending,
        source_url="https://huggingface.co/org/model",
    )

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "file.txt").write_text("data")

    class FakeRepo:
        def __init__(self, root: Path) -> None:
            self.root = root

    class FakeFetcher:
        def __init__(self, repo_id: str) -> None:
            self.repo_id = repo_id

        def __enter__(self) -> FakeRepo:
            return FakeRepo(repo_root)

        def __exit__(
            self,
            exc_type: Optional[type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
        ) -> None:
            return None

    monkeypatch.setattr(logic, "HFModelFetcher", FakeFetcher)
    monkeypatch.setattr(ingestion_metadata, "get_license", lambda repo_id: "apache-2.0")
    monkeypatch.setattr(ingestion_metadata, "get_parent_artifact", lambda repo: None)

    archive_path, meta = logic._fetch_artifact_archive(artifact)

    assert archive_path.endswith(".zip")
    assert meta["license"] == "apache-2.0"
    assert "checksum_sha256" in meta and meta["checksum_sha256"]
