"""Unit tests for S3 storage helpers in app.services.storage.

These tests exercise upload, download and listing helpers while
patching the module-level S3 client to avoid network calls.
"""

import os
import tempfile
from pathlib import Path
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


def test_upload_model(mock_s3_client: MagicMock) -> None:
    """Ensure upload_model constructs the correct key and returns the proper URI."""
    # Create a temporary fake file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"dummy content")
        tmp_path = tmp.name

    model_name = "test_model"

    # Run the upload_model function
    result_uri = storage.upload_model(tmp_path, model_name)

    # Verify upload_file called with expected args
    expected_key = f"models/{model_name}/{os.path.basename(tmp_path)}"
    mock_s3_client.upload_file.assert_called_once_with(
        tmp_path, storage.S3_BUCKET, expected_key
    )

    # Verify returned URI format
    assert result_uri == f"s3://{storage.S3_BUCKET}/{expected_key}"

    # Clean up temp file
    os.remove(tmp_path)


def test_download_model(mock_s3_client: MagicMock, tmp_path: Path) -> None:
    """Ensure download_model downloads file to expected path."""
    model_name = "test_model"
    filename = "weights.bin"
    out_dir = tmp_path / "downloads"

    # Run function
    result_path = storage.download_model(model_name, filename, str(out_dir))

    expected_key = f"models/{model_name}/{filename}"
    expected_path = out_dir / filename

    mock_s3_client.download_file.assert_called_once_with(
        storage.S3_BUCKET, expected_key, str(expected_path)
    )

    assert str(expected_path) == result_path


def test_list_models_with_contents(mock_s3_client: MagicMock) -> None:
    """Ensure list_models returns expected list when S3 responds with objects."""
    mock_s3_client.list_objects_v2.return_value = {
        "Contents": [{"Key": "models/a.pt"}, {"Key": "models/b.pt"}]
    }

    result = storage.list_models()
    mock_s3_client.list_objects_v2.assert_called_once_with(
        Bucket=storage.S3_BUCKET, Prefix="models/"
    )

    assert result == ["models/a.pt", "models/b.pt"]


def test_list_models_empty(mock_s3_client: MagicMock) -> None:
    """Ensure list_models returns empty list when no Contents present."""
    mock_s3_client.list_objects_v2.return_value = {}

    result = storage.list_models()
    assert result == []
