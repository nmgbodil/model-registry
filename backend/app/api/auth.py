"""Authentication endpoints."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify, request

from app.services.auth import (
    AuthServiceError,
    InvalidRegistrationError,
    UsernameTakenError,
    register_user,
)

bp_auth = Blueprint("auth", __name__)


@bp_auth.post("/register")
def register() -> tuple[Response, HTTPStatus]:
    """Register a new user."""
    payload = request.get_json(force=True, silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return (
            jsonify({"error": "Invalid registration payload."}),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        resp = register_user(username, password)
        return jsonify(resp), HTTPStatus.CREATED
    except InvalidRegistrationError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except UsernameTakenError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.CONFLICT
    except AuthServiceError as exc:
        return (
            jsonify({"error": str(exc) or "Registration failed."}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
