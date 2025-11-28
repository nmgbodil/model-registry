"""Utilities for computing artifact metadata during ingestion."""

from __future__ import annotations

from app.db.models import Artifact


def get_parent_artifact(artifact: Artifact) -> None:
    """Return the parent artifact for the given artifact."""
    # TODO: implement parent artifact lookup
    return None


def compute_checksum_sha256(artifact: Artifact) -> None:
    """Compute the SHA256 checksum of the artifact."""
    # TODO: implement checksum computation
    return None


def compute_size_bytes(artifact: Artifact) -> None:
    """Compute the total size in bytes of the artifact."""
    # TODO: implement size computation
    return None


def get_dataset_and_code_ids(artifact: Artifact) -> None:
    """Retrieve dataset and code identifiers related to the artifact."""
    # TODO: implement dataset/code ID resolution
    return None
