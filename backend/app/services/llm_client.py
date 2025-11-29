"""Lightweight client wrapper for invoking an LLM and parsing its responses."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletion


class LLMClient:
    """LLM client intended for registry analyses."""

    def __init__(self, model: str) -> None:
        """Initialize with the model name to use for completions."""
        self._model = model
        self._client = OpenAI()

    def invoke(self, prompt: str) -> str:
        """Send a prompt to the underlying LLM and return its raw string output."""
        response: ChatCompletion = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        # Each choice should contain a message; fall back to empty string if missing.
        content = response.choices[0].message.content
        return content or ""

    def invoke_json(self, prompt: str) -> Any:
        """Send a prompt and parse the response as JSON."""
        raw = self.invoke(prompt)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str) -> Any:
        """Parse raw model output into JSON; extendable for more robust parsing."""
        return json.loads(raw)
