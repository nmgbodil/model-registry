"""Flask app factory for the model registry."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .api.routes_artifacts import bp_artifacts
from .api.routes_health import bp
from .config import get_settings
from .db import Base, engine  # import the global Engine instance


def create_app() -> Flask:
    """Create and configure the Flask application."""
    settings = get_settings()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

    # Enable CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(bp)
    app.register_blueprint(bp_artifacts)

    # Ensure DB tables exist (bind to the imported engine; DO NOT reassign or call it)
    Base.metadata.create_all(bind=engine)

    return app
