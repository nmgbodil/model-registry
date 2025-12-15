"""Simplified reviewedness metric placeholder."""

from __future__ import annotations

import time
from typing import Tuple


def calculate_reviewedness_for_url(url: str) -> Tuple[float, int]:
    """Return a reviewedness score (0-1) and latency_ms.

    This is a lightweight placeholder: we only detect GitHub-hosted URLs and
    return a neutral-low score to avoid blocking ingestion. Non-GitHub URLs
    return 0.0.
    """
    start = time.perf_counter()
    score = 0.0
    if "github.com" in url.lower():
        score = 0.4  # neutral placeholder; scaled later if enabled
    latency_ms = int((time.perf_counter() - start) * 1000)
    return score, latency_ms
