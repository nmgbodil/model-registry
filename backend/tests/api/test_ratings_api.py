"""API tests for model ratings."""

from __future__ import annotations

from unittest import mock

import pytest
from flask import Flask

from app import create_app
from app.api import ratings as ratings_api
from app.db.models import ArtifactStatus
from app.schemas.model_rating import ModelRating, ModelSizeScore
from app.services import ratings as ratings_service


@pytest.fixture()
def flask_app() -> Flask:
    """Provide a test application instance."""
    app = create_app()
    app.config["TESTING"] = True
    return app


class TestRatingsApi:
    """Tests for the ratings API endpoint."""

    def test_rate_model_success(
        self, flask_app: Flask, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns rating payload when service succeeds."""
        model_rating = ModelRating(
            name="demo-model",
            category="model",
            net_score=0.9,
            net_score_latency=1.0,
            ramp_up_time=0.1,
            ramp_up_time_latency=0.01,
            bus_factor=0.2,
            bus_factor_latency=0.02,
            performance_claims=0.3,
            performance_claims_latency=0.03,
            license=0.4,
            license_latency=0.04,
            dataset_and_code_score=0.5,
            dataset_and_code_score_latency=0.05,
            dataset_quality=0.6,
            dataset_quality_latency=0.06,
            code_quality=0.7,
            code_quality_latency=0.07,
            reproducibility=0.8,
            reproducibility_latency=0.08,
            reviewedness=0.9,
            reviewedness_latency=0.09,
            tree_score=1.0,
            tree_score_latency=0.1,
            size_score=ModelSizeScore(
                raspberry_pi=0.1,
                jetson_nano=0.2,
                desktop_pc=0.3,
                aws_server=0.4,
            ),
            size_score_latency=0.11,
        )

        monkeypatch.setattr(
            ratings_api, "get_model_rating", lambda artifact_id: model_rating
        )
        monkeypatch.setattr(
            ratings_api,
            "_wait_for_ingestion",
            lambda artifact_id: ArtifactStatus.accepted,
        )

        client = flask_app.test_client()
        resp = client.get("/api/artifact/model/1/rate")

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["name"] == "demo-model"
        assert payload["net_score"] == model_rating.net_score

    def test_rate_model_invalid_id(
        self, flask_app: Flask, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Responds with 400 when artifact id is invalid."""
        monkeypatch.setattr(
            ratings_api,
            "get_model_rating",
            mock.MagicMock(side_effect=ratings_service.InvalidArtifactIdError()),
        )
        monkeypatch.setattr(
            ratings_api,
            "_wait_for_ingestion",
            lambda artifact_id: ArtifactStatus.accepted,
        )
        client = flask_app.test_client()
        resp = client.get("/api/artifact/model/0/rate")
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "exc_class",
        [
            ratings_service.ArtifactNotFoundError,
            ratings_service.RatingNotFoundError,
            ratings_service.ArtifactNotModelError,
        ],
    )
    def test_rate_model_not_found_errors(
        self,
        flask_app: Flask,
        monkeypatch: pytest.MonkeyPatch,
        exc_class: type[Exception],
    ) -> None:
        """Responds with 404 for missing or ineligible artifacts."""
        monkeypatch.setattr(
            ratings_api,
            "get_model_rating",
            mock.MagicMock(side_effect=exc_class("not found")),
        )
        monkeypatch.setattr(
            ratings_api,
            "_wait_for_ingestion",
            lambda artifact_id: ArtifactStatus.accepted,
        )
        client = flask_app.test_client()
        resp = client.get("/api/artifact/model/5/rate")

        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_rate_model_unexpected_error_returns_500(
        self, flask_app: Flask, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Responds with 500 when service raises unexpectedly."""
        monkeypatch.setattr(
            ratings_api,
            "get_model_rating",
            mock.MagicMock(side_effect=RuntimeError("boom")),
        )
        monkeypatch.setattr(
            ratings_api,
            "_wait_for_ingestion",
            lambda artifact_id: ArtifactStatus.accepted,
        )
        client = flask_app.test_client()
        resp = client.get("/api/artifact/model/5/rate")
        assert resp.status_code == 500

    def test_rate_model_returns_404_when_not_ready(
        self, flask_app: Flask, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Responds with 404 when rating is not yet available (pending ingestion)."""
        monkeypatch.setattr(
            ratings_api,
            "get_model_rating",
            mock.MagicMock(side_effect=ratings_service.RatingNotFoundError()),
        )
        client = flask_app.test_client()
        resp = client.get("/api/artifact/model/5/rate")

        assert resp.status_code == 404
        payload = resp.get_json()
        assert "error" in payload

    def test_rate_model_returns_404_when_artifact_missing_during_wait(
        self, flask_app: Flask, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Responds with 404 when artifact disappears before rating fetch."""
        monkeypatch.setattr(
            ratings_api,
            "_wait_for_ingestion",
            lambda artifact_id: None,
        )
        client = flask_app.test_client()
        resp = client.get("/api/artifact/model/5/rate")

        assert resp.status_code == 404
        payload = resp.get_json()
        assert "error" in payload
