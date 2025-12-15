"""Unit tests for API request limiter utilities."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple, cast

import pytest
from flask import Flask
from redis import Redis

from app.auth.api_request_limiter import (
    MAX_CALLS,
    TOKEN_TTL_SECONDS,
    APIRequestLimiter,
    enforce_api_limits,
)


class FakeRedis:
    """Minimal Redis-like store for limiter tests."""

    def __init__(self) -> None:
        self.store: Dict[str, int] = {}
        self.ttl: Dict[str, int] = {}

    def exists(self, key: str) -> bool:
        """Return True if key exists."""
        return key in self.store

    def setex(self, key: str, ttl: int, value: int) -> None:
        """Set a value with TTL."""
        self.store[key] = value
        self.ttl[key] = ttl

    def incr(self, key: str) -> int:
        """Increment a key and return the new value."""
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def get(self, key: str) -> Optional[int]:
        """Return stored int or None."""
        return self.store.get(key)


def test_increment_and_key_generation() -> None:
    """Increment should set TTL and count up."""
    redis = FakeRedis()
    limiter = APIRequestLimiter(cast(Redis, redis))

    first = limiter.increment("tid123")
    second = limiter.increment("tid123")

    assert first == 1
    assert second == 2
    assert redis.ttl["api_calls:tid123"] == TOKEN_TTL_SECONDS


def test_limit_check_helpers() -> None:
    """Helper methods should reflect store values."""
    redis = FakeRedis()
    limiter = APIRequestLimiter(cast(Redis, redis))

    assert limiter.get_count("missing") == 0

    redis.store["api_calls:tid"] = MAX_CALLS + 1
    assert limiter.is_limit_exceeded("tid") is True


def test_enforce_api_limits_allows_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should allow when under limit and increment counts."""
    app = Flask(__name__)
    redis = FakeRedis()
    limiter = APIRequestLimiter(cast(Redis, redis))
    app.config["API_REQUEST_LIMITER"] = limiter

    calls: list[str] = []

    @enforce_api_limits
    def endpoint() -> str:
        calls.append("ran")
        return "ok"

    with app.test_request_context():
        monkeypatch.setattr(
            "app.auth.api_request_limiter.get_jwt", lambda: {"tid": "token1"}
        )
        result = endpoint()

    assert result == "ok"
    assert calls == ["ran"]
    assert redis.store["api_calls:token1"] == 1


def test_enforce_api_limits_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should block missing token id."""
    app = Flask(__name__)
    app.config["API_REQUEST_LIMITER"] = APIRequestLimiter(cast(Redis, FakeRedis()))

    @enforce_api_limits
    def endpoint() -> str:
        return "ok"

    with app.test_request_context():
        monkeypatch.setattr("app.auth.api_request_limiter.get_jwt", lambda: {})
        resp_tuple: Tuple[Any, HTTPStatus] = cast(Tuple[Any, HTTPStatus], endpoint())
        resp, status = resp_tuple

    assert status == HTTPStatus.FORBIDDEN
    assert resp.get_json()["msg"] == "Invalid authentication token"


def test_enforce_api_limits_exceeds_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should forbid when limit exceeded."""
    app = Flask(__name__)
    redis = FakeRedis()
    redis.store["api_calls:tokenX"] = MAX_CALLS
    app.config["API_REQUEST_LIMITER"] = APIRequestLimiter(cast(Redis, redis))

    @enforce_api_limits
    def endpoint() -> str:
        return "ok"

    with app.test_request_context():
        monkeypatch.setattr(
            "app.auth.api_request_limiter.get_jwt", lambda: {"tid": "tokenX"}
        )
        resp_tuple: Tuple[Any, HTTPStatus] = cast(Tuple[Any, HTTPStatus], endpoint())
        resp, status = resp_tuple

    assert status == HTTPStatus.FORBIDDEN
    assert resp.get_json()["msg"] == "API call limit exceeded. Session ended"


def test_enforce_api_limits_no_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decorator should no-op when JWT not configured."""
    app = Flask(__name__)
    app.config["API_REQUEST_LIMITER"] = APIRequestLimiter(cast(Redis, FakeRedis()))

    @enforce_api_limits
    def endpoint() -> str:
        return "ok"

    def raise_runtime() -> dict[str, str]:
        raise RuntimeError("no jwt")

    with app.test_request_context():
        monkeypatch.setattr("app.auth.api_request_limiter.get_jwt", raise_runtime)
        result = endpoint()

    assert result == "ok"
