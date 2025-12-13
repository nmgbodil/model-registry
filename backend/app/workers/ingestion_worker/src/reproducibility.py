import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


DEFAULT_MODEL_CARD_CANDIDATES = (
    "MODEL_CARD.md",
    "ModelCard.md",
    "modelcard.md",
    "model_card.md",
    "README.md",
    "Readme.md",
    "readme.md",
)

# Fenced code blocks: ```lang\n...\n```
FENCED_BLOCK_RE = re.compile(
    r"```(?P<lang>[a-zA-Z0-9_\-+]*)\s*\n(?P<code>.*?)(?:\n)?```",
    re.DOTALL,
)

# Simple "inline" command blocks like:
# $ python demo.py
# > python demo.py
SHELL_LINE_RE = re.compile(r"^\s*(?:\$|>)\s*(.+)\s*$")


@dataclass
class RunResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    reason: str


def find_model_card(repo_path: str, candidates: Sequence[str] = DEFAULT_MODEL_CARD_CANDIDATES) -> Optional[str]:
    """
    Find a model card file in repo root (preferred), else search recursively.
    Returns absolute path or None.
    """
    # 1) Prefer repo root candidates
    for name in candidates:
        p = os.path.join(repo_path, name)
        if os.path.isfile(p):
            return p

    # 2) Fallback: search recursively for "MODEL_CARD.md" / "README.md" variants
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f in candidates:
                return os.path.join(root, f)
    return None


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def extract_demo_blocks(markdown_text: str) -> list[tuple[str, str]]:
    """
    Extract fenced code blocks from markdown.
    Returns list of (lang, code).
    """
    blocks: list[tuple[str, str]] = []
    for m in FENCED_BLOCK_RE.finditer(markdown_text):
        lang = (m.group("lang") or "").strip().lower()
        code = m.group("code") or ""
        if code.strip():
            blocks.append((lang, code))
    return blocks


def select_runnable_snippets(blocks: list[tuple[str, str]]) -> dict[str, list[str]]:
    """
    Decide what to try running.

    Strategy:
      - Python: run python blocks (lang == "py" or "python")
      - Shell: parse shell/bash blocks for lines like `$ python ...` or `$ pip ...`
        (We do NOT run pip/install commands by default—only python commands)
    """
    python_snippets: list[str] = []
    python_cmds: list[str] = []

    for lang, code in blocks:
        if lang in ("py", "python"):
            python_snippets.append(code)
        elif lang in ("bash", "sh", "shell", "zsh"):
            for line in code.splitlines():
                mm = SHELL_LINE_RE.match(line)
                if not mm:
                    continue
                cmd = mm.group(1).strip()
                if cmd.startswith("python ") or cmd.startswith("python3 "):
                    python_cmds.append(cmd)

    return {"python_snippets": python_snippets, "python_cmds": python_cmds}


def run_python_snippet(repo_path: str, code: str, timeout_s: int = 60) -> RunResult:
    """
    Run a python snippet by writing it to a temp file and executing it.
    Uses cwd=repo_path so relative paths behave like they would for a user.
    """
    with tempfile.TemporaryDirectory() as td:
        script_path = os.path.join(td, "demo_snippet.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            proc = subprocess.run(
                ["python", script_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            ok = proc.returncode == 0
            return RunResult(
                ok=ok,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                reason="ok" if ok else "python_snippet_failed",
            )
        except subprocess.TimeoutExpired as e:
            return RunResult(
                ok=False,
                returncode=124,
                stdout=e.stdout or "",
                stderr=e.stderr or "",
                reason="timeout",
            )
        except FileNotFoundError:
            return RunResult(
                ok=False,
                returncode=127,
                stdout="",
                stderr="python executable not found",
                reason="python_not_found",
            )


def run_python_command(repo_path: str, cmd: str, timeout_s: int = 120) -> RunResult:
    """
    Run a shell-provided python command like "python demo.py --arg x".
    """
    try:
        argv = shlex.split(cmd)
        proc = subprocess.run(
            argv,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        ok = proc.returncode == 0
        return RunResult(
            ok=ok,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            reason="ok" if ok else "python_command_failed",
        )
    except subprocess.TimeoutExpired as e:
        return RunResult(
            ok=False,
            returncode=124,
            stdout=e.stdout or "",
            stderr=e.stderr or "",
            reason="timeout",
        )
    except FileNotFoundError:
        return RunResult(
            ok=False,
            returncode=127,
            stdout="",
            stderr="command executable not found",
            reason="command_not_found",
        )


def _attempt_run_all(repo_path: str, runnable: dict[str, list[str]]) -> RunResult:
    """
    Try to run:
      1) Any explicit python commands found in shell blocks
      2) Else, run each python fenced snippet
    Success is:
      - If there are python commands: ALL commands must succeed
      - Else if python snippets exist: ALL snippets must succeed
      - Else: failure "no_demo_code"
    """
    cmds = runnable["python_cmds"]
    snippets = runnable["python_snippets"]

    if cmds:
        for cmd in cmds:
            rr = run_python_command(repo_path, cmd)
            if not rr.ok:
                return rr
        return RunResult(True, 0, "", "", "ok")

    if snippets:
        for snip in snippets:
            rr = run_python_snippet(repo_path, snip)
            if not rr.ok:
                return rr
        return RunResult(True, 0, "", "", "ok")

    return RunResult(False, 0, "", "No runnable demo code blocks found in model card.", "no_demo_code")


def calculate_reproducibility_score(
    repo_path: str,
    *,
    model_card_path: Optional[str] = None,
    agent_fix: Optional[Callable[[str, RunResult], Optional[str]]] = None,
) -> tuple[float, dict]:
    """
    Compute reproducibility score for a repo:

      - 1.0 if demo runs with no changes.
      - 0.5 if demo fails, but succeeds after agent_fix(...) returns a patch.
      - 0.0 if no demo code or it doesn't run.

    agent_fix is optional. If provided, it should:
      - take (repo_path, failing_run_result)
      - and return a string "patched markdown" OR None
    In other words: you decide how your agent edits/patches the model card.
    This script will re-extract code blocks from the patched model card text and re-run.

    Returns: (score, details_dict)
    """
    if model_card_path is None:
        model_card_path = find_model_card(repo_path)

    if not model_card_path or not os.path.isfile(model_card_path):
        return 0.0, {
            "reason": "model_card_not_found",
            "model_card_path": model_card_path,
        }

    original_md = read_text(model_card_path)
    blocks = extract_demo_blocks(original_md)
    runnable = select_runnable_snippets(blocks)

    first = _attempt_run_all(repo_path, runnable)
    if first.ok:
        return 1.0, {
            "reason": "runs_as_is",
            "model_card_path": model_card_path,
        }

    # Optional "agent debugging" path
    if agent_fix is not None:
        patched_md = agent_fix(repo_path, first)
        if patched_md and patched_md.strip() and patched_md != original_md:
            patched_blocks = extract_demo_blocks(patched_md)
            patched_runnable = select_runnable_snippets(patched_blocks)
            second = _attempt_run_all(repo_path, patched_runnable)
            if second.ok:
                return 0.5, {
                    "reason": "runs_after_agent_fix",
                    "model_card_path": model_card_path,
                    "first_failure": {
                        "reason": first.reason,
                        "returncode": first.returncode,
                        "stderr_tail": first.stderr[-500:],
                    },
                }

    return 0.0, {
        "reason": "does_not_run",
        "model_card_path": model_card_path,
        "first_failure": {
            "reason": first.reason,
            "returncode": first.returncode,
            "stderr_tail": first.stderr[-500:],
        },
    }
