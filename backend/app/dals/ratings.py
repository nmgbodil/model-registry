"""Data access helpers for ratings-related queries."""

from __future__ import annotations

from typing import Mapping, Optional, Union

from sqlalchemy.orm import Session

from app.db.models import Rating


def get_rating_by_artifact(session: Session, artifact_id: int) -> Optional[Rating]:
    """Fetch the rating row for a given artifact id."""
    return session.query(Rating).filter(Rating.artifact_id == artifact_id).one_or_none()


NumberLike = Union[int, float, str]


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def create_rating(
    session: Session, artifact_id: int, rating_data: Mapping[str, object]
) -> Rating:
    """Create and persist a rating row from a raw payload."""
    size_score_raw = rating_data.get("size_score", {}) or {}
    size_score = size_score_raw if isinstance(size_score_raw, Mapping) else {}

    rating = Rating(
        artifact_id=artifact_id,
        dataset_quality=_to_float(rating_data.get("dataset_quality")),
        dataset_quality_latency=_to_float(rating_data.get("dataset_quality_latency")),
        dataset_and_code_score=_to_float(rating_data.get("dataset_and_code_score")),
        dataset_and_code_score_latency=_to_float(
            rating_data.get("dataset_and_code_score_latency")
        ),
        bus_factor=_to_float(rating_data.get("bus_factor")),
        bus_factor_latency=_to_float(rating_data.get("bus_factor_latency")),
        license=_to_float(rating_data.get("license")),
        license_latency=_to_float(rating_data.get("license_latency")),
        code_quality=_to_float(rating_data.get("code_quality")),
        code_quality_latency=_to_float(rating_data.get("code_quality_latency")),
        size_score_raspberry_pi=_to_float(size_score.get("raspberry_pi")),
        size_score_jetson_nano=_to_float(size_score.get("jetson_nano")),
        size_score_desktop_pc=_to_float(size_score.get("desktop_pc")),
        size_score_aws_server=_to_float(size_score.get("aws_server")),
        size_score_latency=_to_float(rating_data.get("size_score_latency")),
        ramp_up_time=_to_float(rating_data.get("ramp_up_time")),
        ramp_up_time_latency=_to_float(rating_data.get("ramp_up_time_latency")),
        performance_claims=_to_float(rating_data.get("performance_claims")),
        performance_claims_latency=_to_float(
            rating_data.get("performance_claims_latency")
        ),
        reproducibility=_to_float(rating_data.get("reproducibility")),
        reproducibility_latency=_to_float(rating_data.get("reproducibility_latency")),
        reviewedness=_to_float(rating_data.get("reviewedness")),
        reviewedness_latency=_to_float(rating_data.get("reviewedness_latency")),
        treescore=_to_float(rating_data.get("tree_score")),
        treescore_latency=_to_float(rating_data.get("tree_score_latency")),
        net_score=_to_float(rating_data.get("net_score")),
        net_score_latency=_to_float(rating_data.get("net_score_latency")),
    )

    session.add(rating)
    session.flush()
    return rating
