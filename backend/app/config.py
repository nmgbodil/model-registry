"""Runtime configuration for the model registry service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Final, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class JWTConfig:
    """JWT configuration values loaded from environment."""

    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=10)
    JWT_HEADER_NAME: str = "X-Authorization"
    JWT_HEADER_TYPE: str = "bearer"


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    # Server
    HOST: str
    PORT: int
    DEBUG: bool

    # Uploads
    UPLOAD_DIR: Path
    MAX_CONTENT_LENGTH: int  # bytes
    ALLOWED_EXTENSIONS: frozenset[str]

    # Database
    DATABASE_URL: str


def _bool(env_val: str | None, default: bool) -> bool:
    if env_val is None:
        return default
    return env_val.lower() in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    """Build Settings from environment with safe defaults."""
    base_dir: Final[Path] = Path(__file__).resolve().parents[1]
    upload_dir = Path(os.getenv("UPLOAD_DIR", base_dir / "var" / "artifacts"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        HOST=os.getenv("HOST", "127.0.0.1"),
        PORT=int(os.getenv("PORT", "8000")),
        DEBUG=_bool(os.getenv("DEBUG"), True),
        UPLOAD_DIR=upload_dir,
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024))),
        ALLOWED_EXTENSIONS=frozenset(
            (
                os.getenv(
                    "ALLOWED_EXTENSIONS", "pt,pth,onnx,pkl,zip,tar,txt,json"
                ).split(",")
            )
        ),
        DATABASE_URL=os.getenv(
            "DATABASE_URL",
            f"sqlite:///{(base_dir / 'var' / 'registry.sqlite').as_posix()}",
        ),
    )
