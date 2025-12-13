"""Tests for treescore lineage and scoring helpers."""

from typing import Any, Dict, Optional

import pytest

import app.workers.ingestion_worker.src.treescore as ts

# -----------------------
# extract_parents_from_config
# -----------------------


def test_extract_parents_from_config_single_key() -> None:
    """Extract parent from a single key."""
    cfg = {"base_model": "org/parent-model"}
    parents = ts.extract_parents_from_config(cfg)
    assert parents == ["org/parent-model"]


def test_extract_parents_from_config_list_key_and_dedup() -> None:
    """Handle list key parents and deduplicate normalized entries."""
    cfg = {
        "parents": ["org/p1", "org/p2", "org/p1", " org/p2  "],
        "base_model": "org/p3",
    }
    parents = ts.extract_parents_from_config(cfg)
    assert parents == ["org/p3", "org/p1", "org/p2"]


def test_extract_parents_from_config_model_index_nested() -> None:
    """Extract parents from nested model_index entries."""
    cfg = {
        "model_index": [
            {"base_model": "org/p1"},
            {"parents": ["org/p2", "org/p3"]},
        ]
    }
    parents = ts.extract_parents_from_config(cfg)
    assert parents == ["org/p1", "org/p2", "org/p3"]


def test_extract_parents_from_config_handles_unknown_or_empty() -> None:
    """Return empty list when no valid parents exist."""
    assert ts.extract_parents_from_config({}) == []
    assert ts.extract_parents_from_config({"base_model": ""}) == []
    assert ts.extract_parents_from_config({"parents": ["", "   "]}) == []


# -----------------------
# build_lineage_graph
# -----------------------


def test_build_lineage_graph_filters_to_existing_models() -> None:
    """Include only parents that exist in the registry."""
    # A -> [B, C], but only B exists in registry
    configs: Dict[str, Dict[str, Any]] = {
        "A": {"parents": ["B", "C"]},
        "B": {"parents": []},
        "C": {"parents": []},
    }
    exists = {"A", "B"}  # C not uploaded

    def get_model_config(mid: str) -> Optional[Dict[str, Any]]:
        return configs.get(mid)

    def model_exists(mid: str) -> bool:
        return mid in exists

    graph = ts.build_lineage_graph(
        "A",
        get_model_config=get_model_config,
        model_exists=model_exists,
    )

    assert graph.root_model_id == "A"
    assert graph.parents_by_model["A"] == ["B"]
    assert "C" not in graph.parents_by_model  # never traversed because C doesn't exist


def test_build_lineage_graph_traverses_multiple_generations() -> None:
    """Traverse multiple generations of parents."""
    # A -> B -> D ; A -> C ; all exist
    configs: Dict[str, Dict[str, Any]] = {
        "A": {"parents": ["B", "C"]},
        "B": {"parents": ["D"]},
        "C": {"parents": []},
        "D": {"parents": []},
    }
    exists = set(configs.keys())

    def get_model_config(mid: str) -> Optional[Dict[str, Any]]:
        return configs.get(mid)

    def model_exists(mid: str) -> bool:
        return mid in exists

    graph = ts.build_lineage_graph(
        "A",
        get_model_config=get_model_config,
        model_exists=model_exists,
    )

    assert graph.parents_by_model["A"] == ["B", "C"]
    assert graph.parents_by_model["B"] == ["D"]
    assert graph.parents_by_model["C"] == []
    assert graph.parents_by_model["D"] == []


def test_build_lineage_graph_handles_cycles() -> None:
    """Handle cycles without infinite loops."""
    # A -> B -> A (cycle)
    configs: Dict[str, Dict[str, Any]] = {
        "A": {"parents": ["B"]},
        "B": {"parents": ["A"]},
    }
    exists = set(configs.keys())

    def get_model_config(mid: str) -> Optional[Dict[str, Any]]:
        return configs.get(mid)

    def model_exists(mid: str) -> bool:
        return mid in exists

    graph = ts.build_lineage_graph(
        "A",
        get_model_config=get_model_config,
        model_exists=model_exists,
        max_depth=10,
    )

    assert graph.parents_by_model["A"] == ["B"]
    assert graph.parents_by_model["B"] == ["A"]


# -----------------------
# calculate_treescore
# -----------------------


def test_calculate_treescore_no_parents_returns_zero() -> None:
    """Return zero when there are no parents in the registry."""
    graph = ts.LineageGraph(root_model_id="A", parents_by_model={"A": []})

    def get_total_score(_mid: str) -> float:
        return 0.9

    score, details = ts.calculate_treescore(
        "A", lineage_graph=graph, get_total_score=get_total_score
    )
    assert score == 0.0
    assert details["reason"] == "no_parents_in_registry"


def test_calculate_treescore_average_of_direct_parents() -> None:
    """Average scores of direct parents that have scores."""
    graph = ts.LineageGraph(root_model_id="A", parents_by_model={"A": ["B", "C"]})

    scores = {"B": 0.2, "C": 0.6}

    def get_total_score(mid: str) -> Optional[float]:
        return scores.get(mid)

    score, details = ts.calculate_treescore(
        "A", lineage_graph=graph, get_total_score=get_total_score
    )
    assert score == pytest.approx(0.4)
    assert details["reason"] == "ok"
    assert details["parents"] == ["B", "C"]
    assert len(details["parents_scored"]) == 2


def test_calculate_treescore_ignores_missing_parent_scores() -> None:
    """Ignore parents without scores when averaging."""
    graph = ts.LineageGraph(root_model_id="A", parents_by_model={"A": ["B", "C", "D"]})

    scores = {"B": 0.1, "D": 0.9}  # C missing

    def get_total_score(mid: str) -> Optional[float]:
        return scores.get(mid)

    score, details = ts.calculate_treescore(
        "A", lineage_graph=graph, get_total_score=get_total_score
    )
    assert score == pytest.approx((0.1 + 0.9) / 2)
    assert details["reason"] == "ok"
    assert details["parents"] == ["B", "C", "D"]
    assert [p["model_id"] for p in details["parents_scored"]] == ["B", "D"]


def test_calculate_treescore_all_missing_scores_returns_zero() -> None:
    """Return zero when none of the parents have scores."""
    graph = ts.LineageGraph(root_model_id="A", parents_by_model={"A": ["B", "C"]})

    def get_total_score(_mid: str) -> Optional[float]:
        return None

    score, details = ts.calculate_treescore(
        "A", lineage_graph=graph, get_total_score=get_total_score
    )
    assert score == 0.0
    assert details["reason"] == "no_parent_scores_available"


# -----------------------
# compute_lineage_and_treescore (integration)
# -----------------------


def test_compute_lineage_and_treescore_integration() -> None:
    """Integration: build lineage graph then compute treescore."""
    configs: Dict[str, Dict[str, Any]] = {
        "A": {"parents": ["B", "C", "X"]},  # X not uploaded, should be filtered out
        "B": {"parents": ["D"]},
        "C": {"parents": []},
        "D": {"parents": []},
    }
    exists = {"A", "B", "C", "D"}  # X missing from registry

    total_scores = {"B": 0.3, "C": 0.9}  # direct parents only used for treescore

    def get_model_config(mid: str) -> Optional[Dict[str, Any]]:
        return configs.get(mid)

    def model_exists(mid: str) -> bool:
        return mid in exists

    def get_total_score(mid: str) -> Optional[float]:
        return total_scores.get(mid)

    graph, treescore, details = ts.compute_lineage_and_treescore(
        "A",
        get_model_config=get_model_config,
        model_exists=model_exists,
        get_total_score=get_total_score,
    )

    assert graph.parents_by_model["A"] == ["B", "C"]
    assert treescore == pytest.approx((0.3 + 0.9) / 2)
    assert details["lineage_graph"]["root"] == "A"
    assert "parents_by_model" in details["lineage_graph"]
