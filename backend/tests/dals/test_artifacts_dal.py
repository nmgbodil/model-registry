"""DAL tests for artifact helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.dals import artifacts as artifacts_dal
from app.db.models import Artifact, ArtifactStatus, Base


@contextmanager
def _db_session() -> Generator[Session, None, None]:
    """Provide a temporary in-memory DB session for DAL integration tests."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestArtifactsDal:
    """Tests for artifact data access helpers."""

    def test_get_artifact_by_id_delegates_to_session_get(self) -> None:
        """Should delegate to session.get with the provided id."""
        fake_session = mock.MagicMock()

        artifacts_dal.get_artifact_by_id(fake_session, 123)

        fake_session.get.assert_called_once_with(Artifact, 123)

    def test_update_artifact_attributes_sets_fields_and_flushes(self) -> None:
        """Should set provided attributes, add, and flush."""
        artifact = Artifact(id=1, name="demo", type="model", source_url="http://x")
        fake_session = mock.MagicMock()

        updated = artifacts_dal.update_artifact_attributes(
            fake_session,
            artifact,
            status=ArtifactStatus.accepted,
            s3_key="s3://bucket/key",
        )

        assert updated.status == ArtifactStatus.accepted
        assert updated.s3_key == "s3://bucket/key"
        fake_session.add.assert_called_once_with(artifact)
        fake_session.flush.assert_called_once_with()

    def test_get_artifact_id_by_ref_matches_name_or_source(self) -> None:
        """Ensure lookup by ref finds matching artifact id."""
        with _db_session() as session:
            a1 = Artifact(name="model-a", type="model", source_url="http://x/a")
            a2 = Artifact(name="model-b", type="model", source_url="http://x/b")
            session.add_all([a1, a2])
            session.commit()

            by_name = artifacts_dal.get_artifact_id_by_ref(session, "model-a")
            by_source = artifacts_dal.get_artifact_id_by_ref(session, "http://x/b")
            exclude = artifacts_dal.get_artifact_id_by_ref(
                session, "model-a", exclude_id=a1.id
            )

            assert by_name == a1.id
            assert by_source == a2.id
            assert exclude is None

    def test_get_artifacts_with_parent_ref_filters_and_excludes(self) -> None:
        """Ensure querying by parent_artifact_ref returns matching artifacts."""
        with _db_session() as session:
            parent_ref = "parent/model"
            child1 = Artifact(
                name="child1",
                type="model",
                source_url="http://child/1",
                parent_artifact_ref=parent_ref,
            )
            child2 = Artifact(
                name="child2",
                type="model",
                source_url="http://child/2",
                parent_artifact_ref=parent_ref,
            )
            other = Artifact(
                name="other",
                type="model",
                source_url="http://child/3",
                parent_artifact_ref="other/model",
            )
            session.add_all([child1, child2, other])
            session.commit()

            found = artifacts_dal.get_artifacts_with_parent_ref(session, parent_ref)
            excluded = artifacts_dal.get_artifacts_with_parent_ref(
                session, parent_ref, exclude_id=child1.id
            )

            assert {c.name for c in found} == {"child1", "child2"}
            assert {c.name for c in excluded} == {"child2"}

    def test_get_artifact_size_returns_size_bytes(self) -> None:
        """Should return the stored size_bytes for an artifact."""
        with _db_session() as session:
            art = Artifact(
                name="sized",
                type="model",
                source_url="http://x",
                size_bytes=123,
            )
            session.add(art)
            session.commit()

            size = artifacts_dal.get_artifact_size(session, art.id)
            missing = artifacts_dal.get_artifact_size(session, 999)

            assert size == 123
            assert missing is None

    def test_create_artifact_persists_and_sets_id(self) -> None:
        """create_artifact should add and flush a new artifact."""
        with _db_session() as session:
            created = artifacts_dal.create_artifact(
                session,
                name="new-artifact",
                type="model",
                source_url="http://example.com",
                status=ArtifactStatus.pending,
            )

            assert created.id is not None
            fetched = artifacts_dal.get_artifact_by_id(session, created.id)
            assert fetched is created
