"""Database helpers and connection management for the backend service."""

import os
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Mapping, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, RowMapping

load_dotenv()

APP_ENV = os.environ.get("APP_ENV", "dev")

database_url = os.environ.get("DATABASE_URL")

if not database_url:
    if APP_ENV in ("dev", "test"):
        if APP_ENV == "dev":
            database_url = "sqlite:///:memory:"
        else:
            database_url = "sqlite:///dev.db"
    else:
        # Fallback: build Postgres URL from parts (for prod)
        DB_USER = os.environ["DB_USER"]
        DB_PASSWORD = os.environ["DB_PASSWORD"]
        DB_HOST = os.environ["DB_HOST"]
        DB_PORT = os.environ.get("DB_PORT", "5432")
        DB_NAME = os.environ["DB_NAME"]
        database_url = (
            "postgresql+psycopg2://"
            f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

# Common args for database engine
engine_kwargs: dict[str, Any] = {"future": True}

if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update(
        pool_size=5,  # t3.micro: keep small
        max_overflow=5,
        pool_pre_ping=True,  # drop dead conns
        pool_recycle=1800,  # avoid stale conns (secs)
        execution_options={"stream_results": True},
    )

# One engine per Gunicorn worker (module-level)
engine: Engine = create_engine(database_url, **engine_kwargs)


def fetch_one(
    sql: str, params: Optional[Mapping[str, Any]] = None
) -> Optional[RowMapping]:
    """Run a query and return the first row as a mapping, or None if empty."""
    with engine.connect() as conn:
        res = conn.execute(text(sql), params or {})
        return res.mappings().first()


def fetch_all(
    sql: str, params: Optional[Mapping[str, Any]] = None
) -> list[Mapping[str, Any]]:
    """Execute a query and return every row as a list of dict-like mappings."""
    with engine.connect() as conn:
        res = conn.execute(text(sql), params or {})
        return [dict(row) for row in res.mappings().all()]


def execute(sql: str, params: Optional[Mapping[str, Any]] = None) -> int:
    """Execute a statement within a transaction and return affected row count."""
    with engine.begin() as conn:  # transaction
        res = conn.execute(text(sql), params or {})
        return res.rowcount


def execute_many(sql: str, seq_of_params: Iterable[Mapping[str, Any]]) -> int:
    """Run the same statement for each parameter set; returns total rows affected."""
    with engine.begin() as conn:
        res = conn.execute(text(sql), list(seq_of_params))
        return res.rowcount


@contextmanager
def transaction() -> Iterator[Connection]:
    """Manual transaction context for multi-statement ops."""
    with engine.begin() as conn:
        yield conn  # conn.execute(text(...), {...})


# transaction() example
# def create_model_and_ingestion(payload: dict) -> int:
#     with transaction() as conn:
#         # 1) Insert model
#         row = conn.execute(
#             text("""
#                 INSERT INTO models (model_name, version, status)
#                 VALUES (:name, :version, 'pending')
#                 RETURNING id;
#             """),
#             {"name": payload["name"], "version": payload.get("version")},
#         ).mappings().first()
#         model_id = row["id"]

#         # 2) Insert ingestion
#         conn.execute(
#             text("""
#                 INSERT INTO ingestions (model_id, source_url, status)
#                 VALUES (:model_id, :source_url, 'pending');
#             """),
#             {"model_id": model_id, "source_url": payload["source_url"]},
#         )

#         # 3) Update model status
#         conn.execute(
#             text("""
#                 UPDATE models
#                 SET status = 'active'
#                 WHERE id = :model_id;
#             """),
#             {"model_id": model_id},
#         )

#         # If we reach here with no exception, the whole block COMMITs.
#         # If any execute() above raises, everything in this block is ROLLED BACK.

#     return model_id
