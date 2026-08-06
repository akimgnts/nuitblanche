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
from app.schemas.carousel import FileDownloadResponse, GenerationResponse, GenerationStatusResponse
from app.schemas.events import WeekRequest
from app.services.download_urls import build_signed_route_url, verify_signed_path
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

    zip_download_url = _build_zip_download_url(http_request, record, settings)
    return GenerationResponse(
        success=True,
        generation_id=record.generation_id,
        status=record.status,
        slide_count=record.slide_count,
        download_url=zip_download_url,
        zip_download_url=zip_download_url,
        manifest_url=_build_file_download_url(http_request, record, record.manifest_path.name, settings),
        files=record.files,
        file_downloads=[
            FileDownloadResponse(
                index=index,
                name=path.name,
                download_url=_build_file_download_url(http_request, record, path.name, settings),
            )
            for index, path in enumerate(record.slide_paths, start=1)
        ],
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

    zip_path = _verify_download(
        generation_id=generation_id,
        path=record.zip_path,
        output_dir=record.output_dir,
        exp=exp,
        sig=sig,
        settings=settings,
    )

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_path.name,
    )


@public_router.get("/{generation_id}/files/{filename:path}")
def download_generation_file(
    generation_id: str,
    filename: str,
    repository: Annotated[GenerationRepository, Depends(get_generation_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    exp: Annotated[int | None, Query()] = None,
    sig: Annotated[str | None, Query()] = None,
) -> FileResponse:
    record = repository.get(generation_id)
    if record is None:
        raise GenerationNotFoundError(f"Aucune génération trouvée pour {generation_id}")

    path = _resolve_generation_file(record, filename)
    signed_path = _verify_download(
        generation_id=generation_id,
        path=path,
        output_dir=record.output_dir,
        exp=exp,
        sig=sig,
        settings=settings,
    )
    return FileResponse(
        path=signed_path,
        filename=signed_path.name,
    )


def _build_zip_download_url(request: Request, record: GenerationRecord, settings: Settings) -> str:
    return build_signed_route_url(
        request=request,
        route_name="download_generation",
        generation_id=record.generation_id,
        stored_path=record.zip_path,
        settings=settings,
    )


def _build_file_download_url(request: Request, record: GenerationRecord, filename: str, settings: Settings) -> str:
    path = _resolve_generation_file(record, filename)
    return build_signed_route_url(
        request=request,
        route_name="download_generation_file",
        generation_id=record.generation_id,
        stored_path=path,
        settings=settings,
        filename=filename,
    )


def _resolve_generation_file(record: GenerationRecord, filename: str) -> Path:
    if not filename or "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise GenerationNotFoundError("Le fichier demandé est introuvable.")
    if filename == record.manifest_path.name:
        return record.manifest_path
    slide_path = record.slide_path_for(filename)
    if slide_path is None:
        raise GenerationNotFoundError("Le fichier demandé est introuvable.")
    return slide_path


def _verify_download(
    *,
    generation_id: str,
    path: Path,
    output_dir: Path,
    exp: int | None,
    sig: str | None,
    settings: Settings,
) -> Path:
    try:
        return verify_signed_path(
            generation_id=generation_id,
            stored_path=path,
            output_dir=output_dir,
            expires_at=exp,
            signature=sig,
            settings=settings,
        )
    except FileNotFoundError as exc:
        raise GenerationNotFoundError("Le fichier demandé est introuvable.") from exc


router.include_router(protected_router)
router.include_router(public_router)
