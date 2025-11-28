"""Utility tests for model ratings."""

from __future__ import annotations

import app.utils as ratings_utils
from app.db.models import ArtifactStatus
from app.schemas.model_rating import ModelRating
from tests.utils import make_artifact, make_rating


class TestRatingsUtils:
    """Tests for rating utility helpers."""

    def test_build_model_rating_from_record_maps_fields(self) -> None:
        """Ensure ORM records are mapped to ModelRating correctly."""
        artifact = make_artifact(1, "demo-model", "model", ArtifactStatus.accepted)
        rating = make_rating(artifact.id)

        result = ratings_utils.build_model_rating_from_record(artifact, rating)

        assert isinstance(result, ModelRating)
        assert result.name == "demo-model"
        assert result.net_score == rating.net_score
        assert result.tree_score == rating.treescore
        assert result.size_score.raspberry_pi == rating.size_score_raspberry_pi
