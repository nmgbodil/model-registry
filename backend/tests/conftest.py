"""tests/conftest.py Fixtures for tests."""

# tests/conftest.py
from __future__ import annotations

import importlib
import pathlib
from typing import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient


@pytest.fixture()
def client(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[FlaskClient]:
    """Flask test client with per-test DB/uploads and patched settings."""
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    from app import create_app

    app: Flask = create_app()

    from app.api import routes_artifacts as ra

    importlib.reload(ra)

    monkeypatch.setattr(ra.settings, "UPLOAD_DIR", upload_dir, raising=True)
    monkeypatch.setattr(
        ra.settings,
        "ALLOWED_EXTENSIONS",
        {"txt", "json", "md", "yaml", "yml", "pdf"},
        raising=True,
    )

    from app.db import get_session
    from app.models import Base

    with get_session() as s:
        bind = s.get_bind()
        assert bind is not None
        Base.metadata.create_all(bind=bind)

    with app.test_client() as c:
        yield c
