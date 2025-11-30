"""Tests for license scoring."""

from app.workers.ingestion_worker.src.license import calculate_license_score


def test_score_license_empty() -> None:
    """Return zero when no license data is present."""
    assert calculate_license_score({}) == 0
