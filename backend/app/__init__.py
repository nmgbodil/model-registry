"""Application factory for the model-registry API."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)

    # Blueprints
    from .api.routes_health import bp as health_bp  # isort: skip

    app.register_blueprint(health_bp)

    @app.get("/")
    def index() -> dict[str, str]:
        """Root smoke-check endpoint."""
        return {"ok": "true"}

    return app
