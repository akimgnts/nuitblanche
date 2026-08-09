"""Targeted tests for Playwright asset waiting before screenshots."""

from __future__ import annotations

import logging
from pathlib import Path

from app.rendering.screenshot import LAYOUT_SETTLE_DELAY_MS, ScreenshotRenderer


class FakePage:
    def __init__(self, failed_images: list[str] | None = None) -> None:
        self.failed_images = failed_images or []
        self.calls: list[tuple[str, object]] = []

    def set_content(self, html: str, wait_until: str) -> None:
        self.calls.append(("set_content", {"html": html, "wait_until": wait_until}))

    def evaluate(self, script: str, params: dict[str, int]) -> list[str]:
        self.calls.append(("evaluate", {"script": script, "params": params}))
        return list(self.failed_images)

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.calls.append(("wait_for_timeout", timeout_ms))

    def screenshot(self, path: str, clip: dict[str, int]) -> None:
        self.calls.append(("screenshot", {"path": path, "clip": clip}))

    def close(self) -> None:
        self.calls.append(("close", None))


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def new_page(self, viewport: dict[str, int]) -> FakePage:
        self.page.calls.append(("new_page", viewport))
        return self.page


def test_capture_waits_for_assets_before_screenshot(tmp_path: Path) -> None:
    page = FakePage()
    renderer = ScreenshotRenderer(width=1080, height=1350)
    renderer._browser = FakeBrowser(page)  # type: ignore[assignment]

    renderer.capture("<html><body><img src='https://example.com/poster.png'></body></html>", tmp_path / "out.png")

    ordered_calls = [name for name, _ in page.calls]
    assert ordered_calls == [
        "new_page",
        "set_content",
        "evaluate",
        "wait_for_timeout",
        "screenshot",
        "close",
    ]
    assert page.calls[2][1]["params"]["timeoutMs"] > 0
    assert page.calls[3] == ("wait_for_timeout", LAYOUT_SETTLE_DELAY_MS)


def test_capture_logs_failed_image_urls(tmp_path: Path, caplog: object) -> None:
    page = FakePage(failed_images=["https://drive.google.com/uc?export=view&id=broken"])
    renderer = ScreenshotRenderer(width=1080, height=1350)
    renderer._browser = FakeBrowser(page)  # type: ignore[assignment]

    with caplog.at_level(logging.WARNING):
        renderer.capture("<html></html>", tmp_path / "out.png")

    assert "Image failed to load before screenshot" in caplog.text
    assert "https://drive.google.com/uc?export=view&id=broken" in caplog.text
