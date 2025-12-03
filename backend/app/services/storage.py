"""S3 storage helpers for uploading, downloading, and listing models.

This module provides thin helpers that talk to Amazon S3 using boto3.
Environment variables used:

- ``AWS_REGION`` (default: "us-east-2")
- ``S3_BUCKET_NAME`` (default: "mod-reg-bucket-28")
- ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY`` for credentials

These helpers are small conveniences consumed by the model registry API
and workers.
"""

import os
from typing import List

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "mod-reg-bucket-dev")

# Create the S3 client using credentials from environment
s3 = boto3.client("s3", region_name=AWS_REGION)


def upload_artifact(file_path: str, artifact_id: int) -> str:
    """Upload an artifact to S3 and return its S3 URI.

    The S3 object key uses the pattern ``artifact/{artifact_id}/{filename}``.
    Returns the ``s3://`` URI of the uploaded object on success.
    """
    try:
        key = f"artifact/{artifact_id}/{os.path.basename(file_path)}"
        s3.upload_file(file_path, S3_BUCKET, key)
        s3_uri = f"s3://{S3_BUCKET}/{key}"
        print(f"Uploaded {file_path} to {s3_uri}")
        return s3_uri
    except ClientError as e:
        print(f"S3 upload failed: {e}")
        raise


def download_artifact(
    artifact_id: int, filename: str, output_dir: str = "./downloads"
) -> str:
    """Download a specific artifact file from S3 to a local directory.

    Creates ``output_dir`` if it does not exist and returns the local
    path to the downloaded file.
    """
    os.makedirs(output_dir, exist_ok=True)
    key = f"artifact/{artifact_id}/{filename}"
    output_path = os.path.join(output_dir, filename)
    try:
        s3.download_file(S3_BUCKET, key, output_path)
        print(f"Downloaded {key} to {output_path}")
        return output_path
    except ClientError as e:
        print(f"S3 download failed: {e}")
        raise


def list_artifacts(prefix: str = "artifact/") -> List[str]:
    """List uploaded artifact keys under ``prefix``.

    Returns a list of object keys found under the given prefix. If no
    objects are found an empty list is returned.
    """
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if "Contents" not in response:
            return []
        keys = [obj["Key"] for obj in response["Contents"]]
        print(f"Found {len(keys)} items under {prefix}")
        return keys
    except ClientError as e:
        print(f"Failed to list artifacts: {e}")
        raise


def delete_all_objects() -> None:
    """Delete all objects from the configured S3 bucket."""
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET):
            keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if keys:
                s3.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": keys})
    except ClientError as e:
        print(f"Failed to delete objects: {e}")
        raise
