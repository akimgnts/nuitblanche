"""Structured, non-sensitive error handling."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


class NuitBlancheError(Exception):
    """Base class for domain errors that map to a clean HTTP response."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class GenerationNotFoundError(NuitBlancheError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "generation_not_found"


class GenerationTimeoutError(NuitBlancheError):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    error_code = "generation_timeout"


class PayloadTooLargeError(NuitBlancheError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code = "payload_too_large"


async def nuit_blanche_error_handler(request: Request, exc: NuitBlancheError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "detail": exc.detail, "request_id": request.headers.get("x-request-id")},
    )
