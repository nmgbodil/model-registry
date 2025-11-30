"""Pydantic schema for artifact cost responses."""

from pydantic import BaseModel


class ArtifactCost(BaseModel):
    """Cost representation for an artifact."""

    total_cost: float
    standalone_cost: float | None = None
