"""FastAPI application entrypoint."""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.api.routes import carousels, health
from app.core.config import get_settings
from app.core.errors import NuitBlancheError, nuit_blanche_error_handler
from app.core.logging import configure_logging


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose declared Content-Length exceeds the configured limit."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > self._max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "detail": f"Le corps de la requête dépasse {self._max_bytes} octets.",
                },
            )
        return await call_next(request)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Nuit Blanche — Carousel Engine", version=settings.app_version)
    app.add_middleware(PayloadSizeLimitMiddleware, max_bytes=settings.max_payload_bytes)
    app.add_exception_handler(NuitBlancheError, nuit_blanche_error_handler)

    app.include_router(health.router)
    app.include_router(carousels.router)
    return app


app = create_app()
