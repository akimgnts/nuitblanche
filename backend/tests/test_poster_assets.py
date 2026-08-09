"""Poster asset download and fallback behavior."""

from __future__ import annotations

import base64
import logging
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

from app.schemas.events import EventIn
from app.services.normalizer import normalize_event
from app.services.poster_assets import localize_poster_assets

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlH0P0AAAAASUVORK5CYII="
)


def _event(url: str | None) -> object:
    return normalize_event(
        EventIn.model_validate(
            {
                "id": "EVT-0001",
                "date": "2026-07-16",
                "dateLabel": "Jeudi 16 juillet",
                "venue": "3 Brasseurs",
                "type": "Concert",
                "eventName": "Concert variétés",
                "visualUrl": url,
            }
        )
    )


@contextmanager
def _poster_server() -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/image":
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(PNG_BYTES)
                return
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/image")
                self.end_headers()
                return
            if self.path == "/text":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"not an image")
                return
            if self.path == "/slow":
                time.sleep(0.2)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                self.wfile.write(PNG_BYTES)
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()


def test_localize_poster_assets_downloads_drive_image(tmp_path: Path) -> None:
    with _poster_server() as base_url:
        localized = localize_poster_assets(
            [_event(f"{base_url}/image")],
            generation_id="gen-1",
            assets_dir=tmp_path / "assets",
        )

    assert localized[0].poster_url.startswith("data:image/png;base64,")
    assert [path.name for path in (tmp_path / "assets").iterdir()] == ["evt-0001.png"]


def test_localize_poster_assets_follows_redirects(tmp_path: Path) -> None:
    with _poster_server() as base_url:
        localized = localize_poster_assets(
            [_event(f"{base_url}/redirect")],
            generation_id="gen-1",
            assets_dir=tmp_path / "assets",
        )

    assert localized[0].poster_url.startswith("data:image/png;base64,")


def test_localize_poster_assets_rejects_bad_content_type(tmp_path: Path, caplog: object) -> None:
    with _poster_server() as base_url:
        with caplog.at_level(logging.WARNING):
            localized = localize_poster_assets(
                [_event(f"{base_url}/text")],
                generation_id="gen-1",
                assets_dir=tmp_path / "assets",
            )

    assert localized[0].poster_url is None
    assert "content_type=text/plain" in caplog.text


def test_localize_poster_assets_rejects_404(tmp_path: Path, caplog: object) -> None:
    with _poster_server() as base_url:
        with caplog.at_level(logging.WARNING):
            localized = localize_poster_assets(
                [_event(f"{base_url}/missing")],
                generation_id="gen-1",
                assets_dir=tmp_path / "assets",
            )

    assert localized[0].poster_url is None
    assert "status=404" in caplog.text


def test_localize_poster_assets_rejects_timeout(
    tmp_path: Path, monkeypatch: object, caplog: object
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise socket.timeout("timed out")

    monkeypatch.setattr("app.services.poster_assets.urlopen", raise_timeout)
    with caplog.at_level(logging.WARNING):
        localized = localize_poster_assets(
            [_event("https://example.com/poster.png")],
            generation_id="gen-1",
            assets_dir=tmp_path / "assets",
        )

    assert localized[0].poster_url is None
    assert "network error: timed out" in caplog.text
