"""Unit tests for app.utils helpers."""

from __future__ import annotations

import app.utils as ratings_utils
from app.db.models import ArtifactStatus
from app.schemas.model_rating import ModelRating
from tests.utils import make_artifact, make_rating


class TestIsHfUrl:
    """Tests for Hugging Face URL detection."""

    def test_recognizes_model_urls(self) -> None:
        """Detects HF model URLs."""
        is_hf, kind, repo_id = ratings_utils._is_hf_url(
            "https://huggingface.co/org/model-name"
        )
        assert is_hf is True
        assert kind == "model"
        assert repo_id == "org/model-name"

    def test_recognizes_dataset_urls(self) -> None:
        """Detects HF dataset URLs."""
        is_hf, kind, repo_id = ratings_utils._is_hf_url(
            "https://huggingface.co/datasets/org/data-set"
        )
        assert is_hf is True
        assert kind == "dataset"
        assert repo_id == "org/data-set"

    def test_recognizes_space_urls(self) -> None:
        """Detects HF space URLs."""
        is_hf, kind, repo_id = ratings_utils._is_hf_url(
            "https://huggingface.co/spaces/user/demo-space"
        )
        assert is_hf is True
        assert kind == "space"
        assert repo_id == "user/demo-space"

    def test_rejects_non_hf_hosts(self) -> None:
        """Rejects non-HF hosts."""
        is_hf, kind, repo_id = ratings_utils._is_hf_url("https://example.com/org/model")
        assert is_hf is False
        assert kind == "unknown"
        assert repo_id is None

    def test_handles_invalid_urls(self) -> None:
        """Handles invalid URLs gracefully."""
        is_hf, kind, repo_id = ratings_utils._is_hf_url("not a url")
        assert is_hf is False
        assert kind == "unknown"
        assert repo_id is None


class TestCanonicalDatasetUrl:
    """Tests for canonical dataset URL normalization."""

    def test_returns_none_for_missing(self) -> None:
        """Returns None when ref is missing."""
        assert ratings_utils.canonical_dataset_url(None) is None

    def test_passthrough_for_urls(self) -> None:
        """Returns URL inputs unchanged."""
        url = "https://example.com/data"
        assert ratings_utils.canonical_dataset_url(url) == url

    def test_exact_match(self) -> None:
        """Matches known canonical dataset names."""
        assert (
            ratings_utils.canonical_dataset_url("SQuAD")
            == "https://huggingface.co/datasets/squad"
        )

    def test_normalizes_variants(self) -> None:
        """Normalizes variants of known dataset names."""
        assert (
            ratings_utils.canonical_dataset_url("squad_v1.1")
            == "https://huggingface.co/datasets/squad"
        )

    def test_fuzzy_contains(self) -> None:
        """Performs fuzzy contains matching."""
        assert (
            ratings_utils.canonical_dataset_url("BookCorpus subset")
            == "https://huggingface.co/datasets/bookcorpus"
        )

    def test_unknown_returns_none(self) -> None:
        """Returns None for unknown datasets."""
        assert ratings_utils.canonical_dataset_url("mystery_dataset") is None


class TestBuildModelRatingFromRecord:
    """Tests for rating-to-schema mapping."""

    def test_maps_all_fields(self) -> None:
        """Maps every rating field into the schema."""
        artifact = make_artifact(1, "demo-model", "model", ArtifactStatus.accepted)
        rating = make_rating(artifact.id)

        result = ratings_utils.build_model_rating_from_record(artifact, rating)

        assert isinstance(result, ModelRating)
        assert result.name == artifact.name
        assert result.category == artifact.type
        assert result.net_score == rating.net_score
        assert result.net_score_latency == rating.net_score_latency
        assert result.ramp_up_time == rating.ramp_up_time
        assert result.ramp_up_time_latency == rating.ramp_up_time_latency
        assert result.bus_factor == rating.bus_factor
        assert result.bus_factor_latency == rating.bus_factor_latency
        assert result.performance_claims == rating.performance_claims
        assert result.performance_claims_latency == rating.performance_claims_latency
        assert result.license == rating.license
        assert result.license_latency == rating.license_latency
        assert result.dataset_and_code_score == rating.dataset_and_code_score
        assert (
            result.dataset_and_code_score_latency
            == rating.dataset_and_code_score_latency
        )
        assert result.dataset_quality == rating.dataset_quality
        assert result.dataset_quality_latency == rating.dataset_quality_latency
        assert result.code_quality == rating.code_quality
        assert result.code_quality_latency == rating.code_quality_latency
        assert result.reproducibility == rating.reproducibility
        assert result.reproducibility_latency == rating.reproducibility_latency
        assert result.reviewedness == rating.reviewedness
        assert result.reviewedness_latency == rating.reviewedness_latency
        assert result.tree_score == rating.treescore
        assert result.tree_score_latency == rating.treescore_latency
        assert result.size_score.raspberry_pi == rating.size_score_raspberry_pi
        assert result.size_score.jetson_nano == rating.size_score_jetson_nano
        assert result.size_score.desktop_pc == rating.size_score_desktop_pc
        assert result.size_score.aws_server == rating.size_score_aws_server
        assert result.size_score_latency == rating.size_score_latency
