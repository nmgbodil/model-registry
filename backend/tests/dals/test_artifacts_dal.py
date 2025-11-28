"""DAL tests for artifact helpers."""

from __future__ import annotations

from unittest import mock

from app.dals import artifacts as artifacts_dal
from app.db.models import Artifact, ArtifactStatus


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
