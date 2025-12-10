"""Unit tests for S3 storage helpers in app.services.storage.

These tests exercise upload and listing helpers while
patching the module-level S3 client to avoid network calls.
"""

import os
import tempfile
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
import app.services.storage as storage


@pytest.fixture
def mock_s3_client() -> Iterator[MagicMock]:
    """Fixture to patch boto3 S3 client inside storage module.

    Yields a MagicMock that replaces the module-level ``s3`` client.
    """
    with patch.object(storage, "s3") as mock_s3:
        yield mock_s3


def test_upload_artifact(mock_s3_client: MagicMock) -> None:
    """Ensure upload_artifact constructs the correct key and returns the key."""
    # Create a temporary fake file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"dummy content")
        tmp_path = tmp.name

    artifact_id = 42

    # Run the upload_model function
    result_key = storage.upload_artifact(tmp_path, artifact_id)

    # Verify upload_file called with expected args
    expected_key = f"artifact/{artifact_id}/{os.path.basename(tmp_path)}"
    mock_s3_client.upload_file.assert_called_once_with(
        tmp_path, storage.S3_BUCKET, expected_key
    )

    # Verify returned key
    assert result_key == expected_key

    # Clean up temp file
    os.remove(tmp_path)


def test_list_artifacts_with_contents(mock_s3_client: MagicMock) -> None:
    """Ensure list_artifacts returns expected list when S3 responds with objects."""
    mock_s3_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "artifact/a.pt"}, {"Key": "artifact/b.pt"}]
    }

    result = storage.list_artifacts()
    mock_s3_client.list_objects_v2.assert_called_once_with(
        Bucket=storage.S3_BUCKET, Prefix="artifact/"
    )

    assert result == ["artifact/a.pt", "artifact/b.pt"]


def test_list_artifacts_empty(mock_s3_client: MagicMock) -> None:
    """Ensure list_artifacts returns empty list when no Contents present."""
    mock_s3_client.list_objects_v2.return_value = {}

    result = storage.list_artifacts()
    assert result == []
