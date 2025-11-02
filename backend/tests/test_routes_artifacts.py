# backend/tests/test_routes_artifacts.py
from __future__ import annotations

import io
from http import HTTPStatus


def _upload_txt(client, name="a.txt", content=b"hello") -> dict:
    resp = client.post(
        "/artifacts",
        data={"file": (io.BytesIO(content), name)},
        content_type="multipart/form-data",
    )
    assert resp.status_code == HTTPStatus.CREATED
    return resp.get_json()


# ── CREATE (upload) ────────────────────────────────────────────────────────────
def test_upload_missing_file(client):
    resp = client.post("/artifacts", data={}, content_type="multipart/form-data")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "missing file field"


def test_upload_empty_filename(client):
    # Werkzeug treats empty filename as "", simulate that:
    resp = client.post(
        "/artifacts",
        data={"file": (io.BytesIO(b"x"), "")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "empty filename"


def test_upload_disallowed_ext(client):
    resp = client.post(
        "/artifacts",
        data={"file": (io.BytesIO(b"x"), "bad.exe")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "file type not allowed"


def test_upload_ok(client):
    data = _upload_txt(client)
    assert set(data) >= {
        "id",
        "filename",
        "size_bytes",
        "checksum_sha256",
        "content_type",
        "created_at",
    }
    assert data["filename"] == "a.txt"
    assert data["size_bytes"] == 5


# ── READ (list) ────────────────────────────────────────────────────────────────
def test_list_basic_and_pagination(client):
    a1 = _upload_txt(client, name="one.txt")
    a2 = _upload_txt(client, name="two.txt")
    # latest-first, so a2 then a1 at offset 1
    resp = client.get("/artifacts?limit=1&offset=1")
    assert resp.status_code == HTTPStatus.OK
    js = resp.get_json()
    assert js["limit"] == 1 and js["offset"] == 1
    assert len(js["items"]) == 1
    assert js["items"][0]["id"] == a1["id"]


def test_list_bad_limit_offset_are_sanitized(client):
    _upload_txt(client)
    resp = client.get("/artifacts?limit=notint&offset=alsonotint")
    assert resp.status_code == HTTPStatus.OK
    js = resp.get_json()
    # falls back to defaults 20/0 per route logic
    assert js["limit"] == 20 and js["offset"] == 0
    assert len(js["items"]) >= 1


# ── READ (search) ──────────────────────────────────────────────────────────────
def test_search_missing_q(client):
    resp = client.get("/artifacts/search")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "missing q"


def test_search_hits(client):
    _upload_txt(client, name="keep.txt")
    _upload_txt(client, name="ignore.md")  # allowed by conftest
    resp = client.get("/artifacts/search?q=keep")
    assert resp.status_code == HTTPStatus.OK
    js = resp.get_json()
    assert js["q"] == "keep"
    assert any(item["filename"] == "keep.txt" for item in js["items"])


# ── READ (single) ──────────────────────────────────────────────────────────────
def test_get_not_found(client):
    resp = client.get("/artifacts/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_get_ok(client):
    a = _upload_txt(client)
    resp = client.get(f"/artifacts/{a['id']}")
    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json()["id"] == a["id"]


# ── UPDATE (patch) ─────────────────────────────────────────────────────────────
def test_patch_no_fields(client):
    a = _upload_txt(client)
    resp = client.patch(f"/artifacts/{a['id']}", json={})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "no updatable fields supplied"


def test_patch_invalid_filename(client):
    a = _upload_txt(client)
    resp = client.patch(f"/artifacts/{a['id']}", json={"filename": "   "})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "invalid filename"


def test_patch_disallowed_ext(client):
    a = _upload_txt(client)
    resp = client.patch(f"/artifacts/{a['id']}", json={"filename": "x.exe"})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
    assert resp.get_json()["error"] == "file type not allowed"


def test_patch_not_found(client):
    resp = client.patch("/artifacts/999999", json={"filename": "ok.txt"})
    # ok.txt is allowed by conftest
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_patch_ok(client):
    a = _upload_txt(client)
    resp = client.patch(f"/artifacts/{a['id']}", json={"filename": "renamed.txt"})
    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json()["filename"] == "renamed.txt"


# ── DOWNLOAD ───────────────────────────────────────────────────────────────────
def test_download_not_found(client):
    resp = client.get("/artifacts/999999/download")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_download_missing_file_on_disk_returns_500(client, tmp_path, monkeypatch):
    a = _upload_txt(client)
    # simulate file missing on disk
    # fetch to get stored_path
    meta = client.get(f"/artifacts/{a['id']}").get_json()
    # now delete the physical file
    # NOTE: UPLOAD_DIR already isolated by conftest
    from pathlib import Path

    p = Path(meta["checksum_sha256"])  # wrong; need stored_path -> grab through DB
    # Better: hit the download to get 200 first, then nuke the file path we know.
    # We can retrieve stored_path by querying DB is overkill; simpler: just delete all files in upload dir.
    from app.api import routes_artifacts as ra

    for f in ra.settings.UPLOAD_DIR.glob("*"):
        f.unlink(missing_ok=True)

    resp = client.get(f"/artifacts/{a['id']}/download")
    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_download_ok(client):
    a = _upload_txt(client, content=b"download-me")
    resp = client.get(f"/artifacts/{a['id']}/download")
    assert resp.status_code == HTTPStatus.OK
    assert resp.data == b"download-me"


# ── DELETE ─────────────────────────────────────────────────────────────────────
def test_delete_not_found(client):
    resp = client.delete("/artifacts/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_delete_ok_then_404(client):
    a = _upload_txt(client)
    resp = client.delete(f"/artifacts/{a['id']}")
    assert resp.status_code == HTTPStatus.NO_CONTENT
    resp2 = client.get(f"/artifacts/{a['id']}")
    assert resp2.status_code == HTTPStatus.NOT_FOUND
