"""This module contains tests for the Flask application."""

import pytest
from flask import Flask, testing

# If your package is "app" (backend/app/__init__.py), this import works:
from app import create_app


@pytest.fixture()
def app() -> Flask:
    """Fixture to create and configure the Flask application instance.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture()
def client(app: Flask) -> testing.FlaskClient:
    """Fixture to create a test client for the Flask application.

    Args:
        app (Flask): The Flask application instance.

    Returns:
        FlaskClient: The test client for the Flask application.
    """
    return app.test_client()


def test_create_app_returns_flask_app(app: Flask) -> None:
    """Test to verify that the create_app function returns a Flask application instance.

    Args:
        app (Flask): The Flask application instance.
    """
    assert isinstance(app, Flask)


def test_root_route_returns_hello_message(client: testing.FlaskClient) -> None:
    """Test to verify that the root route returns the expected welcome message.

    Args:
        client (FlaskClient): The test client for the Flask application.
    """
    resp = client.get("/api/")
    assert resp.status_code == 200
    assert (
        resp.get_data(as_text=True) == "Hello World, welcome to Model Registry backend!"
    )


def test_cors_header_present_on_simple_get(client: testing.FlaskClient) -> None:
    """Test to verify that the CORS header is present on a simple GET request.

    Args:
        client (FlaskClient): The test client for the Flask application.
    """
    resp = client.get("/api/")
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"
