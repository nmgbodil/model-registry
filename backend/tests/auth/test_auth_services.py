"""Tests for authentication service helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import bcrypt
import pytest

from app.auth import auth_services
from app.db.models import UserRole
from tests.utils import fake_session_cm

TEST_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class FakeSession:
    """Lightweight stand-in for SQLAlchemy Session."""

    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        """Record that commit was called."""
        self.committed = True


@dataclass
class FakeUser:
    """Simple user holder for authentication tests."""

    id: str
    username: str
    password_hash: str
    role: UserRole = UserRole.searcher


def test_register_user_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create user when username free and payload valid."""
    fake_session = FakeSession()
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        auth_services, "orm_session", lambda: fake_session_cm(fake_session)
    )
    monkeypatch.setattr(auth_services, "get_user_by_username", lambda s, u: None)

    def fake_create_user(
        session: FakeSession,
        user_id: str,
        username: str,
        password_hash: str,
        role: UserRole,
    ) -> None:
        captured["user_id"] = user_id
        captured["username"] = username
        captured["password_hash"] = password_hash
        captured["role"] = role.value

    monkeypatch.setattr(auth_services, "create_user", fake_create_user)
    monkeypatch.setattr(uuid, "uuid4", lambda: TEST_UUID)

    resp = auth_services.register_user("newuser", "ValidP@ssw0rd")

    assert resp["id"] == str(TEST_UUID)
    assert resp["username"] == "newuser"
    assert fake_session.committed is True
    assert captured["username"] == "newuser"
    assert captured["role"] == UserRole.searcher.value
    assert captured["password_hash"] != "ValidP@ssw0rd"


def test_register_user_rejects_duplicate_username(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject registration if username already taken."""
    fake_session = FakeSession()
    monkeypatch.setattr(
        auth_services, "orm_session", lambda: fake_session_cm(fake_session)
    )
    monkeypatch.setattr(auth_services, "get_user_by_username", lambda s, u: object())

    with pytest.raises(auth_services.UsernameTakenError):
        auth_services.register_user("existing", "ValidP@ssw0rd!")


@pytest.mark.parametrize(
    "username,password",
    [
        ("", "ValidP@ssw0rd!"),
        ("user", "short"),
        ("user", "NoSpecial123"),
        ("user", "nospecialor123"),
    ],
)
def test_register_user_validation_errors(
    username: str, password: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate bad registration payloads."""
    fake_session = FakeSession()
    monkeypatch.setattr(
        auth_services, "orm_session", lambda: fake_session_cm(fake_session)
    )
    monkeypatch.setattr(auth_services, "get_user_by_username", lambda s, u: None)

    with pytest.raises(auth_services.InvalidRegistrationError):
        auth_services.register_user(username, password)


def test_authenticate_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return bearer token for valid username/password."""
    fake_session = FakeSession()
    hashed = bcrypt.hashpw("GoodP@ss1".encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    user = FakeUser(id="abc", username="user", password_hash=hashed)

    monkeypatch.setattr(
        auth_services, "orm_session", lambda: fake_session_cm(fake_session)
    )
    monkeypatch.setattr(auth_services, "get_user_by_username", lambda s, u: user)
    monkeypatch.setattr(
        auth_services,
        "create_access_token",
        lambda identity, additional_claims: "token123",
    )
    monkeypatch.setattr(uuid, "uuid4", lambda: TEST_UUID)

    token = auth_services.authenticate_user("user", "GoodP@ss1")

    assert token == "bearer token123"


def test_authenticate_user_missing_or_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise on missing or invalid auth payloads."""
    fake_session = FakeSession()
    monkeypatch.setattr(
        auth_services, "orm_session", lambda: fake_session_cm(fake_session)
    )
    monkeypatch.setattr(auth_services, "get_user_by_username", lambda s, u: None)

    with pytest.raises(auth_services.AuthenticationFailedError):
        auth_services.authenticate_user("user", "badpass")

    with pytest.raises(auth_services.AuthenticationFailedError):
        auth_services.authenticate_user("", "badpass")


def test_authenticate_user_wrong_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise when password hash does not match."""
    fake_session = FakeSession()
    hashed = bcrypt.hashpw("Correct1!".encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    user = FakeUser(id="abc", username="user", password_hash=hashed)

    monkeypatch.setattr(
        auth_services, "orm_session", lambda: fake_session_cm(fake_session)
    )
    monkeypatch.setattr(auth_services, "get_user_by_username", lambda s, u: user)

    with pytest.raises(auth_services.AuthenticationFailedError):
        auth_services.authenticate_user("user", "WrongP@ss1")
