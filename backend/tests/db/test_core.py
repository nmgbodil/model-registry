"""Unit tests for database helper functions in app.db.core."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import StatementError

from app.db import core


class TestFetchOne:
    """Tests for the fetch_one helper."""

    def test_returns_first_row(self, test_table: Engine) -> None:
        """fetch_one should return the first matching row."""
        engine = test_table
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO test_metrics (name, score) VALUES (:name, :score)"),
                {"name": "alpha", "score": 10},
            )
            conn.execute(
                text("INSERT INTO test_metrics (name, score) VALUES (:name, :score)"),
                {"name": "beta", "score": 5},
            )

        row = core.fetch_one(
            "SELECT name, score FROM test_metrics ORDER BY id ASC LIMIT 1"
        )

        assert row is not None
        assert row["name"] == "alpha"
        assert row["score"] == 10

    def test_returns_none_when_no_rows(self, test_table: Engine) -> None:
        """fetch_one should return None when query has no rows."""
        row = core.fetch_one(
            "SELECT name, score FROM test_metrics WHERE name = :name",
            {"name": "missing"},
        )
        assert row is None


class TestFetchAll:
    """Tests for the fetch_all helper."""

    def test_returns_all_rows_as_dicts(self, test_table: Engine) -> None:
        """fetch_all should return ordered rows as dictionaries."""
        engine = test_table
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO test_metrics (name, score) VALUES (:name, :score)"),
                [{"name": "alpha", "score": 10}, {"name": "beta", "score": 5}],
            )

        rows = core.fetch_all(
            "SELECT name, score FROM test_metrics ORDER BY score DESC"
        )

        assert isinstance(rows, list)
        assert rows == [
            {"name": "alpha", "score": 10},
            {"name": "beta", "score": 5},
        ]

    def test_returns_empty_list_when_no_rows(self, test_table: Engine) -> None:
        """fetch_all should return an empty list for no matches."""
        rows = core.fetch_all(
            "SELECT name, score FROM test_metrics WHERE score > :score",
            {"score": 100},
        )
        assert rows == []


class TestExecute:
    """Tests for the execute helper."""

    def test_executes_statement_and_returns_rowcount(self, test_table: Engine) -> None:
        """Execute should return the affected row count."""
        rowcount = core.execute(
            "INSERT INTO test_metrics (name, score) VALUES (:name, :score)",
            {"name": "gamma", "score": 7},
        )

        assert rowcount == 1
        inserted = core.fetch_one(
            "SELECT name, score FROM test_metrics WHERE name = :name",
            {"name": "gamma"},
        )
        assert inserted is not None
        assert inserted["score"] == 7

    def test_raises_for_invalid_parameters(self, test_table: Engine) -> None:
        """Execute should surface SQL errors for missing params."""
        with pytest.raises(StatementError):
            core.execute(
                "INSERT INTO test_metrics (name, score) VALUES (:name, :score)",
                {"name": "delta"},
            )


class TestExecuteMany:
    """Tests for execute_many helper."""

    def test_executes_multiple_statements(self, test_table: Engine) -> None:
        """Execute many should insert every provided param set."""
        params = [
            {"name": "kappa", "score": 11},
            {"name": "lambda", "score": 4},
        ]
        rowcount = core.execute_many(
            "INSERT INTO test_metrics (name, score) VALUES (:name, :score)", params
        )

        assert rowcount == len(params)
        rows = core.fetch_all(
            "SELECT name, score FROM test_metrics WHERE name IN (:a, :b)",
            {"a": "kappa", "b": "lambda"},
        )
        assert len(rows) == 2

    def test_raises_when_no_param_sets_provided(self, test_table: Engine) -> None:
        """Execute many should safely no-op on empty parameter sets."""
        rowcount = core.execute_many(
            "INSERT INTO test_metrics (name, score) VALUES (:name, :score)", []
        )
        assert rowcount == 0
        rows = core.fetch_all("SELECT * FROM test_metrics")
        assert rows == []


class TestTransaction:
    """Tests for the transaction context manager."""

    def test_commits_changes_on_success(self, test_table: Engine) -> None:
        """Transaction context should commit when no errors occur."""
        with core.transaction() as conn:
            conn.execute(
                text("INSERT INTO test_metrics (name, score) VALUES (:name, :score)"),
                {"name": "omega", "score": 3},
            )

        rows = core.fetch_all("SELECT name, score FROM test_metrics")
        assert rows == [{"name": "omega", "score": 3}]

    def test_rolls_back_when_exception_occurs(self, test_table: Engine) -> None:
        """Transaction should roll back when body raises."""
        with pytest.raises(RuntimeError):
            with core.transaction() as conn:
                conn.execute(
                    text(
                        "INSERT INTO test_metrics (name, score) VALUES (:name, :score)"
                    ),
                    {"name": "zeta", "score": 2},
                )
                raise RuntimeError("boom")

        rows = core.fetch_all("SELECT name, score FROM test_metrics")
        assert rows == []
