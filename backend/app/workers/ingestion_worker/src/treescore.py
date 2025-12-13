# backend/app/workers/ingestion_worker/src/treescore.py

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class LineageGraph:
    """
    A lineage graph limited to models currently available in *this* registry.

    parents_by_model: child_id -> list[parent_id]
    """
    root_model_id: str
    parents_by_model: Dict[str, List[str]]


# --- Helpers: config.json lineage extraction ---------------------------------

# Keys we commonly see (or can reasonably support) for parent/base lineage
_LINEAGE_KEYS_SINGLE = (
    "base_model",
    "base_model_name_or_path",
    "parent_model",
    "parent",
    "finetuned_from",
    "fine_tuned_from",
    "trained_from",
)

_LINEAGE_KEYS_LIST = (
    "parents",
    "base_models",
    "lineage",
)


def _normalize_model_ref(value: str) -> str:
    """
    Normalize a model reference string into a registry lookup key.

    You can adapt this to your registry's canonical ID format.
    For now we keep it simple:
      - strip whitespace
      - drop trailing slashes
    """
    v = value.strip()
    while v.endswith("/"):
        v = v[:-1]
    return v


def extract_parents_from_config(config: Dict[str, Any]) -> List[str]:
    """
    Extract parent model references from a config.json-like dict.

    This intentionally supports multiple conventions to be resilient across sources
    (HuggingFace-style and custom). If multiple keys are present, we union them.

    Returns:
        A list of parent references (strings), normalized and de-duplicated
        (preserving first-seen order).
    """
    parents: List[str] = []
    seen: Set[str] = set()

    def add_ref(ref: str) -> None:
        nr = _normalize_model_ref(ref)
        if nr and nr not in seen:
            seen.add(nr)
            parents.append(nr)

    # Single-string keys
    for k in _LINEAGE_KEYS_SINGLE:
        v = config.get(k)
        if isinstance(v, str) and v.strip():
            add_ref(v)

    # List keys
    for k in _LINEAGE_KEYS_LIST:
        v = config.get(k)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    add_ref(item)

    # Common HuggingFace-ish nested metadata patterns
    # e.g., config["model_index"][0]["base_model"] or similar
    model_index = config.get("model_index")
    if isinstance(model_index, list):
        for entry in model_index:
            if not isinstance(entry, dict):
                continue
            for k in _LINEAGE_KEYS_SINGLE:
                v = entry.get(k)
                if isinstance(v, str) and v.strip():
                    add_ref(v)
            for k in _LINEAGE_KEYS_LIST:
                v = entry.get(k)
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            add_ref(item)

    return parents


def load_config_json(repo_path: str, filename: str = "config.json") -> Optional[Dict[str, Any]]:
    """
    Load a config.json from a local model artifact directory/repo path.
    Returns None if not found or invalid JSON.
    """
    path = os.path.join(repo_path, filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception:
        return None


# --- Lineage graph building ---------------------------------------------------

def build_lineage_graph(
    model_id: str,
    *,
    get_model_config: Callable[[str], Optional[Dict[str, Any]]],
    model_exists: Callable[[str], bool],
    max_depth: int = 50,
) -> LineageGraph:
    """
    Build a lineage graph for a model using only models currently uploaded to this registry.

    Parameters:
        model_id: The target model's registry ID.
        get_model_config: function(model_id) -> dict config.json (or None if missing).
        model_exists: function(model_id) -> bool indicating model is currently uploaded.
        max_depth: safety cap to prevent infinite loops / pathological graphs.

    Returns:
        LineageGraph rooted at model_id. Only includes parent edges where the parent
        exists in the registry. Cycles are handled (visited set).
    """
    parents_by_model: Dict[str, List[str]] = {}

    # BFS/DFS over parents
    stack: List[Tuple[str, int]] = [(model_id, 0)]
    visited: Set[str] = set()

    while stack:
        current, depth = stack.pop()
        if current in visited:
            continue
        visited.add(current)

        if depth >= max_depth:
            parents_by_model.setdefault(current, [])
            continue

        cfg = get_model_config(current)
        if not isinstance(cfg, dict):
            parents_by_model.setdefault(current, [])
            continue

        raw_parents = extract_parents_from_config(cfg)
        # Only include parents that exist in the registry
        existing_parents = [p for p in raw_parents if model_exists(p)]

        parents_by_model[current] = existing_parents

        for p in existing_parents:
            if p not in visited:
                stack.append((p, depth + 1))

    return LineageGraph(root_model_id=model_id, parents_by_model=parents_by_model)


# --- Treescore ----------------------------------------------------------------

def calculate_treescore(
    model_id: str,
    *,
    lineage_graph: LineageGraph,
    get_total_score: Callable[[str], Optional[float]],
) -> Tuple[float, Dict[str, Any]]:
    """
    Treescore metric:
        "Average of the total model scores of all parents of the model according to the lineage graph."

    Interpretation used here:
      - Consider the model's *direct* parents from the lineage graph.
      - Compute average of parents' total scores for parents that have a score.
      - If there are no parents (or no parents with scores), Treescore = 0.0.

    Returns:
        (treescore_float, details_dict)
    """
    parents = lineage_graph.parents_by_model.get(model_id, [])
    if not parents:
        return 0.0, {
            "reason": "no_parents_in_registry",
            "model_id": model_id,
            "parents": [],
            "parents_scored": [],
        }

    scored: List[Tuple[str, float]] = []
    for p in parents:
        s = get_total_score(p)
        if isinstance(s, (int, float)):
            scored.append((p, float(s)))

    if not scored:
        return 0.0, {
            "reason": "no_parent_scores_available",
            "model_id": model_id,
            "parents": parents,
            "parents_scored": [],
        }

    avg = sum(s for _, s in scored) / len(scored)
    return avg, {
        "reason": "ok",
        "model_id": model_id,
        "parents": parents,
        "parents_scored": [{"model_id": mid, "total_score": sc} for mid, sc in scored],
        "treescore": avg,
    }


# --- Convenience wrapper you can call from your pipeline ----------------------

def compute_lineage_and_treescore(
    model_id: str,
    *,
    get_model_config: Callable[[str], Optional[Dict[str, Any]]],
    model_exists: Callable[[str], bool],
    get_total_score: Callable[[str], Optional[float]],
) -> Tuple[LineageGraph, float, Dict[str, Any]]:
    """
    Convenience: build lineage graph (limited to current registry), then compute treescore.

    Returns:
        (lineage_graph, treescore, details)
    """
    graph = build_lineage_graph(
        model_id,
        get_model_config=get_model_config,
        model_exists=model_exists,
    )
    treescore, details = calculate_treescore(
        model_id,
        lineage_graph=graph,
        get_total_score=get_total_score,
    )
    details["lineage_graph"] = {
        "root": graph.root_model_id,
        "parents_by_model": graph.parents_by_model,
    }
    return graph, treescore, details
