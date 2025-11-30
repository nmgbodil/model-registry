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


CANONICAL_DATASET_URLS = {
    "bookcorpus": "https://huggingface.co/datasets/bookcorpus",
    "squad": "https://huggingface.co/datasets/squad",
    "squad v1.1": "https://huggingface.co/datasets/squad",
    "squad1.1": "https://huggingface.co/datasets/squad",
    "c4": "https://huggingface.co/datasets/c4",
    "imagenet": "http://www.image-net.org/",
    "mnist": "https://huggingface.co/datasets/mnist",
    "cifar-10": "https://www.cs.toronto.edu/~kriz/cifar.html",
    # add others you care about
}


def _normalize(text: str) -> str:
    """Normalize a dataset ref for matching."""
    t = text.strip().lower()
    t = t.replace("_", " ").replace("-", " ")
    # collapse multiple spaces
    while "  " in t:
        t = t.replace("  ", " ")
    return t


# Build a normalized → url mapping once
_NORMALIZED_CANONICAL_DATASET_URLS = {
    _normalize(name): url for name, url in CANONICAL_DATASET_URLS.items()
}


def canonical_dataset_url(dataset_ref: Optional[str]) -> Optional[str]:
    """Map a dataset ref (name or variant) to a canonical URL, if known."""
    if not dataset_ref:
        return None

    # If it's already a URL, just return it
    if dataset_ref.startswith("http://") or dataset_ref.startswith("https://"):
        return dataset_ref

    ref_norm = _normalize(dataset_ref)

    # 1) exact normalized match
    if ref_norm in _NORMALIZED_CANONICAL_DATASET_URLS:
        return _NORMALIZED_CANONICAL_DATASET_URLS[ref_norm]

    # 2) fuzzy-ish: normalized key is contained in ref, or vice versa
    for norm_key, url in _NORMALIZED_CANONICAL_DATASET_URLS.items():
        if norm_key in ref_norm or ref_norm in norm_key:
            return url

    return None
