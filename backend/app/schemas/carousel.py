"""Output schemas returned by the generation API."""

from __future__ import annotations

from pydantic import BaseModel


class GenerationResponse(BaseModel):
    generation_id: str
    status: str
    slide_count: int
    download_url: str
    files: list[str]
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
