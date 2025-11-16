"""init file for API package."""

from __future__ import annotations

from .routes_artifacts import bp_artifacts

# Expose blueprints at app.api.*
from .routes_health import bp as health_bp

__all__ = ["health_bp", "bp_artifacts"]
