"""Health endpoints aligned with the Phase 2 spec."""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import Final

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

bp: Final = Blueprint("health", __name__)

_START_TS: Final[float] = time.time()


@bp.get("/health")
def health() -> ResponseReturnValue:
    """Heartbeat check; returns HTTP 200 when reachable."""
    uptime_s = round(time.time() - _START_TS, 3)
    return jsonify({"status": "ok", "uptime_s": uptime_s}), HTTPStatus.OK
