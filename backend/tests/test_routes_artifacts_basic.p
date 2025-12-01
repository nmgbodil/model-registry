"""Basic tests for artifact routes."""

# from __future__ import annotations

# from typing import Any, Dict, Generator, List

# import pytest
# from flask import Flask
# from flask.testing import FlaskClient

# from app import create_app
# from app.db.models import Artifact
# from app.db.session import orm_session


# @pytest.fixture
# def app() -> Generator[Flask, None, None]:
#     """Create a Flask app and ensure a clean database."""
#     app = create_app()
#     with orm_session() as session:
#         session.query(Artifact).delete()
#     yield app


# @pytest.fixture
# def client(app: Flask) -> FlaskClient:
#     """Return a test client for the Flask app fixture."""
#     return app.test_client()


# def _seed_artifacts(rows: List[Dict[str, Any]]) -> None:
#     """Insert artifacts for test setup."""
#     with orm_session() as session:
#         for row in rows:
#             session.add(Artifact(**row))
#         session.flush()
#         session.commit()


# def test_artifacts_list_invalid_body_returns_400(client: FlaskClient) -> None:
#     """POST /artifacts with non-JSON should 400."""
#     resp = client.post(
#         "/api/artifacts",
#         data="not json",
#         headers={"Content-Type": "text/plain"},
#     )
#     assert resp.status_code == 400
#     assert "invalid body" in resp.get_data(as_text=True)


# def test_artifacts_list_success_with_offset_header(client: FlaskClient) -> None:
#     """POST /artifacts returns list and offset header."""
#     _seed_artifacts(
#         [
#             {"id": 1, "name": "a.pt", "type": "model", "source_url": "http://x/z"},
#             {"id": 2, "name": "b.pt", "type": "model", "source_url": "http://x/y"},
#         ]
#     )
#     body: List[Dict[str, Any]] = [{"name": "*"}]
#     resp = client.post(
#         "/api/artifacts?offset=1",
#         json=body,
#     )
#     assert resp.status_code == 200
#     returned = resp.get_json()
#     assert isinstance(returned, list)
#     assert resp.headers.get("offset") == str(1 + len(returned))


# def test_artifact_get_not_found(client: FlaskClient) -> None:
#     """GET artifact by id returns 404 when missing."""
#     resp = client.get("/api/artifacts/model/123")
#     assert resp.status_code == 404


# def test_artifact_get_type_mismatch(client: FlaskClient) -> None:
#     """GET artifact returns 400 on type mismatch."""
#     _seed_artifacts(
#         [{"id": 5, "name": "x", "type": "dataset", "source_url": "http://u"}]
#     )
#     resp = client.get("/api/artifacts/model/5")
#     assert resp.status_code == 400
#     assert "type mismatch" in resp.get_data(as_text=True)


# def test_artifact_put_mismatch_ids(client: FlaskClient) -> None:
#     """PUT artifact rejects when id/type mismatch."""
#     body: Dict[str, Any] = {
#         "metadata": {"id": 999, "type": "model", "name": "n"},
#         "data": {"url": "http://u"},
#     }
#     resp = client.put("/api/artifacts/model/1", json=body)
#     assert resp.status_code == 400
#     assert "mismatch" in resp.get_data(as_text=True)


# def test_artifact_put_updates_ok(client: FlaskClient) -> None:
#     """PUT artifact updates name and url when ids match."""
#     _seed_artifacts(
#         [{"id": 7, "name": "old", "type": "model", "source_url": "http://old"}]
#     )
#     body: Dict[str, Any] = {
#         "metadata": {"id": 7, "type": "model", "name": "new name"},
#         "data": {"url": "http://new"},
#     }
#     resp = client.put("/api/artifacts/model/7", json=body)
#     assert resp.status_code == 200
#     with orm_session() as session:
#         updated = session.get(Artifact, 7)
#         assert updated is not None
#         assert updated.name == "new_name"
#         assert updated.source_url == "http://new"


# def test_artifact_delete_not_found(client: FlaskClient) -> None:
#     """DELETE artifact returns 404 when missing."""
#     resp = client.delete("/api/artifacts/model/9")
#     assert resp.status_code == 404


# def test_artifact_delete_ok(client: FlaskClient) -> None:
#     """DELETE artifact removes record when present."""
#     _seed_artifacts([{"id": 8, "name": "x", "type": "model", "source_url": "http://u"}])
#     resp = client.delete("/api/artifacts/model/8")
#     assert resp.status_code == 200
#     with orm_session() as session:
#         assert session.get(Artifact, 8) is None


# def test_artifact_by_regex_missing_regex(client: FlaskClient) -> None:
#     """Regex search requires regex field."""
#     resp = client.post("/api/artifact/byRegEx", json={})
#     assert resp.status_code == 400


# def test_artifact_by_regex_hits(client: FlaskClient) -> None:
#     """Regex search returns matching artifacts."""
#     _seed_artifacts(
#         [
#             {
#                 "id": 10,
#                 "name": "sentiment-classifier",
#                 "type": "model",
#                 "source_url": "http://x",
#             },
#             {"id": 11, "name": "other", "type": "model", "source_url": "http://x"},
#         ]
#     )
#     resp = client.post("/api/artifact/byRegEx", json={"regex": ".*sentiment.*"})
#     assert resp.status_code == 200
#     items = resp.get_json()
#     assert isinstance(items, list)
#     assert any(item["name"] == "sentiment-classifier" for item in items)


# def test_artifact_by_name_not_found(client: FlaskClient) -> None:
#     """Lookup by name returns 404 when not found."""
#     resp = client.get("/api/artifact/byName/nope")
#     assert resp.status_code == 404


# def test_artifact_by_name_hits(client: FlaskClient) -> None:
#     """Lookup by name returns matching artifacts."""
#     _seed_artifacts(
#         [{"id": 12, "name": "found", "type": "model", "source_url": "http://u"}]
#     )
#     resp = client.get("/api/artifact/byName/found")
#     assert resp.status_code == 200
#     items = resp.get_json()
#     assert isinstance(items, list)
#     assert items[0]["name"] == "found"
