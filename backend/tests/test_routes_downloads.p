# """Tests for artifact download routes (app.api.routes_downloads)."""

# from __future__ import annotations

# import io
# import os
# import tempfile
# from contextlib import contextmanager
# from dataclasses import dataclass
# from typing import Any, Dict, Iterator, List, Optional, Tuple

# import pytest
# from flask import Flask
# from flask.testing import FlaskClient

# from app.api.routes_downloads import (
#     _is_hf_url,
#     _is_http_url,
#     _zip_dir_to_stream,
#     bp_downloads,
# )

# # ──────────────────────────
# # Quick unit tests (helpers)
# # ──────────────────────────


# def test_is_http_url() -> None:
#     """http/https are valid; others should be rejected."""
#     assert _is_http_url("http://x")
#     assert _is_http_url("https://x/y")
#     assert not _is_http_url("ftp://x")
#     assert not _is_http_url("notaurl")


# def test_is_hf_url() -> None:
#     """Recognize huggingface repo shapes."""
#     ok, repo = _is_hf_url("https://huggingface.co/org/name")
#     assert ok and repo == "org/name"

#     ok, repo = _is_hf_url("https://example.com/not-hf")
#     assert not ok and repo is None


# def test_zip_dir_to_stream() -> None:
#     """Create an in-memory zip from a temp folder."""
#     with tempfile.TemporaryDirectory() as d:
#         fpath = os.path.join(d, "file.txt")
#         with open(fpath, "w", encoding="utf-8") as f:
#             f.write("hello")
#         stream = _zip_dir_to_stream(os.path.abspath(d))  # type: ignore[arg-type]
#         assert isinstance(stream, io.BytesIO)
#         assert stream.getbuffer().nbytes > 0


# # ───────────────────────────────
# # Fake ORM/session for the route
# # ───────────────────────────────


# @dataclass
# class FakeArtifact:
#     """Minimal fake Artifact for download route tests."""

#     id: int
#     filename: str
#     stored_path: str
#     type: str = "model"


# class FakeQuery:
#     """Query not used directly here; placeholder to match API if needed."""

#     def __init__(self, rows: List[Any]) -> None:
#         self._rows = rows

#     def filter(self, *_a: Any, **_kw: Any) -> "FakeQuery":
#         """No-op filter; returns self."""
#         return self

#     def first(self) -> Optional[Any]:
#         """Return the first row or None."""
#         return self._rows[0] if self._rows else None


# class FakeSession:
#     """Very small session stub with get()."""

#     def __init__(self, get_map: Optional[Dict[int, Any]] = None) -> None:
#         """Initialize with a map of id -> Artifact."""
#         self._get_map: Dict[int, Any] = get_map or {}

#     def get(self, _model: Any, artifact_id: int) -> Optional[Any]:
#         """Return the artifact by ID or None."""
#         return self._get_map.get(artifact_id)


# @contextmanager
# def fake_get_session(session: FakeSession) -> Iterator[FakeSession]:
#     """Context manager that mimics get_session() yielding a session."""
#     yield session


# # ─────────────────────────────
# # Flask fixtures / app wiring
# # ─────────────────────────────


# @pytest.fixture
# def app(monkeypatch: Any) -> Flask:
#     """Create a minimal Flask app with just the downloads blueprint."""
#     app = Flask(__name__)
#     app.register_blueprint(bp_downloads)
#     # default: empty session (override per-test)
#     monkeypatch.setattr(
#         "app.api.routes_downloads.get_session",
#         lambda: fake_get_session(FakeSession({})),
#         raising=True,
#     )
#     return app


# @pytest.fixture
# def client(app: Flask) -> FlaskClient:
#     """Test client for the downloads blueprint."""
#     return app.test_client()


# # ─────────────────────────────
# # Route behavior happy/sad path
# # ─────────────────────────────


# def test_download_not_found(client: FlaskClient, monkeypatch: Any) -> None:
#     """Returns 404 when the artifact does not exist."""
#     sess = FakeSession(get_map={})
#     monkeypatch.setattr(
#         "app.api.routes_downloads.get_session",
#         lambda: fake_get_session(sess),
#         raising=True,
#     )
#     resp = client.get("/artifacts/model/999/download")
#     assert resp.status_code == 404


# def test_download_type_mismatch(client: FlaskClient, monkeypatch: Any) -> None:
#     """Returns 400 when stored type differs from the path type segment."""
#     art = FakeArtifact(id=1, filename="m", stored_path="http://x", type="dataset")
#     sess = FakeSession(get_map={1: art})
#     monkeypatch.setattr(
#         "app.api.routes_downloads.get_session",
#         lambda: fake_get_session(sess),
#         raising=True,
#     )
#     resp = client.get("/artifacts/model/1/download")
#     assert resp.status_code == 400
#     assert "type mismatch" in resp.get_data(as_text=True)


# def test_download_redirect_for_generic_http(
#     client: FlaskClient, monkeypatch: Any
# ) -> None:
#     """Generic non-HF http(s) should issue a 302 redirect to the source."""
#     src = "https://example.com/file.bin"
#     art = FakeArtifact(id=2, filename="file", stored_path=src, type="model")
#     sess = FakeSession(get_map={2: art})
#     monkeypatch.setattr(
#         "app.api.routes_downloads.get_session",
#         lambda: fake_get_session(sess),
#         raising=True,
#     )

#     resp = client.get("/artifacts/model/2/download")
#     assert resp.status_code == 302
#     assert resp.headers.get("Location") == src


# def test_download_local_file_zips(client: FlaskClient, monkeypatch: Any) -> None:
#     """Absolute local file path is staged into a zip and streamed."""
#     with tempfile.TemporaryDirectory() as d:
#         fpath = os.path.join(d, "weights.safetensors")
#         with open(fpath, "wb") as f:
#             f.write(b"\x00\x01\x02")

#         art = FakeArtifact(id=3, filename="my model", stored_path=fpath, type="model")
#         sess = FakeSession(get_map={3: art})
#         monkeypatch.setattr(
#             "app.api.routes_downloads.get_session",
#             lambda: fake_get_session(sess),
#             raising=True,
#         )

#         resp = client.get("/artifacts/model/3/download")
#         assert resp.status_code == 200
#         # Flask sets Content-Type and Content-Disposition
#         assert "application/zip" in resp.headers.get("Content-Type", "")
#         disp = resp.headers.get("Content-Disposition", "")
#         # secure_filename("my model") -> "my_model"
#         assert 'filename="my_model.zip"' in disp or "filename=my_model.zip" in disp
#         assert resp.data  # not empty


# def test_download_local_dir_zips(client: FlaskClient, monkeypatch: Any) -> None:
#     """Directory path is zipped and streamed."""
#     with tempfile.TemporaryDirectory() as d:
#         # Create a couple of files
#         for name in ("a.txt", "b.txt"):
#             with open(os.path.join(d, name), "w", encoding="utf-8") as f:
#                 f.write("x")

#         art = FakeArtifact(id=4, filename="bundle", stored_path=d, type="model")
#         sess = FakeSession(get_map={4: art})
#         monkeypatch.setattr(
#             "app.api.routes_downloads.get_session",
#             lambda: fake_get_session(sess),
#             raising=True,
#         )

#         resp = client.get("/artifacts/model/4/download?subset=runtime")
#         assert resp.status_code == 200
#         assert "application/zip" in resp.headers.get("Content-Type", "")
#         disp = resp.headers.get("Content-Disposition", "")
#         assert (
#             'filename="bundle-runtime.zip"' in disp
#             or "filename=bundle-runtime.zip" in disp
#         )
#         assert resp.data


# def test_download_hf_snapshot_full_and_weights(
#     client: FlaskClient, monkeypatch: Any
# ) -> None:
#     """HF-backed URL should call snapshot_download..."""
#     # Make a temporary folder that our fake snapshot will "download" to
#     tmp_dir = tempfile.mkdtemp()
#     with open(os.path.join(tmp_dir, "dummy.txt"), "w", encoding="utf-8") as f:
#         f.write("ok")

#     calls: List[Tuple[str, Optional[List[str]]]] = []

#     def fake_snapshot_download(
#         *, repo_id: str, allow_patterns: Optional[List[str]] = None, **_kw: Any
#     ) -> str:
#         """Record calls and return our temp folder path."""
#         calls.append((repo_id, allow_patterns))
#         return tmp_dir

#     art = FakeArtifact(
#         id=5,
#         filename="hf-model",
#         stored_path="https://huggingface.co/org/model-x",
#         type="model",
#     )
#     sess = FakeSession(get_map={5: art})

#     # Force HF path active and patch snapshot function
#     monkeypatch.setattr("app.api.routes_downloads.HF_AVAILABLE", True, raising=True)
#     monkeypatch.setattr(
#         "app.api.routes_downloads.snapshot_download",
#         fake_snapshot_download,
#         raising=True,
#     )
#     monkeypatch.setattr(
#         "app.api.routes_downloads.get_session",
#         lambda: fake_get_session(sess),
#         raising=True,
#     )

#     # 1) subset=full -> allow_patterns None
#     resp_full = client.get("/artifacts/model/5/download?subset=full")
#     assert resp_full.status_code == 200
#     assert calls[-1][0] == "org/model-x"
#     assert calls[-1][1] is None
#     disp_full = resp_full.headers.get("Content-Disposition", "")
#     assert (
#         'filename="hf-model.zip"' in disp_full or "filename=hf-model.zip" in disp_full
#     )

#     # 2) subset=weights -> allow_patterns list (not None)
#     resp_weights = client.get("/artifacts/model/5/download?subset=weights")
#     assert resp_weights.status_code == 200
#     assert calls[-1][0] == "org/model-x"
#     assert calls[-1][1] is not None and isinstance(calls[-1][1], list)
#     disp_w = resp_weights.headers.get("Content-Disposition", "")
#     assert (
#         'filename="hf-model-weights.zip"' in disp_w
#         or "filename=hf-model-weights.zip" in disp_w
#     )
