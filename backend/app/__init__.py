"""This module initializes the Flask application for the backend."""

import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from app.db.session import init_local_db

load_dotenv()

APP_ENV = os.environ.get("APP_ENV")


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

    @app.get("/")
    def hello() -> str:
        """A simple route that returns a welcome message.

        Returns:
            str: Welcome message.
        """
        return "Hello World, welcome to Model Registry backend!"

    return app


if __name__ == "__main__":
    if APP_ENV in ("dev", "test"):
        init_local_db()
    app = create_app()
    app.run(debug=True, port=5001, host="0.0.0.0")
