"""Unit tests for lineage service graph construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import pytest

from app.services import lineage
from app.services.lineage import (
    ArtifactNotFoundError,
    InvalidArtifactIdError,
    LineageServiceError,
)
from tests.utils import fake_session_cm


@dataclass
class FakeArtifact:
    """Lightweight artifact stand-in for lineage traversal."""

    id: int
    name: str
    source_url: Optional[str] = None
    parent_artifact_id: Optional[int] = None
    parent_artifact_ref: Optional[str] = None
    children: list["FakeArtifact"] = field(default_factory=list)


class FakeSession:
    """Fake SQLAlchemy session returning canned artifacts."""

    def __init__(self, artifacts: Dict[int, FakeArtifact]) -> None:
        self.artifacts = artifacts

    def get(self, model: object, artifact_id: int) -> Optional[FakeArtifact]:
        """Return artifact by id."""
        return self.artifacts.get(artifact_id)


def test_get_lineage_graph_invalid_id() -> None:
    """Raise on non-positive artifact id."""
    with pytest.raises(InvalidArtifactIdError):
        lineage.get_lineage_graph(0)


def test_get_lineage_graph_builds_nodes_and_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Construct graph with parent and child relationships."""
    parent = FakeArtifact(id=1, name="parent", source_url="https://example.com/p")
    root = FakeArtifact(id=2, name="root", parent_artifact_id=1)
    child = FakeArtifact(id=3, name="child")
    root.children.append(child)
    artifacts = {1: parent, 2: root, 3: child}
    fake_session = FakeSession(artifacts)

    monkeypatch.setattr(lineage, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(
        lineage, "get_artifact_by_id", lambda session, aid: artifacts.get(aid)
    )
    monkeypatch.setattr(
        lineage,
        "get_artifact_id_by_ref",
        lambda session, ref, exclude_id=None: None,
    )

    graph = lineage.get_lineage_graph(2)

    assert {node.artifact_id for node in graph.nodes} == {1, 2, 3}
    assert any(edge.relationship == "base_model" for edge in graph.edges)
    assert any(
        edge.from_node_artifact_id == 2
        and edge.to_node_artifact_id == 3
        and edge.relationship == "child"
        for edge in graph.edges
    )
    parent_node = next(node for node in graph.nodes if node.artifact_id == 1)
    assert parent_node.metadata == {"source_url": "https://example.com/p"}


def test_get_lineage_graph_uses_ref_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve parent via reference when direct lookup missing."""
    root = FakeArtifact(
        id=5, name="root", parent_artifact_id=99, parent_artifact_ref="ref-1"
    )
    parent = FakeArtifact(id=7, name="resolved-parent")
    artifacts = {5: root, 7: parent}
    fake_session = FakeSession(artifacts)

    monkeypatch.setattr(lineage, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(
        lineage, "get_artifact_by_id", lambda session, aid: artifacts.get(aid)
    )
    monkeypatch.setattr(
        lineage,
        "get_artifact_id_by_ref",
        lambda session, ref, exclude_id=None: 7 if ref == "ref-1" else None,
    )

    graph = lineage.get_lineage_graph(5)

    assert {node.artifact_id for node in graph.nodes} == {5, 7}
    assert any(
        edge.from_node_artifact_id == 7 and edge.to_node_artifact_id == 5
        for edge in graph.edges
    )


def test_get_lineage_graph_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise when artifact does not exist."""
    fake_session = FakeSession({})
    monkeypatch.setattr(lineage, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(lineage, "get_artifact_by_id", lambda session, aid: None)

    with pytest.raises(ArtifactNotFoundError):
        lineage.get_lineage_graph(10)


def test_get_lineage_graph_wraps_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrap unexpected exceptions in LineageServiceError."""
    fake_session = FakeSession({})
    monkeypatch.setattr(lineage, "orm_session", lambda: fake_session_cm(fake_session))
    monkeypatch.setattr(
        lineage,
        "get_artifact_by_id",
        lambda session, aid: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(LineageServiceError):
        lineage.get_lineage_graph(1)
