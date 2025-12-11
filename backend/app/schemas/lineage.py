"""Schemas for artifact lineage graphs."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ArtifactLineageNode(BaseModel):
    """Node in a lineage graph."""

    artifact_id: int
    name: str
    source: Optional[str] = "config_json"
    metadata: Optional[dict[str, Any]]


class ArtifactLineageEdge(BaseModel):
    """Directed edge between two lineage nodes."""

    from_node_artifact_id: int
    to_node_artifact_id: int
    relationship: str


class ArtifactLineageGraph(BaseModel):
    """Complete lineage graph."""

    nodes: list[ArtifactLineageNode]
    edges: list[ArtifactLineageEdge]
