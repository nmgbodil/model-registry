"""Flask app factory for the model registry."""

from __future__ import annotations

from flask import Blueprint, Flask
from flask_cors import CORS

from app.api.ratings import bp_ratings
from app.api.routes_health import bp
from app.config import get_settings
from app.db.core import engine
from app.db.models import Base


def create_app() -> Flask:
    """Create and configure the Flask application."""
    settings = get_settings()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

    # CORS: allow cross-origin calls; we use X-Authorization.
    CORS(
        app,
        # resources={r"/*": {"origins": "*"}},   # permissive for now
        origins="*",
        supports_credentials=False,  # required when origins="*"
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Authorization", "Authorization"],
        expose_headers=["offset", "x-next-offset"],
        max_age=600,
    )

    bp_master = Blueprint(
        "master", __name__, url_prefix="/api"
    )  # Blueprint for api prefix

    # Register new blueprints under bp_master
    bp_master.register_blueprint(bp_ratings)
    bp_master.register_blueprint(bp)

    @bp_master.get("/")
    def hello() -> str:
        """A simple route that returns a welcome message.

        Returns:
            str: Welcome message.
        """
        return "Hello World, welcome to Model Registry backend!"

    # Ensure DB tables exist in dev/test
    Base.metadata.create_all(bind=engine)

    app.register_blueprint(bp_master)

    return app
