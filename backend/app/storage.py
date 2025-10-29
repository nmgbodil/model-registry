"""Local storage utilities for artifact files."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final, Tuple

from werkzeug.datastructures import FileStorage


def save_file(file: FileStorage, dest_dir: Path) -> Tuple[Path, str, int]:
    """Save an uploaded file into dest_dir, returning (path, sha256, size)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Use a content hash prefix to avoid collisions.
    hasher: Final = hashlib.sha256()
    chunk = file.stream.read(8192)
    total = 0
    parts: list[bytes] = []
    while chunk:
        parts.append(chunk)
        hasher.update(chunk)
        total += len(chunk)
        chunk = file.stream.read(8192)
    digest = hasher.hexdigest()

    safe_name = f"{digest[:16]}_{file.filename or 'artifact.bin'}"
    final_path = dest_dir / safe_name
    with final_path.open("wb") as fh:
        for p in parts:
            fh.write(p)

    # Reset stream for any reuse
    file.stream.seek(0)
    return final_path, digest, total
