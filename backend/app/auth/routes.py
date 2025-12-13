"""Authentication endpoints."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify, request

from app.auth.auth_services import (
    AuthenticationFailedError,
    AuthServiceError,
    InvalidRegistrationError,
    UsernameTakenError,
    authenticate_user,
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


@bp_auth.put("/authenticate")
def authenticate() -> tuple[Response, HTTPStatus]:
    """Authenticate a user and return a bearer token."""
    payload = request.get_json(force=True, silent=True) or {}
    user = payload.get("user") or {}
    secret = payload.get("secret") or {}
    username = user.get("name") if isinstance(user, dict) else None
    password = secret.get("password") if isinstance(secret, dict) else None
    if not isinstance(username, str) or not isinstance(password, str):
        return (
            jsonify({"error": "Invalid authentication payload."}),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        token = authenticate_user(username, password)
        return jsonify(token), HTTPStatus.OK
    except AuthenticationFailedError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.UNAUTHORIZED
    except AuthServiceError as exc:
        return (
            jsonify({"error": str(exc) or "Authentication failed."}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
