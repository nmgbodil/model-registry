"""This module initializes the Flask application for the backend."""

from flask import Blueprint, Flask
from flask_cors import CORS

from app.api.ratings import bp_ratings


def create_app() -> Flask:
    """Create and configure the Flask application.

    Args:
        test_config (dict, optional): Configuration dictionary for testing.
            Defaults to None.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)

    bp_master = Blueprint(
        "master", __name__, url_prefix="/api"
    )  # Blueprint for api prefix

    # Register new blueprints under bp_master
    bp_master.register_blueprint(bp_ratings)

    @bp_master.get("/")
    def hello() -> str:
        """A simple route that returns a welcome message.

        Returns:
            str: Welcome message.
        """
        return "Hello World, welcome to Model Registry backend!"

    app.register_blueprint(bp_master)

    return app
