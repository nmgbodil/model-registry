"""Tests for the LLMClient wrapper."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from openai import OpenAI

from app.services.llm_client import LLMClient


class FakeChoice:
    """Choice stub mirroring OpenAI message structure."""

    def __init__(self, content: str) -> None:
        """Simple choice stub."""
        self.message = type("msg", (), {"content": content})


class FakeCompletions:
    """Stub completions container exposing create()."""

    def __init__(self, content: str) -> None:
        """Stub completions.create response."""
        self._content = content

    def create(self, model: str, messages: Any) -> Any:
        """Return a fake response object."""
        return type("resp", (), {"choices": [FakeChoice(self._content)]})


class FakeChat:
    """Stub chat namespace containing completions."""

    def __init__(self, content: str) -> None:
        """Stub chat container."""
        self.completions = FakeCompletions(content)


class FakeOpenAI:
    """Stub top-level OpenAI client."""

    def __init__(self, content: str) -> None:
        """Stub top-level OpenAI client."""
        self.chat = FakeChat(content)


def _make_client(content: Any) -> LLMClient:
    """Build an LLMClient without hitting real OpenAI."""
    client = object.__new__(LLMClient)
    client._model = "gpt-test"
    client._client = cast(OpenAI, FakeOpenAI(content))
    return client


def test_invoke_returns_string(monkeypatch: Any) -> None:
    """invoke should return the string content when present."""  # noqa: D403
    client = _make_client("hello")

    result = client.invoke("prompt")

    assert result == "hello"


def test_invoke_handles_missing_content(monkeypatch: Any) -> None:
    """invoke should fall back to empty string when content missing."""  # noqa: D403
    client = _make_client(content=None)

    result = client.invoke("prompt")

    assert result == ""


def test_invoke_json_parses_json(monkeypatch: Any) -> None:
    """invoke_json should parse valid JSON payloads."""
    payload = {"foo": "bar"}
    client = _make_client(json.dumps(payload))

    result = client.invoke_json("prompt")

    assert result == payload


def test_parse_json_raises_on_invalid() -> None:
    """_parse_json should raise on invalid JSON input."""
    with pytest.raises(json.JSONDecodeError):
        LLMClient._parse_json("not json")
