"""Business logic for computing artifact costs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from flask import current_app
from license_expression import Licensing

from app.dals.artifact_audit import get_artifact_audit_log
from app.dals.artifacts import get_artifact_by_id
from app.dals.users import get_user_by_id
from app.db.models import UserRole
from app.db.session import orm_session
from app.schemas.artifact import ArtifactCost
from app.services.artifacts.code_fetcher import open_codebase


class ArtifactCostError(Exception):
    """Base exception for artifact cost errors."""


class InvalidArtifactTypeError(ArtifactCostError):
    """Raised when the artifact type is missing or invalid."""


class InvalidArtifactIdError(ArtifactCostError):
    """Raised when the artifact id is missing or invalid."""


class ArtifactNotFoundError(ArtifactCostError):
    """Raised when the artifact cannot be found."""


def compute_artifact_cost(
    artifact_id: int, include_dependencies: bool = False
) -> Dict[int, ArtifactCost]:
    """Calculate cost for an artifact, optionally including dependencies."""
    if not artifact_id or artifact_id <= 0:
        raise InvalidArtifactIdError(
            "There is missing field(s) in the artifact_type or artifact_id or it is "
            "formed improperly, or is invalid."
        )

    try:
        with orm_session() as session:
            artifact = get_artifact_by_id(session, artifact_id)
            if artifact is None:
                raise ArtifactNotFoundError("Artifact does not exist.")

            def _size_from_art(art: object) -> float:
                if not art or getattr(art, "size_bytes", None) is None:
                    raise ArtifactNotFoundError("Artifact does not exist.")
                return float(getattr(art, "size_bytes"))

            costs: Dict[int, ArtifactCost] = {}
            base_total = _size_from_art(artifact)
            costs[artifact.id] = ArtifactCost(
                total_cost=base_total,
                standalone_cost=base_total if include_dependencies else None,
            )

            if include_dependencies:
                deps = [
                    artifact.dataset
                    or (
                        get_artifact_by_id(session, artifact.dataset_id)
                        if artifact.dataset_id
                        else None
                    ),
                    artifact.code
                    or (
                        get_artifact_by_id(session, artifact.code_id)
                        if artifact.code_id
                        else None
                    ),
                ]
                for dep in deps:
                    if dep is None:
                        continue
                    dep_size = _size_from_art(dep)
                    costs[dep.id] = ArtifactCost(
                        total_cost=dep_size, standalone_cost=dep_size
                    )
                    base_total += dep_size
                costs[artifact.id].total_cost = base_total

            return costs
    except ArtifactCostError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ArtifactCostError(
            "The artifact cost calculator encountered an error."
        ) from exc


class RepoNotFound(Exception):
    """GitHub repository does not exist."""


class ExternalLicenseError(Exception):
    """External license information could not be retrieved."""


class LicenseCheckError(Exception):
    """Base exception for license compatibility checks."""


class InvalidLicenseRequestError(LicenseCheckError):
    """Raised when the license check input is malformed."""


@dataclass(frozen=True)
class LicenseInfo:
    """Normalized license info using SPDX-like identifiers."""

    spdx_id: str


def _parse_github_url(github_url: str) -> Tuple[str, str]:
    """Parse a GitHub URL into (owner, repo).

    Accepts URLs such as:
    * https://github.com/google-research/bert
    * https://github.com/google-research/bert.git
    """
    parsed = urlparse(github_url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise ValueError("github_url must point to github.com")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        msg = "github_url must be of the form " "https://github.com/<owner>/<repo>"
        raise ValueError(msg)

    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def fetch_github_license(
    github_url: str,
    *,
    timeout: float = 5.0,
) -> LicenseInfo:
    """Fetch license information for a GitHub repository.

    The function uses the GitHub API. It first tries the `/license`
    endpoint and then falls back to the generic repo endpoint if
    necessary.
    """
    owner, repo = _parse_github_url(github_url)
    base = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        license_resp = requests.get(f"{base}/license", timeout=timeout)
        if license_resp.status_code == 404:
            # Fall back to the generic repo endpoint below.
            pass
        elif 200 <= license_resp.status_code < 300:
            license_data = license_resp.json().get("license") or {}
            spdx_id = (
                license_data.get("spdx_id") or license_data.get("key") or ""
            ).strip()
            if not spdx_id or spdx_id.upper() == "NOASSERTION":
                # Fallback to deterministic license detection via repository files
                return fetch_repo_license_via_files(github_url)

            return LicenseInfo(spdx_id=spdx_id.lower())
        else:
            msg = f"GitHub /license endpoint failed: {license_resp.status_code}"
            raise ExternalLicenseError(msg)

        repo_resp = requests.get(base, timeout=timeout)
        if repo_resp.status_code == 404:
            msg = f"Repository {owner}/{repo} not found"
            raise RepoNotFound(msg)
        if not (200 <= repo_resp.status_code < 300):
            msg = f"GitHub repo endpoint failed: {repo_resp.status_code}"
            raise ExternalLicenseError(msg)

        license_data = repo_resp.json().get("license") or {}
        spdx_id = (license_data.get("spdx_id") or license_data.get("key") or "").strip()
        if not spdx_id or spdx_id.upper() == "NOASSERTION":
            # Fallback to deterministic license detection via repository files
            return fetch_repo_license_via_files(github_url)

        return LicenseInfo(spdx_id=spdx_id.lower())

    except RepoNotFound:
        raise
    except requests.RequestException as exc:
        current_app.logger.exception(
            "Network error while fetching GitHub license",
        )
        raise ExternalLicenseError(
            "Network error while fetching GitHub license",
        ) from exc
    except ExternalLicenseError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        current_app.logger.exception(
            "Unexpected error while fetching GitHub license",
        )
        raise ExternalLicenseError(
            "Unexpected error while fetching GitHub license",
        ) from exc


def fetch_repo_license_via_files(github_url: str) -> LicenseInfo:
    """Fetch and detect license.

    Inspects LICENSE / COPYING files when GitHub does not provide a usable SPDX id.
    """
    with open_codebase(github_url) as repo:
        # Common license file patterns
        candidates = (
            list(repo.glob("LICENSE*"))
            + list(repo.glob("COPYING*"))
            + list(repo.glob("license*"))
            + list(repo.glob("copying*"))
        )

        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            detected = detect_spdx_from_license_text(text)
            if detected:
                # Validate SPDX expression using license-expression
                licensing = Licensing()
                try:
                    licensing.parse(detected)
                except Exception:
                    continue

                return LicenseInfo(spdx_id=detected)

    raise ExternalLicenseError("Unable to detect license from repository contents")


def detect_spdx_from_license_text(text: str) -> Optional[str]:
    """Detect SPDX license identifier from raw license file text.

    This function is deterministic and intentionally conservative.
    It mirrors the behavior of lightweight SPDX scanners and avoids LLMs.
    """
    lowered = text.lower()

    # ---- GPL family ----
    if "gnu general public license" in lowered:
        if "version 2" in lowered:
            # Explicitly detect GPL-2.0-only vs or-later
            if "only valid version" in lowered or "not v3" in lowered:
                return "gpl-2.0-only"
            if "or any later version" in lowered:
                return "gpl-2.0-or-later"
            return "gpl-2.0-only"  # conservative default
        if "version 3" in lowered:
            if "or any later version" in lowered:
                return "gpl-3.0-or-later"
            return "gpl-3.0-only"

    # ---- LGPL ----
    if "gnu lesser general public license" in lowered:
        if "version 2.1" in lowered:
            return "lgpl-2.1"
        if "version 3" in lowered:
            return "lgpl-3.0"

    # ---- Apache ----
    if "apache license" in lowered and "version 2.0" in lowered:
        return "apache-2.0"

    # ---- MIT ----
    if "permission is hereby granted, free of charge" in lowered:
        return "mit"

    # ---- BSD ----
    if "redistribution and use in source and binary forms" in lowered:
        if "neither the name" in lowered:
            return "bsd-3-clause"
        return "bsd-2-clause"

    # ---- MPL ----
    if "mozilla public license" in lowered and "2.0" in lowered:
        return "mpl-2.0"

    return None


def normalize_license_string(raw: Optional[str]) -> Optional[str]:
    """Normalize raw license strings into SPDX-ish identifiers."""
    if raw is None:
        return None

    value = raw.strip().lower()
    mapping = {
        "mit license": "mit",
        "mit": "mit",
        "apache2": "apache-2.0",
        "apache 2.0": "apache-2.0",
        "apache license 2.0": "apache-2.0",
        "apache-2.0": "apache-2.0",
        "bsd-3-clause": "bsd-3-clause",
        "bsd 3-clause": "bsd-3-clause",
        'bsd 3-clause "new" or "revised" license': "bsd-3-clause",
        "bsd 2-clause": "bsd-2-clause",
        "gplv3": "gpl-3.0",
        "gpl-3.0": "gpl-3.0",
        "gplv2": "gpl-2.0",
        "gpl-2.0": "gpl-2.0",
        "lgplv3": "lgpl-3.0",
        "lgpl-3.0": "lgpl-3.0",
        "lgpl-2.1": "lgpl-2.1",
        "agpl-3.0": "agpl-3.0",
        "mpl-2.0": "mpl-2.0",
        "epl-2.0": "epl-2.0",
        "unlicense": "unlicense",
        "isc": "isc",
        "cc0-1.0": "cc0-1.0",
        "cc0": "cc0-1.0",
        "proprietary": "proprietary",
        "custom": "custom",
    }

    return mapping.get(value, value)


def is_license_compatible_for_finetune_inference(
    model_spdx: str,
    repo_spdx: str,
) -> bool:
    """Decide if two licenses are compatible for fine-tune + inference.

    This is a conservative heuristic inspired by tools such as ModelGo.
    It is not a complete legal analysis but is sufficient for the course
    project.
    """
    model = (model_spdx or "").lower()
    repo = (repo_spdx or "").lower()

    permissive = {
        "mit",
        "bsd-2-clause",
        "bsd-3-clause",
        "apache-2.0",
        "isc",
        "unlicense",
        "cc0-1.0",
    }

    weak_copyleft = {
        "lgpl-2.1",
        "lgpl-3.0",
        "mpl-2.0",
        "epl-2.0",
    }

    strong_copyleft = {
        "gpl-2.0",
        "gpl-2.0-only",
        "gpl-2.0-or-later",
        "gpl-3.0",
        "gpl-3.0-only",
        "gpl-3.0-or-later",
        "agpl-3.0",
        "agpl-3.0-only",
        "agpl-3.0-or-later",
    }

    if model in {"proprietary", "custom"} or repo in {"proprietary", "custom"}:
        return False

    if not model or not repo:
        return False

    if repo in strong_copyleft and model not in strong_copyleft:
        return False

    if (repo in permissive or repo in weak_copyleft) and (
        model in permissive or model in weak_copyleft or model in strong_copyleft
    ):
        return True

    if model == repo:
        return True

    return False


def check_model_license_compatibility(artifact_id: int, github_url: str) -> bool:
    """Return whether the model artifact license is compatible with the repo."""
    if not isinstance(github_url, str) or not github_url:
        raise InvalidLicenseRequestError(
            (
                "The license check request is malformed or references an "
                "unsupported usage context."
            )
        )

    with orm_session() as session:
        artifact = get_artifact_by_id(session, artifact_id)
        if artifact is None or artifact.type != "model":
            raise ArtifactNotFoundError(
                "The artifact or GitHub project could not be found."
            )
        model_license_raw = artifact.license

    model_spdx = normalize_license_string(model_license_raw)
    if not model_spdx:
        return False

    try:
        repo_license = fetch_github_license(github_url)
    except ValueError as exc:
        raise InvalidLicenseRequestError(
            (
                "The license check request is malformed or references an "
                "unsupported usage context."
            )
        ) from exc
    except RepoNotFound as exc:
        raise ArtifactNotFoundError("Artifact does not exist.") from exc

    compatible = is_license_compatible_for_finetune_inference(
        model_spdx=model_spdx,
        repo_spdx=repo_license.spdx_id,
    )
    return compatible


def get_artifact_audit_entries(
    artifact_type: str, artifact_id: int
) -> List[Dict[str, Any]]:
    """Return audit entries for an artifact."""
    allowed_types = {"model", "dataset", "code"}
    if artifact_type not in allowed_types:
        raise InvalidArtifactTypeError(
            "There is missing field(s) in the artifact_type or artifact_id or it is "
            "formed improperly, or is invalid."
        )
    if artifact_id <= 0:
        raise InvalidArtifactIdError(
            "There is missing field(s) in the artifact_type or artifact_id or it is "
            "formed improperly, or is invalid."
        )

    with orm_session() as session:
        artifact = get_artifact_by_id(session, artifact_id)
        if artifact is None:
            raise ArtifactNotFoundError("Artifact does not exist.")
        if artifact.type != artifact_type:
            raise InvalidArtifactTypeError(
                "There is missing field(s) in the artifact_type or artifact_id or "
                "it is formed improperly, or is invalid."
            )

        logs = get_artifact_audit_log(session=session, artifact_id=artifact_id)

        entries: List[Dict[str, Any]] = []
        for log in logs:
            user = get_user_by_id(session, log.user_id) if log.user_id else None
            entries.append(
                {
                    "user": {
                        "name": user.username if user else None,
                        "is_admin": bool(
                            user and getattr(user, "role", None) == UserRole.admin
                        ),
                    },
                    "date": log.occurred_at.isoformat(),
                    "artifact": {
                        "name": artifact.name,
                        "id": artifact.id,
                        "type": artifact.type,
                    },
                    "action": log.action,
                }
            )

        return entries
