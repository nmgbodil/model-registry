"""Flask app factory for the model registry."""

from __future__ import annotations

import os
from http import HTTPStatus

from dotenv import load_dotenv
from flask import Blueprint, Flask, Response, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.api.artifact import bp_artifact as bp_artifact_cost
from app.api.auth import bp_auth
from app.api.lineage import bp_lineage
from app.api.ratings import bp_ratings
from app.api.routes_artifacts import bp_artifact, bp_artifacts
from app.api.routes_health import bp
from app.api.routes_reset import bp_reset
from app.config import JWTConfig, get_settings


def create_app() -> Flask:
    """Create and configure the Flask application."""
    load_dotenv()
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

    # JWT configuration
    jwt_cfg = JWTConfig()
    app.config.update(jwt_cfg.__dict__)
    jwt = JWTManager(app)  # noqa: F841

    bp_master = Blueprint(
        "master", __name__, url_prefix="/api"
    )  # Blueprint for api prefix

    # Register new blueprints under bp_master
    bp_master.register_blueprint(bp_ratings)
    bp_master.register_blueprint(bp)
    bp_master.register_blueprint(bp_artifacts)
    bp_master.register_blueprint(bp_artifact)
    bp_master.register_blueprint(bp_artifact_cost)
    bp_master.register_blueprint(bp_lineage)
    bp_master.register_blueprint(bp_auth)
    bp_master.register_blueprint(bp_reset)

    @bp_master.get("/")
    def hello() -> str:
        """A simple route that returns a welcome message.

        Returns:
            str: Welcome message.
        """
        return "Hello World, welcome to Model Registry backend!"

    @bp_master.get("/tracks")
    def planned_tracks() -> tuple[Response, HTTPStatus]:
        """Return the list of planned tracks for implementation."""
        try:
            return (
                jsonify(
                    {
                        "plannedTracks": [
                            "Access control track",
                        ]
                    }
                ),
                HTTPStatus.OK,
            )
        except Exception:
            return (
                jsonify(
                    {
                        "error": (
                            "The system encountered an error while retrieving the "
                            "student's track information."
                        )
                    }
                ),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    # Ensure DB tables exist in dev/test
    if os.getenv("APP_ENV", "dev") in ("dev", "test"):
        try:
            from app.db.session import init_local_db

            init_local_db()
        except Exception:
            pass

    app.register_blueprint(bp_master)

    return app
