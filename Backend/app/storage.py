import uuid
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig

from app.config import settings

_s3_client = None


def _use_local_storage() -> bool:
    return settings.STORAGE_BACKEND.lower() == "local"


def _local_root() -> Path:
    root = Path(settings.LOCAL_UPLOAD_DIR)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _local_path(key: str) -> Path:
    root = _local_root().resolve()
    path = (root / key).resolve()
    if root not in path.parents and path != root:
        raise ValueError("Invalid storage key")
    return path


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )
    return _s3_client


def ensure_bucket():
    if _use_local_storage():
        _local_root()
        return

    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except Exception:
        client.create_bucket(Bucket=settings.S3_BUCKET_NAME)


def upload_image_bytes(data: bytes, patient_id: str, content_type: str = "image/jpeg") -> str:
    """Stores image bytes and returns the object key."""
    key = f"patients/{patient_id}/{uuid.uuid4()}.jpg"
    if _use_local_storage():
        path = _local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    client = get_s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    return key


def upload_analysis_bytes(
    data: bytes,
    patient_id: str,
    prefix: str = "analysis",
    extension: str = "png",
    content_type: str = "image/png",
) -> str:
    key = f"patients/{patient_id}/{prefix}/{uuid.uuid4()}.{extension}"
    if _use_local_storage():
        path = _local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    client = get_s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    return key


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    if _use_local_storage():
        return f"/media/{key}"

    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )


def download_image_bytes(key: str) -> bytes:
    if _use_local_storage():
        return _local_path(key).read_bytes()

    client = get_s3_client()
    obj = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    return obj["Body"].read()
