"""Placeholder tree_score metric."""

from __future__ import annotations

import time
from typing import Tuple


def calculate_tree_score_for_url(url: str) -> Tuple[float, int]:
    """Return a tree_score (0-1) and latency_ms.

    Placeholder: always returns 0.0 with minimal latency; scaled later.
    """
    start = time.perf_counter()
    latency_ms = int((time.perf_counter() - start) * 1000)
    return 0.0, latency_ms
