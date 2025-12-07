"""Business logic for constructing artifact lineage graphs."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.dals.artifacts import get_artifact_by_id, get_artifact_id_by_ref
from app.db.models import Artifact
from app.db.session import orm_session
from app.schemas.lineage import (
    ArtifactLineageEdge,
    ArtifactLineageGraph,
    ArtifactLineageNode,
)


class LineageServiceError(Exception):
    """Base exception for lineage service errors."""


class InvalidArtifactIdError(LineageServiceError):
    """Raised when the artifact id is missing or invalid."""


class ArtifactNotFoundError(LineageServiceError):
    """Raised when the artifact cannot be found."""


def _add_node(
    graph: ArtifactLineageGraph, artifact: Artifact, source: Optional[str]
) -> None:
    if any(node.artifact_id == artifact.id for node in graph.nodes):
        return
    default_source = source or "config_json"
    graph.nodes.append(
        ArtifactLineageNode(
            artifact_id=artifact.id,
            name=artifact.name,
            source=default_source,
            metadata=(
                {"source_url": artifact.source_url} if artifact.source_url else None
            ),
        )
    )


def _add_edge(
    graph: ArtifactLineageGraph,
    from_id: int,
    to_id: int,
    relationship: str,
) -> None:
    graph.edges.append(
        ArtifactLineageEdge(
            from_node_artifact_id=from_id,
            to_node_artifact_id=to_id,
            relationship=relationship,
        )
    )


def _traverse_parents(
    session: Session, artifact: Artifact, graph: ArtifactLineageGraph
) -> None:
    current = artifact
    while current.parent_artifact_id:
        parent = session.get(Artifact, current.parent_artifact_id)
        if parent is None:
            # Try to resolve by ref if present
            if current.parent_artifact_ref:
                parent_id = get_artifact_id_by_ref(
                    session, current.parent_artifact_ref, exclude_id=current.id
                )
                parent = session.get(Artifact, parent_id) if parent_id else None
        if parent is None:
            break
        _add_node(graph, parent, "parent_artifact_id")
        _add_edge(graph, parent.id, current.id, "parent")
        current = parent


def _traverse_children(artifact: Artifact, graph: ArtifactLineageGraph) -> None:
    def _walk_children(parent: Artifact) -> None:
        for child in parent.children:
            _add_node(graph, child, "parent_artifact_id")
            _add_edge(graph, parent.id, child.id, "child")
            _walk_children(child)

    _walk_children(artifact)


def get_lineage_graph(artifact_id: int) -> ArtifactLineageGraph:
    """Return the lineage graph for an artifact."""
    if not artifact_id or artifact_id <= 0:
        raise InvalidArtifactIdError("Invalid artifact id.")

    try:
        with orm_session() as session:
            artifact = get_artifact_by_id(session, artifact_id)
            if artifact is None:
                raise ArtifactNotFoundError("Artifact not found.")

            graph = ArtifactLineageGraph(nodes=[], edges=[])
            _add_node(graph, artifact, "registry")
            _traverse_parents(session, artifact, graph)
            _traverse_children(artifact, graph)
            return graph
    except LineageServiceError:
        raise
    except Exception as exc:
        raise LineageServiceError("Lineage system encountered an error.") from exc
