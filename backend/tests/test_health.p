# """add test for health endpoint."""

# # backend/tests/test_health.py
# from __future__ import annotations

# import json

# from app import create_app


# def test_health_ok() -> None:
#     """Test the /health endpoint returns expected data."""
#     app = create_app()
#     client = app.test_client()

#     response = client.get("/health")
#     assert response.status_code == 200

#     body = json.loads(response.data.decode("utf-8"))
#     assert body["status"] == "ok"
#     assert "uptime_s" in body
