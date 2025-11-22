"""Shared fixtures and guards for database-level unit tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db import core


def pytest_sessionstart(session: pytest.Session) -> None:
    """Abort tests if DATABASE_URL is not SQLite to avoid touching prod data."""
    database_url = getattr(core, "database_url", "")
    if not str(database_url).startswith("sqlite"):
        pytest.exit(
            (
                "Database tests require a SQLite DATABASE_URL; "
                "aborting to protect prod data."
            ),
            returncode=1,
        )


@pytest.fixture()
def db_engine() -> Engine:
    """Expose the application-engine instance for tests."""
    return core.engine


@pytest.fixture()
def test_table(db_engine: Engine) -> Iterator[Engine]:
    """Create a simple table for exercising SQL helpers."""
    with db_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS test_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    score INTEGER NOT NULL
                )
                """
            )
        )
        conn.execute(text("DELETE FROM test_metrics"))

    yield db_engine

    with db_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS test_metrics"))
