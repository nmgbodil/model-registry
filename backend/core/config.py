"""init file for core config package."""

# backend/app/core/config.py
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuration settings for the application."""

    app_name: str = os.getenv("APP_NAME", "model-registry")
    git_sha: str = os.getenv("GIT_SHA", "dev")
    database_url: str = os.getenv("DATABASE_URL", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-2")
    s3_bucket: str = os.getenv("S3_BUCKET", "")


settings = Settings()
