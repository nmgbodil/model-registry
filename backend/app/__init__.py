"""Flask app factory for the model registry."""

from __future__ import annotations

from flask import Flask  # jsonify
from flask_cors import CORS

from .api.routes_artifacts import bp_artifacts
from .config import get_settings
from .db import Base, engine


def create_app() -> Flask:
    """Create and configure the Flask application."""
    settings = get_settings()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

    # CORS for your frontend (adjust origin if needed)
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Health
    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    # Blueprints
    app.register_blueprint(bp_artifacts)

    # Ensure tables
    Base.metadata.create_all(bind=engine)

    return app
