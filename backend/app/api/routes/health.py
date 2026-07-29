"""Liveness and version endpoints. No authentication required."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
def version(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    return {"version": settings.app_version}
