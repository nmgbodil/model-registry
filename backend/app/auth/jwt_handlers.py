"""JWT error handlers registration."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Tuple

from flask import Response, jsonify
from flask_jwt_extended import JWTManager


def register_jwt_handlers(jwt: JWTManager) -> None:
    """Attach standard JWT error handlers to the given manager."""

    @jwt.expired_token_loader
    def expired_token_callback(
        jwt_header: dict[str, Any], jwt_payload: dict[str, Any]
    ) -> Tuple[Response, HTTPStatus]:
        return jsonify({"msg": "Authentication token expired"}), HTTPStatus.FORBIDDEN

    @jwt.invalid_token_loader
    def invalid_token_callback(error_message: str) -> Tuple[Response, HTTPStatus]:
        return jsonify({"msg": "Invalid authentication token"}), HTTPStatus.FORBIDDEN

    @jwt.unauthorized_loader
    def missing_token_callback(error_message: str) -> Tuple[Response, HTTPStatus]:
        return jsonify({"msg": "Missing authentication token"}), HTTPStatus.FORBIDDEN

    @jwt.revoked_token_loader
    def revoked_token_callback(
        jwt_header: dict[str, Any], jwt_payload: dict[str, Any]
    ) -> Tuple[Response, HTTPStatus]:
        return jsonify({"msg": "Token has been revoked"}), HTTPStatus.FORBIDDEN

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(
        jwt_header: dict[str, Any], jwt_payload: dict[str, Any]
    ) -> Tuple[Response, HTTPStatus]:
        return jsonify({"msg": "Fresh login required"}), HTTPStatus.FORBIDDEN
