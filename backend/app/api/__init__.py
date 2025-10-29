"""init file for API package."""

# backend/app/api/__init__.py
from __future__ import annotations

from .routes_health import bp as health_bp

__all__ = ["health_bp"]
