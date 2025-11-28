"""Utility functionalities for endpoints."""

from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import urlparse

from .db.models import Artifact, Rating
from .schemas.model_rating import ModelRating, ModelSizeScore


def _is_hf_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """Return (is_hf, kind, repo_id) where kind.

    ∈ {"model","dataset","space","unknown"}.
    """
    try:
        p = urlparse(url)
    except Exception:
        return (False, "unknown", None)
    if p.scheme not in {"http", "https"}:
        return (False, "unknown", None)
    if p.netloc not in {"huggingface.co", "www.huggingface.co"}:
        return (False, "unknown", None)

    parts = [seg for seg in p.path.split("/") if seg]
    if not parts:
        return (True, "unknown", None)

    if parts[0] == "datasets" and len(parts) >= 3:
        return (True, "dataset", f"{parts[1]}/{parts[2]}")
    elif parts[0] == "spaces" and len(parts) >= 3:
        return (True, "space", f"{parts[1]}/{parts[2]}")
    elif len(parts) >= 2:
        return (True, "model", f"{parts[0]}/{parts[1]}")
    else:
        return (True, "unknown", None)


def build_model_rating_from_record(artifact: Artifact, rating: Rating) -> ModelRating:
    """Transform ORM records into the API-facing ModelRating schema."""
    return ModelRating(
        name=artifact.name,
        category=artifact.type,
        net_score=rating.net_score,
        net_score_latency=rating.net_score_latency,
        ramp_up_time=rating.ramp_up_time,
        ramp_up_time_latency=rating.ramp_up_time_latency,
        bus_factor=rating.bus_factor,
        bus_factor_latency=rating.bus_factor_latency,
        performance_claims=rating.performance_claims,
        performance_claims_latency=rating.performance_claims_latency,
        license=rating.license,
        license_latency=rating.license_latency,
        dataset_and_code_score=rating.dataset_and_code_score,
        dataset_and_code_score_latency=rating.dataset_and_code_score_latency,
        dataset_quality=rating.dataset_quality,
        dataset_quality_latency=rating.dataset_quality_latency,
        code_quality=rating.code_quality,
        code_quality_latency=rating.code_quality_latency,
        reproducibility=rating.reproducibility,
        reproducibility_latency=rating.reproducibility_latency,
        reviewedness=rating.reviewedness,
        reviewedness_latency=rating.reviewedness_latency,
        tree_score=rating.treescore,
        tree_score_latency=rating.treescore_latency,
        size_score=ModelSizeScore(
            raspberry_pi=rating.size_score_raspberry_pi,
            jetson_nano=rating.size_score_jetson_nano,
            desktop_pc=rating.size_score_desktop_pc,
            aws_server=rating.size_score_aws_server,
        ),
        size_score_latency=rating.size_score_latency,
    )
