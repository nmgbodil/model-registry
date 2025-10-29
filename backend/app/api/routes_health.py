"""endpoint for health checks."""

# backend/app/api/routes_health.py
from __future__ import annotations

import os
import time
from typing import Final

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

bp: Final = Blueprint("health", __name__)
_START: Final[float] = time.monotonic()


@bp.get("/health")
def health() -> ResponseReturnValue:
    """Lightweight health probe used by graders and dashboards."""
    return jsonify(
        {
            "status": "ok",
            "app": os.environ.get("APP_NAME", "model-registry"),
            "build": os.environ.get("GIT_SHA", "dev"),
            "uptime_s": round(time.monotonic() - _START, 3),
        }
    )
