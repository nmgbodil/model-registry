"""Schemas for artifact lineage graphs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ArtifactLineageNode(BaseModel):
    """Node in a lineage graph."""

    artifact_id: int = Field(..., description="Unique identifier for the artifact.")
    name: str = Field(..., description="Human-readable label for the node.")
    source: Optional[str] = Field(
        default=None, description="Provenance for how the node was discovered."
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional metadata captured for lineage analysis."
    )


class ArtifactLineageEdge(BaseModel):
    """Directed edge between two lineage nodes."""

    from_node_artifact_id: int = Field(
        ..., description="Identifier of the upstream node."
    )
    to_node_artifact_id: int = Field(
        ..., description="Identifier of the downstream node."
    )
    relationship: str = Field(..., description="Qualitative description of the edge.")


class ArtifactLineageGraph(BaseModel):
    """Complete lineage graph."""

    nodes: list[ArtifactLineageNode]
    edges: list[ArtifactLineageEdge]
