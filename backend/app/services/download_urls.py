"""Helpers for signing and validating public download URLs."""

from __future__ import annotations

import hmac
import time
from hashlib import sha256
from pathlib import Path

from fastapi import Request

from app.core.config import Settings
from app.core.errors import ExpiredDownloadSignatureError, InvalidDownloadSignatureError
from app.models.generation import GenerationRecord


def build_download_url(*, request: Request, record: GenerationRecord, settings: Settings) -> str:
    zip_path = _validated_zip_path(record)
    expires_at = int(time.time()) + settings.download_url_ttl_seconds
    signature = _sign(
        generation_id=record.generation_id,
        expires_at=expires_at,
        zip_path=zip_path,
        secret=settings.download_url_secret,
    )
    return str(
        request.url_for("download_generation", generation_id=record.generation_id).include_query_params(
            exp=expires_at,
            sig=signature,
        )
    )


def verify_download_signature(
    *,
    record: GenerationRecord,
    expires_at: int | None,
    signature: str | None,
    settings: Settings,
) -> Path:
    zip_path = _validated_zip_path(record)
    if expires_at is None or signature is None:
        raise InvalidDownloadSignatureError("Signed download URL is missing required parameters.")
    if expires_at < int(time.time()):
        raise ExpiredDownloadSignatureError("Signed download URL has expired.")

    expected_signature = _sign(
        generation_id=record.generation_id,
        expires_at=expires_at,
        zip_path=zip_path,
        secret=settings.download_url_secret,
    )
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidDownloadSignatureError("Signed download URL is invalid.")

    return zip_path


def _validated_zip_path(record: GenerationRecord) -> Path:
    zip_path = record.zip_path.resolve(strict=True)
    output_dir = record.output_dir.resolve(strict=True)
    if zip_path.parent != output_dir:
        raise InvalidDownloadSignatureError("Stored download path is invalid.")
    if not zip_path.is_file():
        raise InvalidDownloadSignatureError("Stored download path is invalid.")
    return zip_path


def _sign(*, generation_id: str, expires_at: int, zip_path: Path, secret: str) -> str:
    payload = f"{generation_id}:{expires_at}:{zip_path.as_posix()}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
