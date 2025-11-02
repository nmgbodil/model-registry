"""Flask app factory for the model registry."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .api.routes_artifacts import bp_artifact, bp_artifacts
from .api.routes_health import bp
from .config import get_settings
from .db import Base, engine


def create_app() -> Flask:
    """Create and configure the Flask application."""
    settings = get_settings()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

    # CORS: allow cross-origin calls; we use X-Authorization.
    CORS(
        app,
        #resources={r"/*": {"origins": "*"}},   # permissive for now
        origins= "*",
        supports_credentials=False,            # required when origins="*"
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Authorization", "Authorization"],
        expose_headers=["offset", "x-next-offset"],
        max_age=600,
    )

    # Register blueprints
    app.register_blueprint(bp)            # /health
    app.register_blueprint(bp_artifacts)  # /artifacts...
    app.register_blueprint(bp_artifact)   # /artifact...

    # Ensure DB tables exist
    Base.metadata.create_all(bind=engine)

    return app
