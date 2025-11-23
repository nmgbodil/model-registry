"""Pydantic schemas representing persisted model ratings."""

from pydantic import BaseModel


class ModelSizeScore(BaseModel):
    """Container for platform-specific size scores."""

    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


class ModelRating(BaseModel):
    """API-facing representation of a model rating."""

    name: str
    category: str
    net_score: float
    net_score_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    bus_factor: float
    bus_factor_latency: float
    performance_claims: float
    performance_claims_latency: float
    license: float
    license_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    code_quality: float
    code_quality_latency: float
    reproducibility: float
    reproducibility_latency: float
    reviewedness: float
    reviewedness_latency: float
    tree_score: float
    tree_score_latency: float
    size_score: ModelSizeScore
    size_score_latency: float
