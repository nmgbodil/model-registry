"""DAL tests for model ratings."""

from __future__ import annotations

from unittest import mock

from app.dals import ratings as ratings_dal
from app.db.models import Rating


class TestRatingsDal:
    """Tests for ratings data access helpers."""

    def test_get_artifact_by_id_delegates_to_session_get(self) -> None:
        """Should delegate to session.get with the provided id."""
        fake_session = mock.MagicMock()
        ratings_dal.get_artifact_by_id(fake_session, 123)
        fake_session.get.assert_called_once_with(mock.ANY, 123)

    def test_get_rating_by_artifact_filters_on_artifact_id(self) -> None:
        """Should filter ratings by artifact_id and call one_or_none."""
        fake_query = mock.MagicMock()
        fake_session = mock.MagicMock()
        fake_session.query.return_value = fake_query

        ratings_dal.get_rating_by_artifact(fake_session, 456)

        fake_session.query.assert_called_once_with(Rating)
        fake_query.filter.assert_called_once()
        fake_query.filter.return_value.one_or_none.assert_called_once()
