"""Shared FastAPI dependencies: settings, storage provider, repository, service."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.models.generation import GenerationRepository, get_repository
from app.services.generation_service import GenerationService
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider


@lru_cache(maxsize=1)
def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    return LocalStorageProvider(root_dir=settings.generated_dir)


def get_generation_service() -> GenerationService:
    return GenerationService(
        settings=get_settings(),
        storage=get_storage_provider(),
        repository=get_repository(),
    )


def get_generation_repository() -> GenerationRepository:
    return get_repository()
