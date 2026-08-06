"""Helpers for signing and validating public download URLs."""

from __future__ import annotations

import hmac
import time
from hashlib import sha256
from pathlib import Path

from fastapi import Request

from app.core.config import Settings
from app.core.errors import ExpiredDownloadSignatureError, InvalidDownloadSignatureError


def build_signed_route_url(
    *,
    request: Request,
    route_name: str,
    generation_id: str,
    stored_path: Path,
    settings: Settings,
    **path_params: str,
) -> str:
    resolved_path = validate_generation_path(path=stored_path, output_dir=stored_path.parent)
    expires_at = int(time.time()) + settings.download_url_ttl_seconds
    signature = _sign(
        generation_id=generation_id,
        expires_at=expires_at,
        stored_path=resolved_path,
        secret=settings.download_url_secret,
    )
    return str(
        request.url_for(route_name, generation_id=generation_id, **path_params).include_query_params(
            exp=expires_at,
            sig=signature,
        )
    )


def verify_signed_path(
    *,
    generation_id: str,
    stored_path: Path,
    output_dir: Path,
    expires_at: int | None,
    signature: str | None,
    settings: Settings,
) -> Path:
    resolved_path = validate_generation_path(path=stored_path, output_dir=output_dir)
    if expires_at is None or signature is None:
        raise InvalidDownloadSignatureError("Signed download URL is missing required parameters.")
    if expires_at < int(time.time()):
        raise ExpiredDownloadSignatureError("Signed download URL has expired.")

    expected_signature = _sign(
        generation_id=generation_id,
        expires_at=expires_at,
        stored_path=resolved_path,
        secret=settings.download_url_secret,
    )
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidDownloadSignatureError("Signed download URL is invalid.")

    return resolved_path


def validate_generation_path(*, path: Path, output_dir: Path) -> Path:
    resolved_path = path.resolve(strict=True)
    resolved_output_dir = output_dir.resolve(strict=True)
    if resolved_path.parent != resolved_output_dir:
        raise InvalidDownloadSignatureError("Stored download path is invalid.")
    if not resolved_path.is_file():
        raise InvalidDownloadSignatureError("Stored download path is invalid.")
    return resolved_path


def _sign(*, generation_id: str, expires_at: int, stored_path: Path, secret: str) -> str:
    payload = f"{generation_id}:{expires_at}:{stored_path.as_posix()}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
