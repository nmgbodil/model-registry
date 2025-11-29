"""Utilities for computing artifact metadata during ingestion."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional, Tuple


def get_parent_artifact(root: Path) -> Optional[int]:
    """Return the parent artifact identifier for the given repository."""
    # TODO: implement parent artifact lookup
    return None


def compute_checksum_sha256(zip_path: Path) -> Optional[str]:
    """Compute the SHA256 checksum of the artifact archive."""
    try:
        digest = hashlib.sha256()
        with zip_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except FileNotFoundError:
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
