"""Download remote poster images and convert them to local data URLs."""

from __future__ import annotations

import base64
import logging
import mimetypes
import socket
from dataclasses import replace
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.filenames import slugify
from app.services.normalizer import NormalizedEvent

POSTER_DOWNLOAD_TIMEOUT_SECONDS = 8

logger = logging.getLogger(__name__)

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def localize_poster_assets(
    events: list[NormalizedEvent],
    *,
    generation_id: str,
    assets_dir: Path,
    timeout_seconds: int = POSTER_DOWNLOAD_TIMEOUT_SECONDS,
) -> list[NormalizedEvent]:
    del generation_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    localized_events: list[NormalizedEvent] = []
    for event in events:
        if not event.poster_url or event.poster_url.startswith("data:"):
            localized_events.append(event)
            continue

        poster_data_url = _download_poster_as_data_url(
            event_id=event.external_id,
            source_url=event.poster_url,
            assets_dir=assets_dir,
            timeout_seconds=timeout_seconds,
        )
        localized_events.append(replace(event, poster_url=poster_data_url))
    return localized_events


def _download_poster_as_data_url(
    *,
    event_id: str,
    source_url: str,
    assets_dir: Path,
    timeout_seconds: int,
) -> str | None:
    request = Request(source_url, headers={"User-Agent": "NuitBlancheBot/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", response.getcode())
            content_type_header = response.headers.get("Content-Type", "")
            content_type = content_type_header.split(";", 1)[0].strip().lower()
            if status != 200 or not content_type.startswith("image/"):
                _log_failure(
                    event_id=event_id,
                    source_url=source_url,
                    status=status,
                    content_type=content_type,
                    reason="invalid response",
                )
                return None
            body = response.read()
    except HTTPError as exc:
        _log_failure(
            event_id=event_id,
            source_url=source_url,
            status=exc.code,
            content_type=exc.headers.get("Content-Type", ""),
            reason="http error",
        )
        return None
    except (URLError, TimeoutError, socket.timeout) as exc:
        _log_failure(
            event_id=event_id,
            source_url=source_url,
            status=None,
            content_type=None,
            reason=f"network error: {exc}",
        )
        return None

    extension = _extension_for_content_type(content_type)
    asset_path = assets_dir / f"{slugify(event_id)}{extension}"
    asset_path.write_bytes(body)
    encoded = base64.b64encode(body).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _extension_for_content_type(content_type: str) -> str:
    if content_type in _CONTENT_TYPE_EXTENSIONS:
        return _CONTENT_TYPE_EXTENSIONS[content_type]
    guessed = mimetypes.guess_extension(content_type, strict=False)
    if guessed == ".jpe":
        return ".jpg"
    return guessed or ".img"


def _log_failure(
    *,
    event_id: str,
    source_url: str,
    status: int | None,
    content_type: str | None,
    reason: str,
) -> None:
    logger.warning(
        "Poster download failed: event_id=%s url=%s status=%s content_type=%s reason=%s",
        event_id,
        source_url,
        status,
        content_type,
        reason,
    )
