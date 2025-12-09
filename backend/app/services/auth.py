"""Business logic for user registration."""

from __future__ import annotations

import re
import uuid

from app.dals.users import create_user, get_user_by_username
from app.db.models import UserRole
from app.db.session import orm_session


class AuthServiceError(Exception):
    """Base exception for auth service errors."""


class InvalidRegistrationError(AuthServiceError):
    """Raised when registration payload is invalid."""


class UsernameTakenError(AuthServiceError):
    """Raised when username already exists."""


def _validate_password(pw: str) -> None:
    if len(pw) < 8:
        raise InvalidRegistrationError("Password must be at least 8 characters long.")
    if not re.search(r"[0-9]", pw):
        raise InvalidRegistrationError("Password must include at least one number.")
    if not re.search(r"[^A-Za-z0-9]", pw):
        raise InvalidRegistrationError(
            "Password must include at least one special character."
        )


def register_user(username: str, password: str) -> dict[str, str]:
    """Register a new user with hashed password."""
    try:
        import bcrypt
    except Exception as exc:
        raise AuthServiceError("bcrypt is required for registration.") from exc

    if not username.strip():
        raise InvalidRegistrationError("Username is required.")
    _validate_password(password)

    with orm_session() as session:
        if get_user_by_username(session, username):
            raise UsernameTakenError("Username is already taken.")

        # generate UUID for id
        user_id = str(uuid.uuid4())
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        create_user(
            session,
            user_id=user_id,
            username=username,
            password_hash=pw_hash.decode("utf-8"),
            role=UserRole.admin,
        )
        session.commit()
        return {"id": user_id, "username": username}
