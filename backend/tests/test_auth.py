"""API key authentication on protected routes."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_API_KEY

client = TestClient(app)


def test_health_does_not_require_api_key() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_does_not_require_api_key() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()


def test_generate_without_api_key_is_rejected(minimal_week_payload: dict[str, object]) -> None:
    response = client.post("/api/v1/carousels/generate", json=minimal_week_payload)
    assert response.status_code == 401


def test_generate_with_wrong_api_key_is_rejected(minimal_week_payload: dict[str, object]) -> None:
    response = client.post(
        "/api/v1/carousels/generate",
        json=minimal_week_payload,
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_generate_with_correct_key_header_name_but_case_insensitive() -> None:
    response = client.get("/api/v1/carousels/unknown-id", headers={"x-api-key": TEST_API_KEY})
    # Wrong key would 401; correct key + unknown id should 404, proving the
    # header was actually accepted case-insensitively (HTTP headers are).
    assert response.status_code == 404


def test_status_route_requires_api_key() -> None:
    response = client.get("/api/v1/carousels/unknown-id")
    assert response.status_code == 401


def test_download_route_without_signature_is_forbidden_even_without_api_key() -> None:
    response = client.get("/api/v1/carousels/unknown-id/download")
    assert response.status_code == 404


def test_download_route_with_valid_signature_does_not_require_api_key(
    minimal_week_payload: dict[str, object],
) -> None:
    generate_response = client.post(
        "/api/v1/carousels/generate",
        json=minimal_week_payload,
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert generate_response.status_code == 200

    download_url = generate_response.json()["download_url"]
    parsed = urlparse(download_url)
    query = parse_qs(parsed.query)

    download_response = client.get(f"{parsed.path}?exp={query['exp'][0]}&sig={query['sig'][0]}")

    assert download_response.status_code == 200
    assert download_response.status_code != 401
