"""Unit tests for session helpers under app.db.session."""

from __future__ import annotations

from unittest import mock

from pytest import MonkeyPatch, raises
from sqlalchemy.engine import Engine

from app.db import session
from app.db.models import Base as ModelBase


class TestOrmSession:
    """Tests for orm_session context manager."""

    def test_yields_session_and_closes_cleanly(self, monkeypatch: MonkeyPatch) -> None:
        """Context should yield the session and close it without rollback."""
        fake_session = mock.MagicMock()
        fake_factory = mock.MagicMock(return_value=fake_session)
        monkeypatch.setattr(session, "SessionLocal", fake_factory)

        with session.orm_session() as yielded:
            assert yielded is fake_session
            fake_session.rollback.assert_not_called()

        fake_factory.assert_called_once()
        fake_session.close.assert_called_once()

    def test_rolls_back_when_body_raises(self, monkeypatch: MonkeyPatch) -> None:
        """Context should rollback and close the session on exception."""
        fake_session = mock.MagicMock()
        fake_factory = mock.MagicMock(return_value=fake_session)
        monkeypatch.setattr(session, "SessionLocal", fake_factory)

        with raises(RuntimeError):
            with session.orm_session():
                raise RuntimeError("boom")

        fake_session.rollback.assert_called_once()
        fake_session.close.assert_called_once()


class TestInitLocalDb:
    """Tests for init_local_db helper."""

    def test_creates_tables_with_bound_engine(
        self, monkeypatch: MonkeyPatch, db_engine: Engine
    ) -> None:
        """init_local_db should call create_all with the configured engine."""
        mocked_create_all = mock.MagicMock()
        monkeypatch.setattr(
            ModelBase.metadata, "create_all", mocked_create_all, raising=False
        )
        monkeypatch.setattr(session, "engine", db_engine, raising=False)

        session.init_local_db()

        mocked_create_all.assert_called_once_with(bind=db_engine)

    def test_bubbles_up_errors_from_create_all(
        self, monkeypatch: MonkeyPatch, db_engine: Engine
    ) -> None:
        """init_local_db should surface errors from metadata creation."""
        mocked_create_all = mock.MagicMock(side_effect=RuntimeError("fail"))
        monkeypatch.setattr(
            ModelBase.metadata, "create_all", mocked_create_all, raising=False
        )
        monkeypatch.setattr(session, "engine", db_engine, raising=False)

        with raises(RuntimeError):
            session.init_local_db()

        mocked_create_all.assert_called_once_with(bind=db_engine)
