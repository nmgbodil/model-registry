"""Data access helpers for artifact audit logging."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import ArtifactAuditLog

# Allowed audit actions (application-level safety)
ALLOWED_AUDIT_ACTIONS = {
    "CREATE",
    "UPDATE_NAME",
    "UPDATE_CONTENT",
    "DOWNLOAD",
    "DELETE",
    "AUDIT",
}


def log_artifact_event(
    *,
    session: Session,
    artifact_id: int,
    artifact_type: str,
    action: str,
    user_id: Optional[str],
    previous_checksum: Optional[str] = None,
    new_checksum: Optional[str] = None,
    request_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Append a single audit event for an artifact.

    This function is intentionally append-only:
    - No updates
    - No deletes
    - One row per call
    """
    if action not in ALLOWED_AUDIT_ACTIONS:
        raise ValueError(f"Invalid audit action: {action}")

    audit_row = ArtifactAuditLog(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        action=action,
        user_id=user_id,
        previous_checksum=previous_checksum,
        new_checksum=new_checksum,
        request_ip=request_ip,
        user_agent=user_agent,
    )

    session.add(audit_row)


def get_artifact_audit_log(
    *,
    session: Session,
    artifact_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[ArtifactAuditLog]:
    """Fetch audit history for a single artifact.

    Results are ordered newest-first.
    """
    return (
        session.query(ArtifactAuditLog)
        .filter(ArtifactAuditLog.artifact_id == artifact_id)
        .order_by(ArtifactAuditLog.occurred_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
