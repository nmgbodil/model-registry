"""Artifacts routes are disabled; skip tests until re-enabled."""

from __future__ import annotations

import pytest

pytest.skip("artifact endpoints currently commented out", allow_module_level=True)
