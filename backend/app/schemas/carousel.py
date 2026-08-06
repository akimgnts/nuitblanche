"""Output schemas returned by the generation API."""

from __future__ import annotations

from pydantic import BaseModel


class FileDownloadResponse(BaseModel):
    index: int
    name: str
    download_url: str


class GenerationResponse(BaseModel):
    success: bool
    generation_id: str
    status: str
    slide_count: int
    download_url: str
    zip_download_url: str
    manifest_url: str
    files: list[str]
    file_downloads: list[FileDownloadResponse]
    warnings: list[str] = []


class GenerationStatusResponse(BaseModel):
    generation_id: str
    status: str
    slide_count: int
    city: str
    week_number: int
    files: list[str]
    warnings: list[str] = []


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None
