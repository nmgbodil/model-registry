import os
import subprocess
from app.workers.ingestion_worker.src.url import Url, UrlCategory

CODE_EXTS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"}

def is_code_file(path: str) -> bool:
    """
    Check if a file is a code file based on its extension.
    
    Parameters:
    path (str): Path to the file.
    
    Returns:
    bool: True if the file is a code file, False otherwise.
    """
    _, ext = os.path.splitext(path)
    return ext in CODE_EXTS

def count_total_loc(repo_path: str) -> int:
    """
    Count total lines of code in a repository.

    Parameters:
    repo_path (str): Path to the local repository.
    
    Returns:
    int: Total lines of code in the repository.
    """
    total_loc = 0
    for root, _, files in os.walk(repo_path):
        for f in files:
            full = os.path.join(root, f)
            if not is_code_file(full):
                continue
            with open(full, "r", errors="ignore") as fh:
                for _ in fh:
                    total_loc += 1
    return total_loc

def count_reviewed_loc_for_file(repo_path: str, rel_path: str, reviewed_commits: set[str]) -> int:
    """
    Count lines of code in a file that were added via reviewed pull requests.
    
    Parameters:
    repo_path (str): Path to the local repository.
    rel_path (str): Path to the file relative to the repository root.
    reviewed_commits (set[str]): Set of commit SHAs that are considered reviewed.

    Returns:
    int: Number of lines in the file that were added via reviewed commits.
    """
    cmd = ["git", "blame", "--line-porcelain", "HEAD", "--", rel_path]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
    
    reviewed_lines = 0
    current_commit = None
    
    for line in result.stdout.splitlines():
        if line and not line.startswith("\t"):
            # header line
            parts = line.split()
            # first header line of a block: "<sha> <orig_lineno> <final_lineno> <num_lines>"
            if len(parts[0]) == 40:  # looks like a full SHA
                current_commit = parts[0]
        elif line.startswith("\t"):
            # source line; we assume current_commit is the commit
            if current_commit in reviewed_commits:
                reviewed_lines += 1
    
    return reviewed_lines

def count_reviewed_loc(repo_path: str, reviewed_commits: set[str]) -> int:
    """
    Count total lines of code in the repository that were added via reviewed pull requests.
    
    Parameters:
    repo_path (str): Path to the local repository.
    reviewed_commits (set[str]): Set of commit SHAs that are considered reviewed.
    
    Returns:
    int: Total lines of code added via reviewed commits.
    """
    reviewed_loc = 0
    for root, _, files in os.walk(repo_path):
        for f in files:
            full = os.path.join(root, f)
            if not is_code_file(full):
                continue
            rel = os.path.relpath(full, repo_path)
            reviewed_loc += count_reviewed_loc_for_file(repo_path, rel, reviewed_commits)
    return reviewed_loc

def calculate_reviewedness_score(reviewed_loc, total_loc, url: Url) -> float:
    """
    Calculate the reviewedness score from 0 to 1.

    Parameters:
    reviewed_loc (int): Lines of code added via pull requests with at least 1 review.
    total_loc (int): The total lines of code in the repo.

    Returns:
    float: The reviewedness score as a float from 0 to 1 or -1 if there is an issue. 
        - Returns 0.0 if total_items is 0 and -1.0 if a repo url is unusable or doesn't exist.
    """

    if total_loc == 0:
        score = 0.0
    elif url.category != UrlCategory.MODEL:
        score = -1.0
    else:
        score = (reviewed_loc / total_loc)

    return score
