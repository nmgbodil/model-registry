"""Shared helpers for rating-related unit tests."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from app.db.models import Artifact, ArtifactStatus, Rating


def make_artifact(
    artifact_id: int = 1,
    name: str = "demo-model",
    type_: str = "model",
    status: ArtifactStatus = ArtifactStatus.ACCEPTED,
    source_url: str = "https://example.com/model",
) -> Artifact:
    """Create an Artifact ORM instance with sensible defaults."""
    return Artifact(
        id=artifact_id,
        name=name,
        type=type_,
        status=status,
        source_url=source_url,
    )


def make_rating(artifact_id: int = 1) -> Rating:
    """Create a Rating ORM instance with populated metrics."""
    return Rating(
        artifact_id=artifact_id,
        dataset_quality=0.1,
        dataset_quality_latency=0.01,
        dataset_and_code_score=0.2,
        dataset_and_code_score_latency=0.02,
        bus_factor=0.3,
        bus_factor_latency=0.03,
        license=0.4,
        license_latency=0.04,
        code_quality=0.5,
        code_quality_latency=0.05,
        size_score_raspberry_pi=0.6,
        size_score_jetson_nano=0.7,
        size_score_desktop_pc=0.8,
        size_score_aws_server=0.9,
        size_score_latency=0.06,
        ramp_up_time=1.0,
        ramp_up_time_latency=0.1,
        performance_claims=1.1,
        performance_claims_latency=0.11,
        reproducibility=1.2,
        reproducibility_latency=0.12,
        reviewedness=1.3,
        reviewedness_latency=0.13,
        treescore=1.4,
        treescore_latency=0.14,
        net_score=9.9,
        net_score_latency=0.99,
    )


@contextmanager
def fake_session_cm(fake_session: object) -> Iterator[object]:
    """Context manager that mimics orm_session yielding a supplied session."""
    yield fake_session
