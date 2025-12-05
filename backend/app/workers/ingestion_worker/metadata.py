"""Utilities for computing artifact metadata during ingestion."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional, Tuple

from app.prompts import build_dataset_code_extraction_prompt
from app.services.artifacts.client import HFClient
from app.services.artifacts.repo_view import RepoView
from app.services.llm_client import LLMClient
from app.utils import canonical_dataset_url


def get_parent_artifact(repo: RepoView) -> Optional[str]:
    """Return the base model reference from config.json if present in the repo."""
    try:
        data = repo.read_json("config.json")
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    # Aligns with common Hugging Face configs where downstream models
    # declare their base via this field.
    parent_ref = data.get("base_model_name_or_path")
    if isinstance(parent_ref, str) and parent_ref.strip():
        return parent_ref.strip()

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
    client = LLMClient(model="gpt-5-nano")

    try:
        result = client.invoke_json(prompt)
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None, None

    dataset_url = None
    code_url = None

    if isinstance(result, dict):
        primary = result.get("primary_dataset")
        if isinstance(primary, str) and primary.strip():
            raw_ref = primary.strip()
            dataset_url = _convert_dataset_ref_to_url(raw_ref)

        code_repos = result.get("code_repos")
        if isinstance(code_repos, list) and code_repos:
            first = code_repos[0]
            if isinstance(first, str) and first.strip():
                code_url = first.strip()

    return dataset_url, code_url


def _convert_dataset_ref_to_url(ref: str) -> str:
    if ref.startswith(("http://", "https://")):
        dataset_url = ref
    else:
        dataset_url = (
            canonical_dataset_url(ref) or f"https://huggingface.co/datasets/{ref}"
        )

    return dataset_url


def get_license(repo_id: str) -> Optional[str]:
    """Return the license for a HF model by inspecting cardData or license tags."""
    hf_client = HFClient()
    try:
        metadata = hf_client.get_model_metadata(repo_id)
    except Exception:
        return None

    card = metadata.get("cardData")
    if isinstance(card, dict):
        license = card.get("license")
        if isinstance(license, str) and license.strip():
            return license.strip()

    tags = metadata.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if not isinstance(tag, str):
                continue
            match = re.search(r"license:(.+)", tag)
            if match:
                license = match.group(1).strip()
                if license:
                    return license

    return None
