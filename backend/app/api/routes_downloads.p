# """API routes for artifact downloads."""

# from __future__ import annotations

# import io
# import re
# import shutil
# import tempfile
# from http import HTTPStatus
# from pathlib import Path
# from typing import List, Optional, Tuple

# from flask import Blueprint, jsonify, request, send_file
# from flask.typing import ResponseReturnValue
# from werkzeug.utils import secure_filename

# from ..db import get_session
# from ..models import Artifact

# # Optional HF hub
# try:
#     from huggingface_hub import snapshot_download

#     HF_AVAILABLE = True
# except Exception:
#     HF_AVAILABLE = False

# bp_downloads = Blueprint("downloads", __name__, url_prefix="/artifacts")

# # ── helpers ────────────────────────────────────────────────────────────────────

# _HF_EXT_WEIGHTS: List[str] = [
#     "*.safetensors",
#     "*.bin",
#     "*.pt",
#     "*.ckpt",
#     "pytorch_model*.bin",
#     "model*.safetensors*",
#     "model*.bin",
#     "model.safetensors.index.json",
#     "pytorch_model.bin.index.json",
# ]

# _HF_RUNTIME: List[str] = [
#     "config.json",
#     "generation_config.json",
#     "tokenizer*.json",
#     "tokenizer.model",
#     "vocab.json",
#     "merges.txt",
#     "special_tokens_map.json",
# ]


# def _is_http_url(url: str) -> bool:
#     return bool(re.match(r"^https?://", url or "", re.I))


# def _is_hf_url(url: str) -> Tuple[bool, Optional[str]]:
#     """Returns (is_hf, repo_id) for URLs like.

#     https://huggingface.co/{org_or_user}/{repo}[...]
#     """
#     m = re.match(
#         r"^https?://(?:www\.)?huggingface\.co/([^/]+)/([^/?#]+)",
#         url or "",
#         re.I,
#     )
#     if not m:
#         return False, None
#     return True, f"{m.group(1)}/{m.group(2)}"


# def _zip_dir_to_stream(folder: Path) -> io.BytesIO:
#     """Create a ZIP of `folder` in memory."""
#     mem = io.BytesIO()
#     with tempfile.TemporaryDirectory() as tmpzipdir:
#         zip_base = Path(tmpzipdir) / "bundle"
#         # shutil.make_archive expects a string base name without extension
#         shutil.make_archive(str(zip_base), "zip", root_dir=str(folder))
#         with open(str(zip_base) + ".zip", "rb") as f:
#             mem.write(f.read())
#     mem.seek(0)
#     return mem


# # ── route ─────────────────────────────────────────────────────────────────────


# @bp_downloads.get("/<artifact_type>/<int:artifact_id>/download")
# def artifact_download(artifact_type: str, artifact_id: int) -> ResponseReturnValue:
#     """Off-spec helper download.

#     GET /artifacts/{type}/{id}/download?subset=full|weights|runtime
#     - HF URLs: snapshot the repo (optionally filtered) then zip and stream.
#     - Local file/dir (file:// or absolute path): zip & stream that path.
#     - Other http(s): 302 redirect to the URL.
#     """
#     subset_raw = request.args.get("subset") or "full"
#     subset = subset_raw.lower()
#     if subset not in {"full", "weights", "runtime"}:
#         subset = "full"

#     allow_patterns: Optional[List[str]] = None
#     if subset == "weights":
#         allow_patterns = list(_HF_EXT_WEIGHTS)
#     elif subset == "runtime":
#         allow_patterns = list(_HF_EXT_WEIGHTS) + _HF_RUNTIME

#     with get_session() as s:
#         a = s.get(Artifact, artifact_id)
#         if a is None:
#             return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND

#         if hasattr(a, "type") and a.type != artifact_type:
#             return jsonify({"error": "type mismatch"}), HTTPStatus.BAD_REQUEST

#         src = (a.stored_path or "").strip()
#         safe_name = secure_filename(a.filename or f"artifact-{artifact_id}")

#         # 1) HF model/dataset URLs -> snapshot & zip
#         is_hf, repo_id = _is_hf_url(src)
#         if is_hf and repo_id and HF_AVAILABLE:
#             local_dir = snapshot_download(
#                 repo_id=repo_id,
#                 allow_patterns=allow_patterns,  # list[str] | None
#             )
#             stream = _zip_dir_to_stream(Path(local_dir))
#             filename = (
#                 f"{safe_name}.zip" if subset == "full" else f"{safe_name}-{subset}.zip"
#             )
#             return send_file(
#                 stream,
#                 mimetype="application/zip",
#                 as_attachment=True,
#                 download_name=filename,
#                 max_age=0,
#                 conditional=True,
#                 etag=False,
#                 last_modified=None,
#             )

#         # 2) local file/dir (file:// or absolute path) -> zip & stream
#         local_path = Path(src[7:]) if src.startswith("file://") else Path(src)
#         if local_path.exists():
#             target = local_path
#             if target.is_file():
#                 # Stage single file into a temp dir to zip
#                 with tempfile.TemporaryDirectory() as tmpdir:
#                     staging = Path(tmpdir) / safe_name
#                     staging.mkdir(parents=True, exist_ok=True)
#                     shutil.copy2(str(target), str(staging / target.name))
#                     stream = _zip_dir_to_stream(staging)
#             else:
#                 stream = _zip_dir_to_stream(target)

#             filename = (
#                 f"{safe_name}.zip" if subset == "full" else f"{safe_name}-{subset}.zip"
#             )
#             return send_file(
#                 stream,
#                 mimetype="application/zip",
#                 as_attachment=True,
#                 download_name=filename,
#                 max_age=0,
#                 conditional=True,
#                 etag=False,
#                 last_modified=None,
#             )

#         # 3) generic http(s) URL (non-HF) -> redirect
#         if _is_http_url(src):
#             return "", HTTPStatus.FOUND, {"Location": src}

#         return jsonify({"error": "no downloadable source"}), HTTPStatus.BAD_REQUEST
