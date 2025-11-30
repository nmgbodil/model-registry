# """Health endpoints aligned with the Phase 2 spec."""

# from __future__ import annotations

# import time
# from datetime import datetime, timezone
# from http import HTTPStatus
# from typing import Final

# from flask import Blueprint, jsonify, request
# from flask.typing import ResponseReturnValue

# bp: Final = Blueprint("health", __name__)

# # Track process start for uptime
# _START_TS: Final[float] = time.time()


# # ──────────────────────────────────────────────────────────────────────────────
# # GET /health  → Heartbeat check (BASELINE)
# #   Spec: returns HTTP 200 when the API is reachable. No response schema required.
# # ──────────────────────────────────────────────────────────────────────────────
# @bp.get("/health")
# def health() -> ResponseReturnValue:
#     """Health check endpoint."""
#     # Minimal body to keep clients happy, but spec only requires 200.
#     uptime_s = round(time.time() - _START_TS, 3)
#     return jsonify({"status": "ok", "uptime_s": uptime_s}), HTTPStatus.OK


# # ──────────────────────────────────────────────────────────────────────────────
# # GET /health/components  → Component health (NON-BASELINE)
# #   Query:
# #     - windowMinutes: int (5–1440), default 60
# #     - includeTimeline: bool (optional; accepted but ignored in this stub)
# #   Response: { components: [], generated_at: <ISO-8601 UTC>, window_minutes: <int> }
# # ──────────────────────────────────────────────────────────────────────────────
# @bp.get("/health/components")
# def health_components() -> ResponseReturnValue:
#     """Component health endpoint (stub)."""
#     # windowMinutes parsing with bounds per spec
#     try:
#         window_minutes = int(request.args.get("windowMinutes", "60"))
#     except ValueError:
#         window_minutes = 60
#     window_minutes = max(5, min(1440, window_minutes))

#     # includeTimeline is accepted but this stub does not populate timelines
#     _ = request.args.get("includeTimeline", "false").lower() in {"1", "true", "yes"}

#     payload = {
#         "components": [],  # you can populate this later with real component data
#         "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
#         "window_minutes": window_minutes,
#     }
#     return jsonify(payload), HTTPStatus.OK
