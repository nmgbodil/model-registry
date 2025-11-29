"""Utilities for computing artifact metadata during ingestion."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple

from app.prompts import build_dataset_code_extraction_prompt
from app.services.artifacts.repo_view import RepoView
from app.services.llm_client import LLMClient


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


def _read_readme(repo: RepoView) -> Optional[str]:
    for candidate in ("README.md", "README.MD", "README", "README.txt"):
        try:
            return repo.read_text(candidate)
        except FileNotFoundError:
            continue
        except OSError:
            return None
    return None


def get_dataset_and_code(repo: RepoView) -> Tuple[Optional[str], Optional[str]]:
    """Retrieve dataset reference and code URL via LLM extraction from README."""
    readme = _read_readme(repo)
    if not readme:
        return None, None

    prompt = build_dataset_code_extraction_prompt(readme)
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    client = LLMClient(model=model)

    try:
        result = client.invoke_json(prompt)
    except Exception:
        return None, None

    dataset_ref = None
    code_url = None

    if isinstance(result, dict):
        primary = result.get("primary_dataset")
        if isinstance(primary, str) and primary.strip():
            dataset_ref = primary.strip()

        code_repos = result.get("code_repos")
        if isinstance(code_repos, list) and code_repos:
            first = code_repos[0]
            if isinstance(first, str) and first.strip():
                code_url = first.strip()

    return dataset_ref, code_url
