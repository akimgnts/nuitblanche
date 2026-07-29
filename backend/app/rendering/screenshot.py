"""Render HTML strings to PNG files using headless Chromium via Playwright."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType

from playwright.sync_api import Browser, Playwright, sync_playwright


class ScreenshotRenderer:
    """Reuses a single headless browser across all slides of one generation."""

    def __init__(self, width: int, height: int, executable_path: str | None = None) -> None:
        self._width = width
        self._height = height
        self._executable_path = executable_path
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def __enter__(self) -> ScreenshotRenderer:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            args=["--no-sandbox"], executable_path=self._executable_path
        )
        return self

    def capture(self, html: str, output_path: Path) -> None:
        if self._browser is None:
            raise RuntimeError("ScreenshotRenderer must be used as a context manager")
        page = self._browser.new_page(viewport={"width": self._width, "height": self._height})
        try:
            page.set_content(html, wait_until="networkidle")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(output_path),
                clip={"x": 0, "y": 0, "width": self._width, "height": self._height},
            )
        finally:
            page.close()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
