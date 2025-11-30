"""Tests for ingestion metadata helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple
from unittest.mock import MagicMock, patch

from app.services.artifacts.repo_view import RepoView
from app.workers.ingestion_worker import metadata


def _write_file(path: Path, rel: str, content: str) -> None:
    target = path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def test_get_parent_artifact_reads_config(tmp_path: Path) -> None:
    """Reads parent reference from config.json when present."""
    _write_file(
        tmp_path,
        "config.json",
        json.dumps({"base_model_name_or_path": "parent/model"}),
    )
    repo = RepoView(tmp_path)

    assert metadata.get_parent_artifact(repo) == "parent/model"


def test_get_parent_artifact_missing_returns_none(tmp_path: Path) -> None:
    """Returns None when config.json missing or invalid."""
    repo = RepoView(tmp_path)
    assert metadata.get_parent_artifact(repo) is None


def test_compute_checksum_and_size(tmp_path: Path) -> None:
    """Computes checksum and size for archive."""
    content = b"abc123"
    path = tmp_path / "archive.zip"
    path.write_bytes(content)

    checksum = metadata.compute_checksum_sha256(path)
    size = metadata.compute_size_bytes(path)

    assert (
        checksum == "6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090"
    )
    assert size == len(content)


def test_read_readme_falls_back_across_names(tmp_path: Path) -> None:
    """Falls back across README name variants."""
    _write_file(tmp_path, "README.MD", "hello world")
    repo = RepoView(tmp_path)

    assert metadata._read_readme(repo) == "hello world"


def test_get_dataset_and_code_uses_llm(monkeypatch: Any, tmp_path: Path) -> None:
    """Uses LLM client to extract dataset/code."""
    _write_file(tmp_path, "README.md", "Some content")
    repo = RepoView(tmp_path)

    prompt_captured: Tuple[str, ...] = ()

    class FakeClient:
        def __init__(self, model: str) -> None:
            self.model = model

        def invoke_json(self, prompt: str) -> Any:
            nonlocal prompt_captured
            prompt_captured = (prompt,)
            return {
                "primary_dataset": "SQuAD v1.1",
                "code_repos": ["https://github.com/demo/repo"],
            }

    monkeypatch.setattr(metadata, "LLMClient", FakeClient)
    monkeypatch.setattr(
        metadata, "build_dataset_code_extraction_prompt", lambda readme: "prompt"
    )

    dataset_ref, code_url = metadata.get_dataset_and_code(repo)

    assert dataset_ref == "https://huggingface.co/datasets/squad"
    assert code_url == "https://github.com/demo/repo"
    assert prompt_captured


def test_get_dataset_and_code_handles_llm_failures(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Returns Nones when LLM call fails."""
    _write_file(tmp_path, "README.md", "Some content")
    repo = RepoView(tmp_path)

    class FakeClient:
        def __init__(self, model: str) -> None:
            self.model = model

        def invoke_json(self, prompt: str) -> Any:
            raise RuntimeError("LLM down")

    monkeypatch.setattr(metadata, "LLMClient", FakeClient)
    monkeypatch.setattr(
        metadata, "build_dataset_code_extraction_prompt", lambda readme: "prompt"
    )

    dataset_ref, code_url = metadata.get_dataset_and_code(repo)

    assert dataset_ref is None
    assert code_url is None


@patch(
    "app.workers.ingestion_worker.metadata.HFClient.get_model_metadata",
    return_value={"cardData": {"license": "apache-2.0"}},
)
def test_get_license_prefers_card_data(mock_get_model: MagicMock) -> None:
    """Prefers license from cardData when present."""
    assert metadata.get_license("model") == "apache-2.0"
    mock_get_model.assert_called_once_with("model")


@patch(
    "app.workers.ingestion_worker.metadata.HFClient.get_model_metadata",
    return_value={"tags": ["foo", "license:mit"]},
)
def test_get_license_falls_back_to_tags(mock_get_model: MagicMock) -> None:
    """Falls back to tags prefixed with license: when cardData missing."""
    assert metadata.get_license("model") == "mit"
    mock_get_model.assert_called_once_with("model")


@patch(
    "app.workers.ingestion_worker.metadata.HFClient.get_model_metadata",
    return_value={"tags": ["foo", "bar"]},
)
def test_get_license_returns_none_when_missing(
    mock_get_model: MagicMock,
) -> None:
    """Returns None when no license info is available."""
    assert metadata.get_license("model") is None
    mock_get_model.assert_called_once_with("model")
