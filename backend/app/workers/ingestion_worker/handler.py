"""Lambda worker entrypoint for ingesting artifacts and persisting results."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.dals.ratings import (
    create_rating,
    get_artifact_by_id,
    update_artifact_attributes,
)
from app.db.models import Artifact, ArtifactStatus
from app.db.session import orm_session
from app.schemas.model_rating import ModelRating
from app.services.artifacts.code_fetcher import open_codebase
from app.services.artifacts.dataset_fetcher import HFDatasetFetcher
from app.services.artifacts.model_fetcher import HFModelFetcher
from app.services.storage import upload_artifact
from app.utils import _is_hf_url, build_model_rating_from_record
from app.workers.ingestion_worker.src.main import calculate_scores
from app.workers.ingestion_worker.src.url import Url, UrlSet

logger = logging.getLogger()
logger.setLevel(logging.INFO)


DEFAULT_RATING_VALUES: Dict[str, Any] = {
    "category": "model",
    "reproducibility": 0.0,
    "reproducibility_latency": 0.0,
    "reviewedness": 0.0,
    "reviewedness_latency": 0.0,
    "tree_score": 0.0,
    "tree_score_latency": 0.0,
}

DEFAULT_SIZE_SCORES: Dict[str, float] = {
    "raspberry_pi": 0.0,
    "jetson_nano": 0.0,
    "desktop_pc": 0.0,
    "aws_server": 0.0,
}


def normalize_rating_payload(raw_rating: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure missing metrics from the worker are filled with defaults."""
    normalized = raw_rating.copy()

    for key, default in DEFAULT_RATING_VALUES.items():
        normalized.setdefault(key, default)

    size_score = normalized.get("size_score") or {}
    normalized["size_score"] = {**DEFAULT_SIZE_SCORES, **size_score}

    return normalized


def _build_urlset_for_artifact(artifact_link: str) -> UrlSet:
    """Create a UrlSet with only the model URL populated."""
    model_url = Url(artifact_link)
    # TODO: Populate dataset and code URLs when artifact relationships are present.
    return UrlSet(None, None, model_url)


def _persist_rating(
    session: Session, artifact: Artifact, raw_rating: Dict[str, Any]
) -> ModelRating:
    """Normalize, save, and return the rating."""
    normalized = normalize_rating_payload(raw_rating)
    # TODO: Add logic in rate_worker to compute reproducibility, reviewedness,
    # and tree_score metrics.
    rating_record = create_rating(session, artifact.id, normalized)
    return build_model_rating_from_record(artifact, rating_record)


def _is_ingestible(rating: Dict[str, Any], threshold: float = 0.5) -> bool:
    """Check that every non-latency metric meets the minimum threshold."""
    for key, value in rating.items():
        if key.endswith("_latency") or key in {"name", "category", "error"}:
            continue

        if key == "size_score":
            score_dict = value or {}
            if not isinstance(score_dict, dict):
                return False
            if any(score < threshold for score in score_dict.values()):
                return False
            continue

        if not isinstance(value, (int, float)):
            return False

        if value < threshold:
            return False

    return True


def _fetch_artifact_archive(artifact: Artifact) -> str:
    """Fetch artifact contents based on type and return a zip file path."""
    tmp_dir = tempfile.mkdtemp(prefix="artifact_fetch_")
    archive_base = os.path.join(tmp_dir, f"{artifact.name}-full")
    if not artifact.source_url:
        raise ValueError("Artifact source_url is required to fetch contents.")

    if artifact.type == "model":
        is_hf, kind, repo_id = _is_hf_url(artifact.source_url)
        if is_hf and kind == "model" and repo_id:
            with HFModelFetcher(repo_id) as repo:
                return shutil.make_archive(archive_base, "zip", root_dir=repo.root)

    if artifact.type == "dataset":
        is_hf, kind, repo_id = _is_hf_url(artifact.source_url)
        if is_hf and kind == "dataset" and repo_id:
            with HFDatasetFetcher(repo_id) as repo:
                return shutil.make_archive(archive_base, "zip", root_dir=repo.root)

    # treat anything else as code
    with open_codebase(artifact.source_url) as repo:
        return shutil.make_archive(archive_base, "zip", root_dir=repo.root)


def ingest_artifact(artifact_id: int) -> ArtifactStatus:
    """Ingest a model artifact by scoring and updating its status.

    The artifact must be in PENDING status. If all non-latency metrics are
    at least 0.5, the artifact is marked as ACCEPTED, uploaded to S3, and a
    rating row is created. Otherwise, the artifact is marked as REJECTED.
    """
    with orm_session() as session:
        artifact = get_artifact_by_id(session, artifact_id)
        if artifact is None:
            raise ValueError("Artifact not found.")
        if artifact.status != ArtifactStatus.pending:
            raise ValueError("Artifact is not pending and cannot be ingested.")
        if not artifact.source_url:
            raise ValueError("Artifact source_url is required to fetch contents.")

        urlset = _build_urlset_for_artifact(artifact.source_url)
        rating_payload = calculate_scores(urlset)

        if _is_ingestible(rating_payload):
            archive_path = _fetch_artifact_archive(artifact)
            try:
                s3_uri = upload_artifact(archive_path, artifact.id)
                update_artifact_attributes(
                    session, artifact, status=ArtifactStatus.accepted, s3_key=s3_uri
                )

                _persist_rating(session, artifact, rating_payload)
                session.commit()
            finally:
                if archive_path and os.path.exists(archive_path):
                    try:
                        os.remove(archive_path)
                        shutil.rmtree(Path(archive_path).parent, ignore_errors=True)
                    except Exception:
                        pass
            return ArtifactStatus.accepted

        update_artifact_attributes(session, artifact, status=ArtifactStatus.rejected)
        session.commit()
        return ArtifactStatus.rejected


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
        final_status = ingest_artifact(artifact_id)  # should return an ArtifactStatus
        logger.info(
            "Finished ingestion for artifact_id=%s with status=%s",
            artifact_id,
            final_status,
        )

        return {"artifact_id": artifact_id, "status": final_status.value}

    except ValueError as exc:
        # Expected domain errors (e.g., artifact not found, not pending)
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
        # Unexpected failure: log stack trace and re-raise so Lambda reports an error
        logger.exception(
            "Unexpected error ingesting artifact_id=%s: %s", artifact_id, exc
        )
        raise


if __name__ == "__main__":
    pass
    # print(os.getenv("DATABASE_URL"))
    # artifact: Artifact = Artifact(
    #     id=101,
    #     name="bert-base-uncased",
    #     type="model",
    #     source_url="https://huggingface.co/google-bert/bert-base-uncased"
    # )

    # zip_file_path = _fetch_artifact_archive(artifact)
    # print(zip_file_path)
    # upload_artifact(zip_file_path, artifact.id)
    # os.remove(zip_file_path)
    # import json
    # import os

    # import boto3

    # lambda_client = boto3.client(
    #     "lambda", region_name=os.environ.get("AWS_REGION", "us-east-2")
    # )
    # INGESTION_LAMBDA_NAME = os.environ["INGESTION_LAMBDA_NAME"]

    # def trigger_ingestion(artifact_id: int) -> None:
    #     event = {"artifact_id": artifact_id}
    #     lambda_client.invoke(
    #         FunctionName=INGESTION_LAMBDA_NAME,
    #         InvocationType="Event",  # async
    #         Payload=json.dumps(event).encode("utf-8"),
    #     )

    # trigger_ingestion(1001)
