"""Tests covering reviewedness helper functions."""

from pathlib import Path
from typing import Set

import pytest

from app.workers.ingestion_worker.src.reviewedness import (
    calculate_reviewedness_score,
    count_reviewed_loc,
    count_reviewed_loc_for_file,
    count_total_loc,
    is_code_file,
)
from app.workers.ingestion_worker.src.url import Url, UrlCategory

# ------------------------
# is_code_file
# ------------------------


@pytest.mark.parametrize(
    "path,expected",
    [
        ("file.py", True),
        ("file.js", True),
        ("file.ts", True),
        ("file.java", True),
        ("file.cpp", True),
        ("file.c", True),
        ("file.go", True),
        ("file.rs", True),
        ("README.md", False),
        ("image.png", False),
        ("noext", False),
        ("SCRIPT.PY", False),  # case-sensitive by design
    ],
)
def test_is_code_file(path: str, expected: bool) -> None:
    """Return True only for supported code file extensions."""
    assert is_code_file(path) == expected


# ------------------------
# count_total_loc
# ------------------------


def test_count_total_loc_counts_only_code_files(tmp_path: Path) -> None:
    """Count LOC from code files while ignoring non-code files."""
    py_file = tmp_path / "a.py"
    js_file = tmp_path / "b.js"
    txt_file = tmp_path / "c.txt"

    py_file.write_text("1\n2\n", encoding="utf-8")
    js_file.write_text("1\n", encoding="utf-8")
    txt_file.write_text("ignore\nignore\n", encoding="utf-8")

    assert count_total_loc(str(tmp_path)) == 3


def test_count_total_loc_empty_repo(tmp_path: Path) -> None:
    """Return zero when repository directory is empty."""
    assert count_total_loc(str(tmp_path)) == 0


# ------------------------
# count_reviewed_loc_for_file
# ------------------------


def test_count_reviewed_loc_for_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Count reviewed lines for a file based on git blame output."""
    repo_path = tmp_path
    rel_path = "dummy.py"

    sha1 = "a" * 40
    sha2 = "b" * 40

    blame_output = f"""\
{sha1} 1 1 1
author Alice
\tline one
{sha2} 2 2 1
author Bob
\tline two
{sha1} 3 3 2
author Alice
\tline three
\tline four
"""

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout
            self.returncode = 0

    def fake_run(*args: object, **kwargs: object) -> FakeCompletedProcess:
        return FakeCompletedProcess(blame_output)

    monkeypatch.setattr("subprocess.run", fake_run)

    reviewed_commits: Set[str] = {sha1}
    reviewed = count_reviewed_loc_for_file(str(repo_path), rel_path, reviewed_commits)

    assert reviewed == 3


def test_count_reviewed_loc_for_file_no_reviewed_commits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Return zero when no commits are marked as reviewed."""
    sha = "c" * 40

    blame_output = f"""\
{sha} 1 1 2
author Carol
\tline one
\tline two
"""

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout
            self.returncode = 0

    def fake_run(*args: object, **kwargs: object) -> FakeCompletedProcess:
        return FakeCompletedProcess(blame_output)

    monkeypatch.setattr("subprocess.run", fake_run)

    reviewed = count_reviewed_loc_for_file(
        str(tmp_path), "file.py", reviewed_commits=set[str]()
    )

    assert reviewed == 0


# ------------------------
# count_reviewed_loc
# ------------------------


def test_count_reviewed_loc_only_code_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aggregate reviewed LOC only for code files."""
    py_file = tmp_path / "a.py"
    txt_file = tmp_path / "b.txt"
    sub = tmp_path / "sub"
    sub.mkdir()
    js_file = sub / "c.js"

    py_file.write_text("x\n")
    txt_file.write_text("ignore\n")
    js_file.write_text("y\nz\n")

    def fake_count(_repo: str, rel_path: str, _commits: Set[str]) -> int:
        if rel_path.endswith("a.py"):
            return 2
        if rel_path.endswith("c.js"):
            return 3
        pytest.fail(f"Non-code file passed: {rel_path}")

    monkeypatch.setattr(
        "app.workers.ingestion_worker.src.reviewedness.count_reviewed_loc_for_file",
        fake_count,
    )

    reviewed = count_reviewed_loc(str(tmp_path), {"dummy"})

    assert reviewed == 5


def test_count_reviewed_loc_empty_repo(tmp_path: Path) -> None:
    """Return zero when repository has no files."""
    assert count_reviewed_loc(str(tmp_path), {"dummy"}) == 0


# ------------------------
# calculate_reviewedness_score
# ------------------------


def make_url(category: UrlCategory) -> Url:
    """Build a Url with a pre-set category for testing."""
    return Url("placeholder", category)


def test_reviewedness_score_zero_when_total_loc_zero() -> None:
    """Score is zero when there is no total LOC."""
    url = make_url(UrlCategory.MODEL)
    assert calculate_reviewedness_score(5, 0, url) == 0.0


def test_reviewedness_score_negative_one_for_non_model_url() -> None:
    """Return sentinel value when URL category is not model."""
    url = make_url(UrlCategory.INVALID)
    assert calculate_reviewedness_score(5, 10, url) == -1.0


def test_reviewedness_score_ratio_for_model() -> None:
    """Return reviewed/total ratio for model URLs."""
    url = make_url(UrlCategory.MODEL)
    assert calculate_reviewedness_score(25, 100, url) == pytest.approx(0.25)
