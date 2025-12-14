"""Data access layer for users."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import User, UserRole


def create_user(
    session: Session,
    user_id: str,
    username: str,
    password_hash: str,
    role: UserRole = UserRole.searcher,
) -> User:
    """Create and persist a new user."""
    user = User(id=user_id, username=username, password_hash=password_hash, role=role)
    session.add(user)
    session.flush()
    return user


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Return a user by username, if one exists."""
    return session.query(User).filter(User.username == username).one_or_none()


def get_user_by_id(session: Session, user_id: str) -> Optional[User]:
    """Return a user by id, if one exists."""
    return session.get(User, user_id)
