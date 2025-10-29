"""Delete endpoint tests."""

from __future__ import annotations

import io
from typing import Any


def test_delete_artifact(client: Any) -> None:
    """Test deleting an artifact."""
    # Upload a small file
    res = client.post(
        "/artifacts",
        data={"file": (io.BytesIO(b"hello"), "hello.txt")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 201
    art_id = res.get_json()["id"]

    # Delete it
    res = client.delete(f"/artifacts/{art_id}")
    assert res.status_code == 204

    # Now 404s
    res = client.get(f"/artifacts/{art_id}")
    assert res.status_code == 404
