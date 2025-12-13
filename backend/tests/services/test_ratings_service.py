"""Service tests for model ratings."""

from __future__ import annotations

import pytest

from app.db.models import ArtifactStatus
from app.services import ratings as ratings_service
from tests.utils import fake_session_cm, make_artifact, make_rating


class TestGetModelRating:
    """Tests for get_model_rating service logic."""

    def test_raises_for_invalid_id(self) -> None:
        """Reject invalid or missing artifact ids."""
        with pytest.raises(ratings_service.InvalidArtifactIdError):
            ratings_service.get_model_rating(0)

    def test_returns_existing_rating_when_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Return rating when artifact exists and has a rating row."""
        artifact = make_artifact(1, "demo-model", "model", ArtifactStatus.accepted)
        rating = make_rating(artifact.id)

        monkeypatch.setattr(
            ratings_service, "get_artifact_by_id", lambda session, aid: artifact
        )
        monkeypatch.setattr(
            ratings_service, "get_rating_by_artifact", lambda session, aid: rating
        )
        monkeypatch.setattr(
            ratings_service, "orm_session", lambda: fake_session_cm(object())
        )

        result = ratings_service.get_model_rating(artifact.id)

        assert result.name == artifact.name
        assert result.net_score == rating.net_score

    def test_raises_when_artifact_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise when artifact cannot be found."""
        monkeypatch.setattr(
            ratings_service, "get_artifact_by_id", lambda session, aid: None
        )
        monkeypatch.setattr(
            ratings_service, "orm_session", lambda: fake_session_cm(object())
        )

        with pytest.raises(ratings_service.ArtifactNotFoundError):
            ratings_service.get_model_rating(99)

    def test_raises_when_not_a_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reject artifacts that are not models."""
        artifact = make_artifact(1, "not-model", "dataset", ArtifactStatus.accepted)
        monkeypatch.setattr(
            ratings_service, "get_artifact_by_id", lambda session, aid: artifact
        )
        monkeypatch.setattr(
            ratings_service, "orm_session", lambda: fake_session_cm(object())
        )

        with pytest.raises(ratings_service.ArtifactNotModelError):
            ratings_service.get_model_rating(artifact.id)

    def test_raises_when_not_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reject artifacts that are not yet accepted."""
        artifact = make_artifact(1, "pending-model", "model", ArtifactStatus.pending)
        monkeypatch.setattr(
            ratings_service, "get_artifact_by_id", lambda session, aid: artifact
        )
        monkeypatch.setattr(
            ratings_service,
            "get_rating_by_artifact",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("should not fetch rating when not accepted")
            ),
        )
        monkeypatch.setattr(
            ratings_service, "orm_session", lambda: fake_session_cm(object())
        )

        with pytest.raises(ratings_service.RatingNotFoundError):
            ratings_service.get_model_rating(artifact.id)

    def test_raises_when_no_rating_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raise when artifact is eligible but missing a rating row."""
        artifact = make_artifact(1, "demo", "model", ArtifactStatus.accepted)
        monkeypatch.setattr(
            ratings_service, "get_artifact_by_id", lambda session, aid: artifact
        )
        monkeypatch.setattr(
            ratings_service, "get_rating_by_artifact", lambda session, aid: None
        )
        monkeypatch.setattr(
            ratings_service, "orm_session", lambda: fake_session_cm(object())
        )

        with pytest.raises(ratings_service.RatingNotFoundError):
            ratings_service.get_model_rating(artifact.id)

    def test_wraps_unexpected_exceptions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wrap unexpected exceptions in RatingServiceError."""

        def boom(*_: object, **__: object) -> None:
            raise RuntimeError("db down")

        monkeypatch.setattr(ratings_service, "get_artifact_by_id", boom)
        monkeypatch.setattr(
            ratings_service, "orm_session", lambda: fake_session_cm(object())
        )

        with pytest.raises(ratings_service.RatingServiceError):
            ratings_service.get_model_rating(1)
