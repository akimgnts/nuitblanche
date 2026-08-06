"""Carousel generation routes."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from app.api.deps import get_generation_repository, get_generation_service
from app.core.config import Settings, get_settings
from app.core.errors import GenerationNotFoundError, GenerationTimeoutError
from app.core.security import verify_api_key
from app.models.generation import GenerationRecord, GenerationRepository
from app.schemas.carousel import GenerationResponse, GenerationStatusResponse
from app.schemas.events import WeekRequest
from app.services.download_urls import build_download_url, verify_download_signature
from app.services.generation_service import GenerationService
from app.services.payload_adapter import to_generation_request

router = APIRouter(tags=["carousels"])
protected_router = APIRouter(prefix="/api/v1/carousels", dependencies=[Depends(verify_api_key)])
public_router = APIRouter(prefix="/api/v1/carousels")

# Dedicated pool so a slow generation can be time-boxed independently of
# FastAPI's own worker threads.
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="carousel-gen")


@protected_router.post("/generate", response_model=GenerationResponse)
def generate_carousel(
    payload: WeekRequest,
    http_request: Request,
    service: Annotated[GenerationService, Depends(get_generation_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerationResponse:
    internal_request = to_generation_request(payload, settings)
    future = _executor.submit(service.generate, internal_request)
    try:
        record = future.result(timeout=settings.generation_timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise GenerationTimeoutError(
            f"La génération a dépassé le délai de {settings.generation_timeout_seconds}s."
        ) from exc

    return GenerationResponse(
        generation_id=record.generation_id,
        status=record.status,
        slide_count=record.slide_count,
        download_url=build_download_url(request=http_request, record=record, settings=settings),
        files=record.files,
        warnings=record.warnings,
    )


@protected_router.get("/{generation_id}", response_model=GenerationStatusResponse)
def get_generation(
    generation_id: str,
    repository: Annotated[GenerationRepository, Depends(get_generation_repository)],
) -> GenerationStatusResponse:
    record = repository.get(generation_id)
    if record is None:
        raise GenerationNotFoundError(f"Aucune génération trouvée pour {generation_id}")
    return GenerationStatusResponse(
        generation_id=record.generation_id,
        status=record.status,
        slide_count=record.slide_count,
        city=record.city,
        week_number=record.week_number,
        files=record.files,
        warnings=record.warnings,
    )


@public_router.get("/{generation_id}/download")
def download_generation(
    generation_id: str,
    repository: Annotated[GenerationRepository, Depends(get_generation_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    exp: Annotated[int | None, Query()] = None,
    sig: Annotated[str | None, Query()] = None,
) -> FileResponse:
    record = repository.get(generation_id)
    if record is None:
        raise GenerationNotFoundError(f"Aucune génération trouvée pour {generation_id}")

    zip_path = _resolve_download_path(record.zip_path)
    record_zip_path = _resolve_download_path(record.output_dir / record.zip_path.name)
    if zip_path != record_zip_path:
        raise GenerationNotFoundError(f"Aucune génération trouvée pour {generation_id}")

    signed_zip_path = _verify_download(record=record, exp=exp, sig=sig, settings=settings)
    if signed_zip_path != zip_path:
        raise GenerationNotFoundError(f"Aucune génération trouvée pour {generation_id}")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_path.name,
    )


def _resolve_download_path(path: Path) -> Path:
    try:
        return path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise GenerationNotFoundError("Le fichier ZIP demandé est introuvable.") from exc


def _verify_download(
    *,
    record: GenerationRecord,
    exp: int | None,
    sig: str | None,
    settings: Settings,
) -> Path:
    try:
        return verify_download_signature(
            record=record,
            expires_at=exp,
            signature=sig,
            settings=settings,
        )
    except FileNotFoundError as exc:
        raise GenerationNotFoundError("Le fichier ZIP demandé est introuvable.") from exc


router.include_router(protected_router)
router.include_router(public_router)
