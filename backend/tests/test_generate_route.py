"""End-to-end generation route: request in, PNGs + ZIP out."""

from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_generation_service
from app.core.config import get_settings
from app.main import app
from app.models.generation import get_repository
from app.services.generation_service import GenerationService
from app.storage.local import LocalStorageProvider


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    class StubScreenshotRenderer:
        def __init__(self, width: int, height: int, executable_path: str | None = None) -> None:
            self._width = width
            self._height = height

        def __enter__(self) -> "StubScreenshotRenderer":
            return self

        def capture(self, html: str, output_path: Path) -> None:
            del html
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (self._width, self._height), "white").save(output_path)

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    settings = get_settings()
    storage = LocalStorageProvider(root_dir=tmp_path)
    service = GenerationService(settings=settings, storage=storage, repository=get_repository())
    app.dependency_overrides[get_generation_service] = lambda: service
    import app.services.generation_service as generation_service_module

    original_renderer = generation_service_module.ScreenshotRenderer
    generation_service_module.ScreenshotRenderer = StubScreenshotRenderer
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        generation_service_module.ScreenshotRenderer = original_renderer
        app.dependency_overrides.pop(get_generation_service, None)


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": get_settings().api_key}


def _query_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


def test_generate_returns_expected_shape(client: TestClient, minimal_week_payload: dict[str, object]) -> None:
    response = client.post("/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "completed"
    assert body["slide_count"] == 3  # cover + 1 day + outro
    assert body["files"] == ["01-cover.png", "02-jeudi.png", "03-fin.png"]
    assert isinstance(body["files"], list)
    parsed = urlparse(body["download_url"])
    query = _query_params(body["download_url"])
    assert parsed.scheme == "http"
    assert parsed.netloc == "testserver"
    assert parsed.path == f"/api/v1/carousels/{body['generation_id']}/download"
    assert "exp" in query
    assert "sig" in query
    assert body["zip_download_url"] == body["download_url"]
    manifest_parsed = urlparse(body["manifest_url"])
    assert manifest_parsed.path == f"/api/v1/carousels/{body['generation_id']}/files/manifest.json"
    assert "exp" in _query_params(body["manifest_url"])
    assert body["file_downloads"] == [
        {
            "index": 1,
            "name": "01-cover.png",
            "download_url": body["file_downloads"][0]["download_url"],
        },
        {
            "index": 2,
            "name": "02-jeudi.png",
            "download_url": body["file_downloads"][1]["download_url"],
        },
        {
            "index": 3,
            "name": "03-fin.png",
            "download_url": body["file_downloads"][2]["download_url"],
        },
    ]
    for expected_index, expected_name, file_download in zip((1, 2, 3), body["files"], body["file_downloads"]):
        assert file_download["index"] == expected_index
        assert file_download["name"] == expected_name
        file_url = urlparse(file_download["download_url"])
        assert file_url.path == f"/api/v1/carousels/{body['generation_id']}/files/{expected_name}"
        assert "exp" in _query_params(file_download["download_url"])
        assert "sig" in _query_params(file_download["download_url"])
    assert body["warnings"] == []


def test_generate_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post("/api/v1/carousels/generate", json={"city": "Le Havre"}, headers=_auth_headers())
    assert response.status_code == 422


def test_status_route_returns_generation_metadata(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    generation_id = generate_response.json()["generation_id"]

    status_response = client.get(f"/api/v1/carousels/{generation_id}", headers=_auth_headers())
    assert status_response.status_code == 200
    assert status_response.json()["city"] == "Le Havre"
    assert status_response.json()["week_number"] == 29


def test_generate_uses_iso_week_number_from_week_start_date(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    payload = {
        **minimal_week_payload,
        "week": {
            "label": "Semaine 1 – du 29/12/2025 au 04/01/2026",
            "startDate": "2025-12-29",
            "endDate": "2026-01-04",
        },
        "events": [
            {
                **minimal_week_payload["events"][0],
                "date": "2025-12-29",
                "dateLabel": "Lundi 29 décembre",
            }
        ],
    }

    generate_response = client.post(
        "/api/v1/carousels/generate", json=payload, headers=_auth_headers()
    )
    generation_id = generate_response.json()["generation_id"]

    status_response = client.get(f"/api/v1/carousels/{generation_id}", headers=_auth_headers())
    assert status_response.status_code == 200
    assert status_response.json()["week_number"] == 1


def test_generate_uses_default_city_when_env_not_set(
    client: TestClient, minimal_week_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NUIT_BLANCHE_CITY", raising=False)
    get_settings.cache_clear()

    response = client.post("/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers())
    generation_id = response.json()["generation_id"]

    status_response = client.get(f"/api/v1/carousels/{generation_id}", headers=_auth_headers())
    assert status_response.status_code == 200
    assert status_response.json()["city"] == "Le Havre"


def test_generate_uses_city_from_environment_override(
    client: TestClient, minimal_week_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NUIT_BLANCHE_CITY", "Rouen")
    get_settings.cache_clear()

    override_settings = get_settings()
    app.dependency_overrides[get_settings] = lambda: override_settings
    try:
        response = client.post("/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers())
    finally:
        app.dependency_overrides.pop(get_settings, None)
        monkeypatch.delenv("NUIT_BLANCHE_CITY", raising=False)
        get_settings.cache_clear()

    generation_id = response.json()["generation_id"]
    status_response = client.get(f"/api/v1/carousels/{generation_id}", headers=_auth_headers())
    assert status_response.status_code == 200
    assert status_response.json()["city"] == "Rouen"


def test_status_route_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/api/v1/carousels/does-not-exist", headers=_auth_headers())
    assert response.status_code == 404


def test_download_route_returns_a_valid_zip(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    download_url = generate_response.json()["download_url"]

    download_response = client.get(download_url)

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(download_response.content)) as archive:
        assert "01-cover.png" in archive.namelist()


def test_download_route_404_for_unknown_id(client: TestClient) -> None:
    response = client.get("/api/v1/carousels/does-not-exist/download?exp=1&sig=invalid")
    assert response.status_code == 404


def test_manifest_is_generated_and_downloadable(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    manifest_url = generate_response.json()["manifest_url"]

    manifest_response = client.get(manifest_url)

    assert manifest_response.status_code == 200
    manifest = json.loads(manifest_response.text)
    assert manifest["generation_id"] == generate_response.json()["generation_id"]
    assert manifest["week"] == "Semaine 29 – du 16/07/2026 au 22/07/2026"
    assert manifest["slide_count"] == 3
    assert manifest["slides"] == [
        {"index": 1, "filename": "01-cover.png"},
        {"index": 2, "filename": "02-jeudi.png"},
        {"index": 3, "filename": "03-fin.png"},
    ]


def test_png_download_route_returns_a_valid_png(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    png_url = generate_response.json()["file_downloads"][0]["download_url"]

    png_response = client.get(png_url)

    assert png_response.status_code == 200
    assert png_response.headers["content-type"] == "image/png"
    assert png_response.content.startswith(b"\x89PNG")


def test_download_route_rejects_missing_signature(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    generation_id = generate_response.json()["generation_id"]

    response = client.get(f"/api/v1/carousels/{generation_id}/download")

    assert response.status_code == 403


def test_file_download_route_rejects_invalid_signature(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    file_url = generate_response.json()["file_downloads"][0]["download_url"]
    parsed = urlparse(file_url)
    query = _query_params(file_url)

    response = client.get(f"{parsed.path}?exp={query['exp'][0]}&sig=invalid")

    assert response.status_code == 403


def test_download_route_rejects_invalid_signature(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    download_url = generate_response.json()["download_url"]
    parsed = urlparse(download_url)
    query = parse_qs(parsed.query)
    invalid_url = f"{parsed.path}?exp={query['exp'][0]}&sig=invalid"

    response = client.get(invalid_url)

    assert response.status_code == 403


def test_file_download_route_rejects_expired_signature(
    client: TestClient, minimal_week_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NUIT_BLANCHE_DOWNLOAD_URL_TTL_SECONDS", "-1")
    get_settings.cache_clear()
    expired_settings = get_settings()
    app.dependency_overrides[get_settings] = lambda: expired_settings
    try:
        generate_response = client.post(
            "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
        )
        file_url = generate_response.json()["file_downloads"][0]["download_url"]
        response = client.get(file_url)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        monkeypatch.delenv("NUIT_BLANCHE_DOWNLOAD_URL_TTL_SECONDS", raising=False)
        get_settings.cache_clear()

    assert response.status_code == 403


def test_download_route_rejects_expired_signature(
    client: TestClient, minimal_week_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NUIT_BLANCHE_DOWNLOAD_URL_TTL_SECONDS", "-1")
    get_settings.cache_clear()
    expired_settings = get_settings()
    app.dependency_overrides[get_settings] = lambda: expired_settings
    try:
        generate_response = client.post(
            "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
        )
        download_url = generate_response.json()["download_url"]
        response = client.get(download_url)
    finally:
        app.dependency_overrides.pop(get_settings, None)
        monkeypatch.delenv("NUIT_BLANCHE_DOWNLOAD_URL_TTL_SECONDS", raising=False)
        get_settings.cache_clear()

    assert response.status_code == 403


def test_file_download_route_404_for_missing_file(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    generation_id = generate_response.json()["generation_id"]

    response = client.get(f"/api/v1/carousels/{generation_id}/files/99-missing.png?exp=1&sig=invalid")

    assert response.status_code == 404


def test_file_download_route_rejects_path_traversal(
    client: TestClient, minimal_week_payload: dict[str, object]
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate", json=minimal_week_payload, headers=_auth_headers()
    )
    generation_id = generate_response.json()["generation_id"]

    response = client.get(f"/api/v1/carousels/{generation_id}/files/../secret.txt?exp=1&sig=invalid")

    assert response.status_code == 404


def test_generate_continues_when_poster_download_fails(
    client: TestClient, minimal_week_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.poster_assets.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("boom")),
    )
    payload = {
        **minimal_week_payload,
        "events": [
            {
                **minimal_week_payload["events"][0],
                "visualUrl": "https://example.com/poster.png",
            }
        ],
    }

    response = client.post("/api/v1/carousels/generate", json=payload, headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["files"] == ["01-cover.png", "02-jeudi.png", "03-fin.png"]


def test_generate_times_out_returns_504(minimal_week_payload: dict[str, object]) -> None:
    class SlowService:
        def generate(self, request: object) -> None:
            time.sleep(1)
            raise AssertionError("generation should have been abandoned by the timeout")

    fast_timeout_settings = get_settings().model_copy(update={"generation_timeout_seconds": 0})

    app.dependency_overrides[get_generation_service] = lambda: SlowService()
    app.dependency_overrides[get_settings] = lambda: fast_timeout_settings
    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/v1/carousels/generate",
                json=minimal_week_payload,
                headers={"X-API-Key": fast_timeout_settings.api_key},
            )
    finally:
        app.dependency_overrides.pop(get_generation_service, None)
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 504
