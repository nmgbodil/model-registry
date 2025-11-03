"""Tests for basic routes and helpers in routes_artifacts.py."""

import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

import pytest
from flask import Flask
from flask.testing import FlaskClient

# Import the blueprints and helpers under test (do NOT import Artifact from the app)
from app.api.routes_artifacts import (
    _is_hf_url,
    _iso,
    _to_envelope,
    _to_metadata,
    _validate_http_url,
    bp_artifact,
    bp_artifacts,
)

# ---------------------------
# Helpers coverage (pure funcs)
# ---------------------------


def test_iso_variants() -> None:
    """Test _iso() with datetime, string, and None inputs."""
    from datetime import datetime

    val_dt = _iso(datetime(2024, 1, 2, 3, 4, 5))
    assert val_dt is not None and val_dt.endswith("Z")

    val_str = _iso("2024-01-02 03:04:05")
    assert val_str is not None and val_str.endswith("Z")

    none_val = _iso(None)
    assert none_val is None


def test_validate_http_url() -> None:
    """Test _validate_http_url() with valid/invalid schemes."""
    assert _validate_http_url("https://example.com/path")
    assert _validate_http_url("http://example.com")
    assert not _validate_http_url("ftp://example.com")
    assert not _validate_http_url("notaurl")


def test_is_hf_url_shapes() -> None:
    """Test _is_hf_url() with model/dataset/space and non-HF URLs."""
    ok, kind, repo = _is_hf_url("https://huggingface.co/user/repo")
    assert ok and kind == "model" and repo == "user/repo"

    ok, kind, repo = _is_hf_url("https://huggingface.co/datasets/user/dsname")
    assert ok and kind == "dataset" and repo == "user/dsname"

    ok, kind, repo = _is_hf_url("https://huggingface.co/spaces/user/spacey")
    assert ok and kind == "space" and repo == "user/spacey"

    ok, kind, _ = _is_hf_url("https://example.com/not-hf")
    assert not ok and kind == "unknown"


# Minimal fake Artifact used by helper tests
@dataclass
class FakeArtifact:
    """Minimal fake Artifact for helper tests."""

    id: int
    filename: str
    stored_path: str
    type: str = "model"


def test_metadata_and_envelope_helpers() -> None:
    """Test _to_metadata() and _to_envelope() helpers."""
    a = FakeArtifact(id=1, filename="m.pt", stored_path="https://hf.co/user/repo")
    md = _to_metadata(a)  # type: ignore[arg-type]
    assert md["id"] == "1" and md["name"] == "m.pt" and md["type"] == "model"

    env = _to_envelope(a)  # type: ignore[arg-type]
    assert env["metadata"]["name"] == "m.pt"
    url_val = env["data"]["url"]
    assert isinstance(url_val, str) and url_val.startswith("https://")


# ---------------------------
# Route tests with fake session
# ---------------------------


class FakeQuery:
    """Minimal fake Query that mimics a subset of SQLAlchemy's API."""

    def __init__(self, rows: List[Any]) -> None:
        """Initialize with a list of rows to return."""
        self._rows: List[Any] = rows
        self._offset: int = 0
        self._limit: int = len(rows)

    def order_by(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        """Return self (no-op)."""
        return self

    def filter(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        """Return self (no-op)."""
        return self

    def in_(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        """Return self (no-op for 'IN' in fake)."""
        return self

    def offset(self, n: int) -> "FakeQuery":
        """Set the current offset and return self."""
        self._offset = n
        return self

    def limit(self, n: int) -> "FakeQuery":
        """Set the current limit and return self."""
        self._limit = n
        return self

    def all(self) -> List[Any]:
        """Return paginated rows based on offset/limit."""
        return self._rows[self._offset : self._offset + self._limit]

    def first(self) -> Optional[Any]:
        """Return the first row if present."""
        return self._rows[0] if self._rows else None


class FakeSession:
    """Minimal fake Session providing query/get/add/delete/flush."""

    def __init__(
        self,
        rows: Optional[List[Any]] = None,
        get_map: Optional[Dict[int, Any]] = None,
    ) -> None:
        """Initialize the session with optional rows and id->row map."""
        self._rows: List[Any] = rows or []
        self._get_map: Dict[int, Any] = get_map or {}
        self.deleted: List[Any] = []
        self.added: List[Any] = []
        self.flushed: bool = False

    def query(self, _model: Any) -> FakeQuery:
        """Return a FakeQuery over the preset rows."""
        return FakeQuery(self._rows)

    def get(self, _model: Any, artifact_id: int) -> Optional[Any]:
        """Return object for id from the preset map, if any."""
        return self._get_map.get(artifact_id)

    def add(self, x: Any) -> None:
        """Record that an object was added."""
        self.added.append(x)

    def delete(self, x: Any) -> None:
        """Record that an object was deleted."""
        self.deleted.append(x)

    def flush(self) -> None:
        """Mark that flush was called."""
        self.flushed = True


@contextmanager
def fake_get_session(session: FakeSession) -> Iterator[FakeSession]:
    """Contextmanager to mimic get_session() yielding a session."""
    yield session


@pytest.fixture
def app(monkeypatch: Any) -> Flask:
    """Create a Flask app and register blueprints with a default fake session."""
    app = Flask(__name__)
    app.register_blueprint(bp_artifacts)
    app.register_blueprint(bp_artifact)
    # default empty session for tests that don't override
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(FakeSession()),
        raising=True,
    )
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Return a test client for the Flask app fixture."""
    return app.test_client()


# ---------------------------
# /artifacts (POST list)
# ---------------------------


def test_artifacts_list_invalid_body_returns_400(client: FlaskClient) -> None:
    """Posting non-JSON should hit the invalid body branch and return 400."""
    resp = client.post(
        "/artifacts", data="not json", headers={"Content-Type": "text/plain"}
    )
    assert resp.status_code == 400
    assert "invalid body" in resp.get_data(as_text=True)


def test_artifacts_list_success_with_offset_header(
    client: FlaskClient, monkeypatch: Any
) -> None:
    """Posting a wildcard query should succeed and set the offset header."""
    rows: List[FakeArtifact] = [
        FakeArtifact(id=2, filename="b.pt", stored_path="http://x/y", type="model"),
        FakeArtifact(id=1, filename="a.pt", stored_path="http://x/z", type="dataset"),
    ]
    sess = FakeSession(rows=rows)
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    body: List[Dict[str, Any]] = [{"name": "*"}]
    resp = client.post(
        "/artifacts?offset=1",
        data=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    returned = resp.get_json()
    assert isinstance(returned, list)
    assert resp.headers.get("offset") == str(1 + len(returned))


# ---------------------------
# GET /artifacts/<type>/<id>
# ---------------------------


def test_artifact_get_not_found(client: FlaskClient, monkeypatch: Any) -> None:
    """GET for a non-existent artifact should return 404."""
    sess = FakeSession(get_map={})
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    resp = client.get("/artifacts/model/123")
    assert resp.status_code == 404


def test_artifact_get_type_mismatch(client: FlaskClient, monkeypatch: Any) -> None:
    """GET where stored type mismatches path type should return 400."""
    a = FakeArtifact(id=5, filename="x", stored_path="http://u", type="dataset")
    sess = FakeSession(get_map={5: a})
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    resp = client.get("/artifacts/model/5")
    assert resp.status_code == 400
    assert "type mismatch" in resp.get_data(as_text=True)


# ---------------------------
# PUT /artifacts/<type>/<id>
# ---------------------------


def test_artifact_put_mismatch_ids(client: FlaskClient) -> None:
    """PUT with metadata.id that doesn't match path id should return 400."""
    body: Dict[str, Any] = {
        "metadata": {"id": 999, "type": "model", "name": "n"},
        "data": {"url": "http://u"},
    }
    resp = client.put("/artifacts/model/1", json=body)
    assert resp.status_code == 400
    assert "mismatch" in resp.get_data(as_text=True)


def test_artifact_put_updates_ok(client: FlaskClient, monkeypatch: Any) -> None:
    """PUT should update filename (secure_filename underscores) and stored_path."""
    a = FakeArtifact(id=7, filename="old", stored_path="http://old", type="model")
    sess = FakeSession(get_map={7: a})
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )

    body: Dict[str, Any] = {
        "metadata": {"id": 7, "type": "model", "name": "new name"},
        "data": {"url": "http://new"},
    }
    resp = client.put("/artifacts/model/7", json=body)
    assert resp.status_code == 200
    assert sess.flushed
    # werkzeug.utils.secure_filename converts spaces to underscores by default
    assert a.filename == "new_name"
    assert a.stored_path == "http://new"


# ---------------------------
# DELETE /artifacts/<type>/<id>
# ---------------------------


def test_artifact_delete_not_found(client: FlaskClient, monkeypatch: Any) -> None:
    """DELETE for a non-existent artifact should return 404."""
    sess = FakeSession(get_map={})
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    resp = client.delete("/artifacts/model/9")
    assert resp.status_code == 404


def test_artifact_delete_ok(client: FlaskClient, monkeypatch: Any) -> None:
    """DELETE for an existing artifact should return 200 and record deletion."""
    a = FakeArtifact(id=8, filename="x", stored_path="http://u", type="model")
    sess = FakeSession(get_map={8: a})
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    resp = client.delete("/artifacts/model/8")
    assert resp.status_code == 200
    assert sess.deleted and sess.deleted[0] is a


# ---------------------------
# POST /artifact/byRegEx
# ---------------------------


def test_artifact_by_regex_missing_regex(client: FlaskClient) -> None:
    """POST byRegEx without regex should return 400."""
    resp = client.post("/artifact/byRegEx", json={})
    assert resp.status_code == 400


def test_artifact_by_regex_hits(client: FlaskClient, monkeypatch: Any) -> None:
    """POST byRegEx with a pattern should return a list (possibly empty)."""
    rows: List[FakeArtifact] = [
        FakeArtifact(
            id=10, filename="sentiment-classifier", stored_path="http://x", type="model"
        ),
        FakeArtifact(id=11, filename="other", stored_path="http://x", type="model"),
    ]
    sess = FakeSession(rows=rows)
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    resp = client.post("/artifact/byRegEx", json={"regex": ".*sentiment.*"})
    assert resp.status_code == 200
    items = resp.get_json()
    assert isinstance(items, list)


# ---------------------------
# GET /artifact/byName/<name>
# ---------------------------


def test_artifact_by_name_not_found(client: FlaskClient, monkeypatch: Any) -> None:
    """GET byName for a missing artifact should return 404."""
    sess = FakeSession(rows=[])
    monkeypatch.setattr(
        "app.api.routes_artifacts.get_session",
        lambda: fake_get_session(sess),
        raising=True,
    )
    resp = client.get("/artifact/byName/nope")
    assert resp.status_code == 404
