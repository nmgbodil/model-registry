"""DAL tests for rating helpers."""

from __future__ import annotations

from typing import Any, Mapping
from unittest import mock

import pytest

from app.dals import ratings as ratings_dal


class DummyRating:
    """Lightweight stand-in for the Rating ORM model."""

    def __init__(self, **kwargs: Any) -> None:
        for key, val in kwargs.items():
            setattr(self, key, val)


class TestRatingsDal:
    """Tests for ratings data access helpers."""

    def test_get_rating_by_artifact_filters_on_artifact_id(self) -> None:
        """Should filter ratings by artifact_id and call one_or_none."""
        fake_result = object()
        fake_filter = mock.MagicMock()
        fake_filter.one_or_none.return_value = fake_result

        fake_query = mock.MagicMock()
        fake_query.filter.return_value = fake_filter

        fake_session = mock.MagicMock()
        fake_session.query.return_value = fake_query

        result = ratings_dal.get_rating_by_artifact(fake_session, 456)

        fake_session.query.assert_called_once()
        fake_query.filter.assert_called_once()
        fake_filter.one_or_none.assert_called_once()
        assert result is fake_result

    @pytest.mark.parametrize(
        "rating_data,expected",
        [
            (
                {
                    "dataset_quality": "1.5",
                    "bus_factor": 2,
                    "size_score": {"raspberry_pi": 0.9},
                },
                {
                    "dataset_quality": 1.5,
                    "bus_factor": 2.0,
                    "size_score_raspberry_pi": 0.9,
                },
            ),
            (
                {
                    "dataset_quality": "not-a-number",
                    "bus_factor": None,
                    "size_score": "oops",
                },
                {
                    "dataset_quality": 0.0,
                    "bus_factor": 0.0,
                    "size_score_raspberry_pi": 0.0,
                },
            ),
        ],
    )
    def test_create_rating_converts_values_and_adds_to_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        rating_data: Mapping[str, Any],
        expected: Mapping[str, float],
    ) -> None:
        """Create rating converts inputs, applies defaults, and adds then flushes."""
        fake_session = mock.MagicMock()
        created_instances: list[DummyRating] = []

        def fake_rating_factory(**kwargs: Any) -> DummyRating:
            inst = DummyRating(**kwargs)
            created_instances.append(inst)
            return inst

        monkeypatch.setattr(ratings_dal, "Rating", fake_rating_factory)

        rating = ratings_dal.create_rating(fake_session, 999, rating_data)

        fake_session.add.assert_called_once_with(rating)
        fake_session.flush.assert_called_once_with()

        assert rating.artifact_id == 999
        assert (
            pytest.approx(getattr(rating, "dataset_quality"))
            == expected["dataset_quality"]
        )
        assert pytest.approx(getattr(rating, "bus_factor")) == expected["bus_factor"]
        assert (
            pytest.approx(getattr(rating, "size_score_raspberry_pi"))
            == expected["size_score_raspberry_pi"]
        )

    def test_create_rating_uses_default_when_size_score_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing size_score populates defaults and still creates a rating."""
        fake_session = mock.MagicMock()

        created_instances: list[DummyRating] = []

        def fake_rating_factory(**kwargs: Any) -> DummyRating:
            inst = DummyRating(**kwargs)
            created_instances.append(inst)
            return inst

        monkeypatch.setattr(ratings_dal, "Rating", fake_rating_factory)

        rating = ratings_dal.create_rating(fake_session, 1, {})

        assert getattr(rating, "size_score_raspberry_pi") == 0.0
        assert getattr(rating, "size_score_jetson_nano") == 0.0
        assert getattr(rating, "size_score_desktop_pc") == 0.0
        assert getattr(rating, "size_score_aws_server") == 0.0
        fake_session.add.assert_called_once_with(rating)
        fake_session.flush.assert_called_once_with()
