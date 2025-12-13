import subprocess
import pytest

import app.workers.ingestion_worker.src.reproducibility as repro


def test_find_model_card_prefers_root_candidate(tmp_path):
    root = tmp_path / "README.md"
    root.write_text("root", encoding="utf-8")

    sub = tmp_path / "docs"
    sub.mkdir()
    (sub / "README.md").write_text("nested", encoding="utf-8")

    found = repro.find_model_card(str(tmp_path))
    assert found == str(root)


def test_find_model_card_recursive_fallback(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    card = sub / "MODEL_CARD.md"
    card.write_text("card", encoding="utf-8")

    found = repro.find_model_card(str(tmp_path))
    assert found == str(card)


def test_find_model_card_none(tmp_path):
    assert repro.find_model_card(str(tmp_path)) is None


def test_extract_demo_blocks_basic():
    md = """```python
print("hello")
```

```bash
$ python demo.py
$ echo ignored
```"""
    blocks = repro.extract_demo_blocks(md)
    assert len(blocks) == 2


def test_select_runnable_snippets():
    blocks = [
        ("bash", "$ python demo.py\n"),
        ("python", "print('hi')\n"),
    ]
    runnable = repro.select_runnable_snippets(blocks)
    assert runnable["python_cmds"] == ["python demo.py"]
    assert runnable["python_snippets"] == ["print('hi')\n"]


def test_run_python_snippet_success(monkeypatch, tmp_path):
    class FakeProc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(repro.subprocess, "run", fake_run)
    result = repro.run_python_snippet(str(tmp_path), "print('hi')", timeout_s=1)
    assert result.ok


def test_run_python_snippet_timeout(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["python"], timeout=1)

    monkeypatch.setattr(repro.subprocess, "run", fake_run)
    result = repro.run_python_snippet(str(tmp_path), "while True: pass", timeout_s=1)
    assert not result.ok


def test_calculate_reproducibility_score_runs_as_is(monkeypatch, tmp_path):
    card = tmp_path / "README.md"
    card.write_text("```python\nprint('hello')\n```", encoding="utf-8")

    monkeypatch.setattr(
        repro,
        "run_python_snippet",
        lambda *a, **k: repro.RunResult(True, 0, "", "", "ok"),
    )

    score, details = repro.calculate_reproducibility_score(str(tmp_path))
    assert score == 1.0


def test_calculate_reproducibility_score_runs_after_agent_fix(monkeypatch, tmp_path):
    card = tmp_path / "README.md"
    card.write_text("```python\nprint('fail')\n```", encoding="utf-8")

    calls = {"n": 0}

    def fake_run(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return repro.RunResult(False, 1, "", "fail", "python_snippet_failed")
        return repro.RunResult(True, 0, "", "", "ok")

    monkeypatch.setattr(repro, "run_python_snippet", fake_run)

    def agent_fix(repo_path, failing_result):
        return "```python\nprint('fixed')\n```"

    score, details = repro.calculate_reproducibility_score(
        str(tmp_path), agent_fix=agent_fix
    )
    assert score == 0.5


def test_calculate_reproducibility_score_no_demo_code(tmp_path):
    card = tmp_path / "README.md"
    card.write_text("# No demo here", encoding="utf-8")

    score, details = repro.calculate_reproducibility_score(str(tmp_path))
    assert score == 0.0
