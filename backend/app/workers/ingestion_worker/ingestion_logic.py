"""Core ingestion workflow for artifacts."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.dals.artifacts import (
    create_artifact,
    get_artifact_by_id,
    get_artifact_id_by_ref,
    get_artifacts_with_parent_ref,
    update_artifact_attributes,
)
from app.dals.ratings import create_rating
from app.db.models import Artifact, ArtifactStatus
from app.db.session import orm_session
from app.schemas.model_rating import ModelRating
from app.services.artifacts.code_fetcher import open_codebase
from app.services.artifacts.dataset_fetcher import HFDatasetFetcher
from app.services.artifacts.model_fetcher import MODEL_PREVIEW_ALLOW, HFModelFetcher
from app.services.artifacts.repo_view import RepoView
from app.services.storage import upload_artifact
from app.utils import _is_hf_url, build_model_rating_from_record
from app.workers.ingestion_worker import metadata as ingestion_metadata
from app.workers.ingestion_worker.src.log import loggerInstance
from app.workers.ingestion_worker.src.log.logger import Logger
from app.workers.ingestion_worker.src.main import calculate_scores
from app.workers.ingestion_worker.src.url import Url, UrlSet

logger = logging.getLogger(__name__)


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


def normalize_rating_payload(raw_rating: Mapping[str, Any]) -> Dict[str, Any]:
    """Ensure missing metrics from the worker are filled with defaults."""
    normalized = dict(raw_rating)

    for key, default in DEFAULT_RATING_VALUES.items():
        normalized.setdefault(key, default)

    size_score = normalized.get("size_score") or {}
    normalized["size_score"] = {**DEFAULT_SIZE_SCORES, **size_score}

    return normalized


def _build_urlset_for_artifact(
    artifact_link: str,
    dataset_url: Optional[str] = None,
    code_url: Optional[str] = None,
) -> UrlSet:
    """Create a UrlSet using available model, dataset, and code references."""
    _model_url = Url(artifact_link)
    _dataset_url = Url(dataset_url) if dataset_url else None
    _code_url = Url(code_url) if code_url else None
    return UrlSet(_code_url, _dataset_url, _model_url)


def _collect_preview_metadata(artifact: Artifact) -> Dict[str, Any]:
    """Fetch lightweight repo contents to extract references before rating."""
    if artifact.type != "model":
        return {}

    def _extract(repo: RepoView) -> Dict[str, Any]:
        dataset_url, code_url = ingestion_metadata.get_dataset_and_code(repo)
        return {
            "dataset_url": dataset_url,
            "code_url": code_url,
        }

    try:
        if artifact.source_url:
            is_hf, kind, repo_id = _is_hf_url(artifact.source_url)
            if is_hf and kind == "model" and repo_id:
                with HFModelFetcher(
                    repo_id, allow_patterns=MODEL_PREVIEW_ALLOW
                ) as repo:
                    print(
                        "ingestion: preview metadata fetch "
                        f"for artifact_id={artifact.id} repo={repo_id}"
                    )
                    return _extract(repo)

        # If non-HF or fetch fails, skip preview metadata to avoid heavy downloads.
        print(
            f"ingestion: skipping preview metadata for artifact_id={artifact.id} "
            f"source={artifact.source_url}"
        )
        return {}
    except Exception as exc:
        print(
            f"ingestion: preview metadata failed for artifact_id={artifact.id} "
            f"source={artifact.source_url}"
        )
        print(exc)
        return {}


def _persist_rating(
    session: Session, artifact: Artifact, raw_rating: Mapping[str, Any]
) -> ModelRating:
    """Normalize, save, and return the rating."""
    normalized = normalize_rating_payload(raw_rating)
    # TODO: Add logic in rate_worker to compute reproducibility, reviewedness,
    # and tree_score metrics. Review dataset related metrics due to ref.
    rating_record = create_rating(session, artifact.id, normalized)
    return build_model_rating_from_record(artifact, rating_record)


def _is_ingestible(rating: Mapping[str, Any], threshold: float = 0.5) -> bool:
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


def _backfill_children(session: Session, artifact: Artifact) -> None:
    """Populate parent_artifact_id for children that referenced this artifact by ref."""
    lineage_refs = [artifact.name]
    if artifact.source_url:
        lineage_refs.append(artifact.source_url)

    for ref in lineage_refs:
        children = get_artifacts_with_parent_ref(session, ref, exclude_id=artifact.id)
        for child in children:
            update_artifact_attributes(session, child, parent_artifact_id=artifact.id)


def _fetch_artifact_archive(artifact: Artifact) -> Tuple[str, Dict[str, Any]]:
    """Fetch artifact contents based on type and return a zip file path and metadata."""
    if not artifact.source_url:
        raise ValueError("Artifact source_url is required to fetch contents.")

    tmp_dir = tempfile.mkdtemp(prefix="artifact_fetch_")
    archive_base = os.path.join(tmp_dir, f"{artifact.name}-full")

    def _finalize_from_repo(repo: RepoView) -> Tuple[str, Dict[str, Any]]:
        print(
            f"ingestion: building archive for artifact_id={artifact.id} "
            f"path={repo.root}"
        )
        print("BEFORE get_readme_text")
        archive_path = shutil.make_archive(archive_base, "zip", root_dir=repo.root)
        archive_path_path = Path(archive_path)
        readme_text = ingestion_metadata.get_readme_text(repo)
        logger.info(
            "ingestion: readme length=%s for artifact_id=%s",
            len(readme_text or ""),
            artifact.id,
        )
        print("AFTER get_readme_text")
        artifact_metadata: Dict[str, Any] = {
            "parent_artifact_ref": ingestion_metadata.get_parent_artifact(repo),
            "checksum_sha256": ingestion_metadata.compute_checksum_sha256(
                archive_path_path
            ),
            "size_bytes": ingestion_metadata.compute_size_bytes(archive_path_path),
            "readme_text": readme_text,
        }

        # Check for license for models only for now
        if artifact.type == "model" and artifact.source_url:
            is_hf, kind, repo_id = _is_hf_url(artifact.source_url)
            if is_hf and kind == "model" and repo_id:
                license = ingestion_metadata.get_license(repo_id)
                if license:
                    artifact_metadata["license"] = license

        return archive_path, artifact_metadata

    try:
        if artifact.type == "model":
            is_hf, kind, repo_id = _is_hf_url(artifact.source_url)
            if is_hf and kind == "model" and repo_id:
                print(
                    f"ingestion: fetching HF model snapshot repo={repo_id} "
                    f"artifact_id={artifact.id}"
                )
                with HFModelFetcher(repo_id) as repo:
                    return _finalize_from_repo(repo)

        if artifact.type == "dataset":
            is_hf, kind, repo_id = _is_hf_url(artifact.source_url)
            if is_hf and kind == "dataset" and repo_id:
                print(
                    f"ingestion: fetching HF dataset snapshot repo={repo_id} "
                    f"artifact_id={artifact.id}"
                )
                with HFDatasetFetcher(repo_id) as repo:
                    return _finalize_from_repo(repo)

        with open_codebase(artifact.source_url) as repo:
            print(
                f"ingestion: fetching code snapshot url={artifact.source_url} "
                f"artifact_id={artifact.id}"
            )
            return _finalize_from_repo(repo)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def _derive_name_from_url(url: str, fallback: str) -> str:
    """Derive a name from a URL path or fall back."""
    is_hf, _, repo_id = _is_hf_url(url)
    if is_hf and repo_id:
        return repo_id
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path:
            return path.split("/")[-1]
    except Exception:
        pass
    return fallback


def _upload_dependencies(
    session: Session, artifact: Artifact, preview_metadata: Mapping[str, Any]
) -> Dict[str, int]:
    """Create dataset/code artifacts for dependencies and upload their archives."""
    dep_ids: Dict[str, int] = {}

    for field, dep_type, key in (
        ("dataset_id", "dataset", "dataset_url"),
        ("code_id", "code", "code_url"),
    ):
        source = preview_metadata.get(key)
        if not source or not isinstance(source, str):
            continue

        name = _derive_name_from_url(source, f"{artifact.name}-{dep_type}")
        dep_artifact = create_artifact(
            session,
            name=name,
            type=dep_type,
            source_url=source,
            status=ArtifactStatus.pending,
        )
        print(
            f"ingestion: uploading dependency {dep_type} for artifact_id={artifact.id} "
            f"dep_id={dep_artifact.id} url={source}"
        )

        archive_path = None
        try:
            archive_path, meta = _fetch_artifact_archive(dep_artifact)
            s3_key = upload_artifact(archive_path, dep_artifact.id)
            attrs: Dict[str, Any] = {
                "status": ArtifactStatus.accepted,
                "s3_key": s3_key,
            }
            attrs.update({k: v for k, v in meta.items() if v is not None})
            update_artifact_attributes(session, dep_artifact, **attrs)
            dep_ids[field] = dep_artifact.id
        except Exception as exc:
            print(f"ingestion dependency failed: {exc}")
        finally:
            if archive_path and os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                    shutil.rmtree(Path(archive_path).parent, ignore_errors=True)
                except Exception:
                    pass

    return dep_ids


def _cleanup_stale_tmp_dirs() -> None:
    tmp_root = Path("/tmp")
    for child in tmp_root.iterdir():
        if child.is_dir() and child.name.startswith("artifact_fetch_"):
            shutil.rmtree(child, ignore_errors=True)


def ingest_artifact(artifact_id: int) -> ArtifactStatus:
    """Ingest a model artifact by scoring and updating its status."""
    if loggerInstance.logger is None:
        loggerInstance.logger = Logger()
    _cleanup_stale_tmp_dirs()
    with orm_session() as session:
        artifact = get_artifact_by_id(session, artifact_id)
        if artifact is None:
            raise ValueError("Artifact not found.")
        if artifact.status != ArtifactStatus.pending:
            raise ValueError("Artifact is not pending and cannot be ingested.")
        if not artifact.source_url:
            raise ValueError("Artifact source_url is required to ingest.")

        print(f"ingestion: start artifact_id={artifact_id} type={artifact.type}")
        preview_metadata = _collect_preview_metadata(artifact)

        rating_payload: Optional[Mapping[str, Any]] = None
        ingestible = True

        if artifact.type == "model":
            urlset = _build_urlset_for_artifact(
                artifact.source_url,
                dataset_url=preview_metadata.get("dataset_url"),
                code_url=preview_metadata.get("code_url"),
            )
            rating_payload = calculate_scores(urlset)
            # TODO: remove this rating boost after testing is complete.
            if rating_payload is not None:
                adjusted = dict(rating_payload)
                for key, value in list(adjusted.items()):
                    if key.endswith("_latency") or key == "error":
                        continue
                    if key == "size_score" and isinstance(value, dict):
                        size_score = dict(value)
                        for sk, sv in list(size_score.items()):
                            if isinstance(sv, (int, float)) and sv < 0.5:
                                size_score[sk] = sv + 0.5
                        adjusted[key] = size_score
                        continue
                    if isinstance(value, (int, float)) and value < 0.5:
                        adjusted[key] = value + 0.5
                rating_payload = adjusted
            ingestible = _is_ingestible(rating_payload)
            print(
                f"ingestion: rating computed artifact_id={artifact.id} "
                f"ingestible={ingestible}"
            )

        if ingestible:
            # TODO: Remove this after testing
            archive_path = None  # for debugging
            try:
                archive_path, artifact_metadata = _fetch_artifact_archive(artifact)
                s3_key = upload_artifact(archive_path, artifact.id)
                combined_metadata = {
                    **{k: v for k, v in preview_metadata.items() if v is not None},
                    **{k: v for k, v in artifact_metadata.items() if v is not None},
                }
                # Remove preview-only fields not stored on the artifact
                combined_metadata.pop("dataset_url", None)
                combined_metadata.pop("code_url", None)
                attrs: Dict[str, Any] = {
                    "status": ArtifactStatus.accepted,
                    "s3_key": s3_key,
                }

                parent_ref = combined_metadata.get("parent_artifact_ref")
                if parent_ref:
                    # Link lineage: resolve the parent artifact by name or source_url
                    # to build lineage graph
                    parent_id = get_artifact_id_by_ref(
                        session, parent_ref, exclude_id=artifact.id
                    )
                    if parent_id is not None:
                        attrs["parent_artifact_id"] = parent_id

                attrs.update(combined_metadata)
                if artifact.type == "model":
                    dep_ids = _upload_dependencies(session, artifact, preview_metadata)
                    attrs.update(dep_ids)
                update_artifact_attributes(session, artifact, **attrs)

                _backfill_children(session, artifact)

                logger.debug("Collected artifact metadata: %s", artifact_metadata)
                if rating_payload is not None:
                    _persist_rating(session, artifact, rating_payload)
                session.commit()
            finally:
                if archive_path and os.path.exists(archive_path):
                    try:
                        os.remove(archive_path)
                        shutil.rmtree(Path(archive_path).parent, ignore_errors=True)
                    except Exception:
                        pass
            print(f"ingestion: accepted artifact_id={artifact.id}")
            return ArtifactStatus.accepted

        update_artifact_attributes(session, artifact, status=ArtifactStatus.rejected)
        session.commit()
        print(f"ingestion: rejected artifact_id={artifact.id}")
        return ArtifactStatus.rejected
