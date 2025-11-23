"""SQLAlchemy models for the backend's persistence layer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Common SQLAlchemy declarative base for all models."""

    pass


class UserRole(PyEnum):
    """All roles a user can hold within the registry."""

    ADMIN = "admin"
    UPLOADER = "uploader"
    DOWNLOADER = "downloader"
    SEARCHER = "searcher"


class User(Base):
    """Application user with login credentials and a role."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True),
        default=UserRole.SEARCHER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="creator",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ArtifactStatus(PyEnum):
    """Lifecycle status for an artifact after rating/evaluation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Artifact(Base):
    """Versioned artifact metadata stored in the registry."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="model")
    version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manifest_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    s3_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # NEW: current status of the artifact in your registry
    status: Mapped[ArtifactStatus] = mapped_column(
        Enum(ArtifactStatus, name="artifact_status", native_enum=True),
        nullable=False,
        default=ArtifactStatus.PENDING,
    )

    dataset_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )

    code_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )

    parent_artifact_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    creator: Mapped[Optional[User]] = relationship(
        "User",
        back_populates="artifacts",
    )

    parent_artifact: Mapped[Optional["Artifact"]] = relationship(
        "Artifact",
        foreign_keys=[parent_artifact_id],
        remote_side=[id],
        back_populates="children",
    )

    dataset: Mapped[Optional["Artifact"]] = relationship(
        "Artifact", foreign_keys=[dataset_id], remote_side=[id]
    )

    code: Mapped[Optional["Artifact"]] = relationship(
        "Artifact", foreign_keys=[code_id], remote_side=[id]
    )

    children: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="parent_artifact",
        cascade="all, delete-orphan",
    )

    rating: Mapped["Rating"] = relationship(
        "Rating", back_populates="artifact", cascade="all, delete-orphan", uselist=False
    )


class Rating(Base):
    """Captured quality metrics for a specific artifact version."""

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_quality: Mapped[float] = mapped_column(Float, nullable=False)
    dataset_quality_latency: Mapped[float] = mapped_column(Float, nullable=False)
    dataset_and_code_score: Mapped[float] = mapped_column(Float, nullable=False)
    dataset_and_code_score_latency: Mapped[float] = mapped_column(Float, nullable=False)
    bus_factor: Mapped[float] = mapped_column(Float, nullable=False)
    bus_factor_latency: Mapped[float] = mapped_column(Float, nullable=False)
    license: Mapped[float] = mapped_column(Float, nullable=False)
    license_latency: Mapped[float] = mapped_column(Float, nullable=False)
    code_quality: Mapped[float] = mapped_column(Float, nullable=False)
    code_quality_latency: Mapped[float] = mapped_column(Float, nullable=False)
    size_score_raspberry_pi: Mapped[float] = mapped_column(Float, nullable=False)
    size_score_jetson_nano: Mapped[float] = mapped_column(Float, nullable=False)
    size_score_desktop_pc: Mapped[float] = mapped_column(Float, nullable=False)
    size_score_aws_server: Mapped[float] = mapped_column(Float, nullable=False)
    size_score_latency: Mapped[float] = mapped_column(Float, nullable=False)
    ramp_up_time: Mapped[float] = mapped_column(Float, nullable=False)
    ramp_up_time_latency: Mapped[float] = mapped_column(Float, nullable=False)
    performance_claims: Mapped[float] = mapped_column(Float, nullable=False)
    performance_claims_latency: Mapped[float] = mapped_column(Float, nullable=False)
    reproducibility: Mapped[float] = mapped_column(Float, nullable=False)
    reproducibility_latency: Mapped[float] = mapped_column(Float, nullable=False)
    reviewedness: Mapped[float] = mapped_column(Float, nullable=False)
    reviewedness_latency: Mapped[float] = mapped_column(Float, nullable=False)
    treescore: Mapped[float] = mapped_column(Float, nullable=False)
    treescore_latency: Mapped[float] = mapped_column(Float, nullable=False)
    net_score: Mapped[float] = mapped_column(Float, nullable=False)
    net_score_latency: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    artifact: Mapped[Artifact] = relationship(
        "Artifact",
        back_populates="rating",
    )
