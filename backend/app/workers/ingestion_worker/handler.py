"""Lambda worker entrypoint for artifact ingestion."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.workers.ingestion_worker.ingestion_logic import ingest_artifact

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entrypoint.

    Expected event shape:
    {
        "artifact_id": 123
    }
    """
    artifact_id_raw = event.get("artifact_id")
    if artifact_id_raw is None:
        logger.warning("Received event without artifact_id: %s", event)
        return {"error": "artifact_id is required"}

    try:
        artifact_id = int(artifact_id_raw)
    except (TypeError, ValueError):
        logger.warning("Invalid artifact_id value: %r", artifact_id_raw)
        return {
            "artifact_id": artifact_id_raw,
            "error": "artifact_id must be an integer",
        }

    try:
        logger.info("Starting ingestion for artifact_id=%s", artifact_id)
        final_status = ingest_artifact(artifact_id)
        logger.info(
            "Finished ingestion for artifact_id=%s with status=%s",
            artifact_id,
            final_status,
        )

        return {"artifact_id": artifact_id, "status": final_status.value}

    except ValueError as exc:
        logger.warning(
            "Ingestion failed for artifact_id=%s with ValueError: %s",
            artifact_id,
            exc,
        )
        return {
            "artifact_id": artifact_id,
            "error": str(exc),
        }

    except Exception as exc:
        logger.exception(
            "Unexpected error ingesting artifact_id=%s: %s", artifact_id, exc
        )
        raise
