"""Utilities for computing artifact metadata during ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple


def get_parent_artifact(root: Path) -> Optional[int]:
    """Return the parent artifact identifier for the given repository."""
    # TODO: implement parent artifact lookup
    return None


def compute_checksum_sha256(root: Path) -> Optional[str]:
    """Compute the SHA256 checksum of the artifact contents."""
    # TODO: implement checksum computation
    return None


def compute_size_bytes(zip_path: Path) -> Optional[int]:
    """Compute the size in bytes of the generated artifact archive."""
    try:
        return zip_path.stat().st_size
    except FileNotFoundError:
        return None


def get_dataset_and_code_ids(root: Path) -> Tuple[Optional[int], Optional[int]]:
    """Retrieve dataset and code identifiers related to the artifact."""
    # TODO: implement dataset/code ID resolution
    return None, None
