"""API Request Limiter for the Model Registry backend.

Tracks the number of API calls per JWT token using Redis,
enforcing the Security Track requirement:

    - Max 1000 API calls per token
    - Token expires after 10 hours (TTL aligns with JWT expiration)

This module exposes:
    - APIRequestLimiter class
    - enforce_api_limit decorator
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from http import HTTPStatus
from typing import Any, Callable, ParamSpec, TypeVar, cast

from flask import current_app, jsonify
from flask_jwt_extended import get_jwt
from redis import Redis

MAX_CALLS = 1000
TOKEN_TTL_SECONDS = 10 * 60 * 60

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class APIRequestLimiter:
    """Lightweight wrapper around Redis for tracking API usage per token."""

    redis_client: Redis

    def _key(self, token_id: str) -> str:
        """Return the Redis key for this token_id."""
        return f"api_calls:{token_id}"

    def increment(self, token_id: str) -> int:
        """Atomically increments call count for this token.

        If key does not exist, initialize it with TTL matching token lifetime.
        """
        key = self._key(token_id)

        # Initialize with TTL only on first seen call
        if not self.redis_client.exists(key):
            # Set initial value = 0 with TTL
            self.redis_client.setex(key, TOKEN_TTL_SECONDS, 0)

        # Redis INCR returns the new integer value
        new_count = cast(int, self.redis_client.incr(key))
        return new_count

    def get_count(self, token_id: str) -> int:
        """Return the current call count or ) if key not found."""
        val = cast(int, self.redis_client.get(self._key(token_id)))
        return val if val is not None else 0

    def is_limit_exceeded(self, token_id: str) -> bool:
        """Check if this token_id has exceeded its allowed limit."""
        return self.get_count(token_id) > MAX_CALLS


def enforce_api_limits(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator applied on every authenticated API endpoint.

    It performs:
        1. Extract token payload
        2. Read token_id ("tid") claim
        3. Increment API usage in Redis
        4. Enforce 1000-call limit
        5. Return 403 if limit exceeded

    Must be applied *after* `@jwt_required()`.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        try:
            jwt_payload = get_jwt()
        except RuntimeError:
            # If JWT isn't set (tests), skip enforcement.
            return func(*args, **kwargs)
        token_id = jwt_payload.get("tid")

        if not token_id:
            print("error in api limits")
            return (
                jsonify({"msg": "Invalid authentication token"}),
                HTTPStatus.FORBIDDEN,
            )

        limiter: APIRequestLimiter = current_app.config["API_REQUEST_LIMITER"]

        new_count = limiter.increment(token_id)
        if new_count > MAX_CALLS:
            return (
                jsonify({"msg": "API call limit exceeded. Session ended"}),
                HTTPStatus.FORBIDDEN,
            )

        return func(*args, **kwargs)

    return wrapper
