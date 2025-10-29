# registry/storage/s3_client.py
import boto3
from botocore.exceptions import ClientError
import os

# Load environment variables (set these in GitHub Secrets or .env)
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "model-registry-bucket-ott29")

# Create the S3 client using credentials from environment (GitHub Secrets)
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def upload_model(file_path: str, model_name: str) -> str:
    """
    Uploads a model artifact to S3 and returns its S3 URI.
    Example key structure: models/{model_name}/{filename}
    """
    try:
        key = f"models/{model_name}/{os.path.basename(file_path)}"
        s3.upload_file(file_path, S3_BUCKET, key)
        s3_uri = f"s3://{S3_BUCKET}/{key}"
        print(f"Uploaded {file_path} to {s3_uri}")
        return s3_uri
    except ClientError as e:
        print(f"S3 upload failed: {e}")
        raise

def download_model(model_name: str, filename: str, output_dir: str = "./downloads") -> str:
    """
    Downloads a specific model file from S3 to local directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    key = f"models/{model_name}/{filename}"
    output_path = os.path.join(output_dir, filename)
    try:
        s3.download_file(S3_BUCKET, key, output_path)
        print(f"Downloaded {key} to {output_path}")
        return output_path
    except ClientError as e:
        print(f"S3 download failed: {e}")
        raise

def list_models(prefix: str = "models/"):
    """
    Lists all uploaded models under a prefix.
    Useful for your 'enumerate' API endpoint.
    """
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if "Contents" not in response:
            return []
        keys = [obj["Key"] for obj in response["Contents"]]
        print(f"Found {len(keys)} items under {prefix}")
        return keys
    except ClientError as e:
        print(f"Failed to list models: {e}")
        raise
