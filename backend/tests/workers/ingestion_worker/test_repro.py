"""Tests for reproducibility helpers."""

import subprocess
from pathlib import Path

import pytest

import app.workers.ingestion_worker.src.reproducibility as repro


def test_find_model_card_prefers_root_candidate(tmp_path: Path) -> None:
    """Prefer root-level candidate when multiple model cards exist."""
    root = tmp_path / "README.md"
    root.write_text("root", encoding="utf-8")

    sub = tmp_path / "docs"
    sub.mkdir()
    (sub / "README.md").write_text("nested", encoding="utf-8")

    found = repro.find_model_card(str(tmp_path))
    assert found == str(root)


def test_find_model_card_recursive_fallback(tmp_path: Path) -> None:
    """Find model card recursively when absent from root."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    card = sub / "MODEL_CARD.md"
    card.write_text("card", encoding="utf-8")

    found = repro.find_model_card(str(tmp_path))
    assert found == str(card)


def test_find_model_card_none(tmp_path: Path) -> None:
    """Return None when no model card is present."""
    assert repro.find_model_card(str(tmp_path)) is None


def test_extract_demo_blocks_basic() -> None:
    """Extract fenced code blocks with language tags."""
    md = """```python
print("hello")
```


```bash
$ python demo.py
$ echo ignored
```"""
    blocks = repro.extract_demo_blocks(md)
    assert len(blocks) == 2


def test_select_runnable_snippets() -> None:
    """Select runnable snippets from shell and python blocks."""
    blocks = [
        ("bash", "$ python demo.py\n"),
        ("python", "print('hi')\n"),
    ]
    runnable = repro.select_runnable_snippets(blocks)
    assert runnable["python_cmds"] == ["python demo.py"]
    assert runnable["python_snippets"] == ["print('hi')\n"]


def test_run_python_snippet_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Return ok when python snippet completes successfully."""

    class FakeProc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(*args: object, **kwargs: object) -> FakeProc:
        return FakeProc()

    monkeypatch.setattr(
        "app.workers.ingestion_worker.src.reproducibility.subprocess.run", fake_run
    )
    result = repro.run_python_snippet(str(tmp_path), "print('hi')", timeout_s=1)
    assert result.ok


def test_run_python_snippet_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Handle timeout when running python snippet."""

    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["python"], timeout=1)

    monkeypatch.setattr(
        "app.workers.ingestion_worker.src.reproducibility.subprocess.run", fake_run
    )
    result = repro.run_python_snippet(str(tmp_path), "while True: pass", timeout_s=1)
    assert not result.ok


def test_calculate_reproducibility_score_runs_as_is(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Score 1.0 when demo runs without modification."""
    card = tmp_path / "README.md"
    card.write_text("```python\nprint('hello')\n```", encoding="utf-8")

    monkeypatch.setattr(
        repro,
        "run_python_snippet",
        lambda *a, **k: repro.RunResult(True, 0, "", "", "ok"),
    )

    score, details = repro.calculate_reproducibility_score(str(tmp_path))
    assert score == 1.0


def test_calculate_reproducibility_score_runs_after_agent_fix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Score 0.5 when demo runs after applying agent patch."""
    card = tmp_path / "README.md"
    card.write_text("```python\nprint('fail')\n```", encoding="utf-8")

    calls = {"n": 0}

    def fake_run(*a: object, **k: object) -> repro.RunResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return repro.RunResult(False, 1, "", "fail", "python_snippet_failed")
        return repro.RunResult(True, 0, "", "", "ok")

    monkeypatch.setattr(repro, "run_python_snippet", fake_run)

    def agent_fix(repo_path: str, failing_result: repro.RunResult) -> str:
        return "```python\nprint('fixed')\n```"

    score, details = repro.calculate_reproducibility_score(
        str(tmp_path), agent_fix=agent_fix
    )
    assert score == 0.5


def test_calculate_reproducibility_score_no_demo_code(tmp_path: Path) -> None:
    """Score 0.0 when no runnable demo code is present."""
    card = tmp_path / "README.md"
    card.write_text("# No demo here", encoding="utf-8")

    score, details = repro.calculate_reproducibility_score(str(tmp_path))
    assert score == 0.0
