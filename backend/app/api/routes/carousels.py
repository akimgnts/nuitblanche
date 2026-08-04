"""Carousel generation routes. All require a valid X-API-Key."""

from __future__ import annotations

import concurrent.futures
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.deps import get_generation_repository, get_generation_service
from app.core.config import Settings, get_settings
from app.core.errors import GenerationNotFoundError, GenerationTimeoutError
from app.core.security import verify_api_key
from app.models.generation import GenerationRepository
from app.schemas.carousel import GenerationResponse, GenerationStatusResponse
from app.schemas.events import WeekRequest
from app.services.generation_service import GenerationService
from app.services.payload_adapter import to_generation_request

router = APIRouter(prefix="/api/v1/carousels", tags=["carousels"], dependencies=[Depends(verify_api_key)])

# Dedicated pool so a slow generation can be time-boxed independently of
# FastAPI's own worker threads.
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="carousel-gen")


@router.post("/generate", response_model=GenerationResponse)
def generate_carousel(
    request: WeekRequest,
    service: Annotated[GenerationService, Depends(get_generation_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerationResponse:
    internal_request = to_generation_request(request, settings)
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
        download_url=f"/api/v1/carousels/{record.generation_id}/download",
        files=record.files,
        warnings=record.warnings,
    )


@router.get("/{generation_id}", response_model=GenerationStatusResponse)
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


@router.get("/{generation_id}/download")
def download_generation(
    generation_id: str,
    repository: Annotated[GenerationRepository, Depends(get_generation_repository)],
) -> FileResponse:
    record = repository.get(generation_id)
    if record is None:
        raise GenerationNotFoundError(f"Aucune génération trouvée pour {generation_id}")
    return FileResponse(
        path=record.zip_path,
        media_type="application/zip",
        filename=record.zip_path.name,
    )
