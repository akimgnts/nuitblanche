"""Render HTML strings to PNG files using headless Chromium via Playwright."""

from __future__ import annotations

import logging
from pathlib import Path
from types import TracebackType

from playwright.sync_api import Browser, Playwright, sync_playwright

ASSET_LOAD_TIMEOUT_MS = 8_000
LAYOUT_SETTLE_DELAY_MS = 300

logger = logging.getLogger(__name__)


def _wait_for_visible_assets(page: object, timeout_ms: int = ASSET_LOAD_TIMEOUT_MS) -> list[str]:
    return page.evaluate(
        """
        async ({ timeoutMs }) => {
          const deadline = Date.now() + timeoutMs;
          const remaining = () => Math.max(0, deadline - Date.now());
          const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
          const isVisible = (img) => {
            const style = window.getComputedStyle(img);
            return img.getClientRects().length > 0 && style.display !== "none" && style.visibility !== "hidden";
          };

          if (document.fonts && document.fonts.ready) {
            await Promise.race([
              document.fonts.ready.catch(() => undefined),
              wait(remaining()),
            ]);
          }

          const waitForImage = (img) =>
            new Promise((resolve) => {
              if (img.complete) {
                resolve(img.naturalWidth > 0);
                return;
              }

              const finalize = (loaded) => {
                img.removeEventListener("load", onLoad);
                img.removeEventListener("error", onError);
                clearTimeout(timer);
                resolve(loaded);
              };
              const onLoad = () => finalize(img.naturalWidth > 0);
              const onError = () => finalize(false);
              const timer = setTimeout(
                () => finalize(img.complete && img.naturalWidth > 0),
                remaining(),
              );

              img.addEventListener("load", onLoad, { once: true });
              img.addEventListener("error", onError, { once: true });
            });

          const failures = [];
          const images = Array.from(document.images).filter(isVisible);
          await Promise.all(
            images.map(async (img) => {
              const loaded = await waitForImage(img);
              if (!loaded) {
                failures.push(img.currentSrc || img.src || "");
              }
            }),
          );
          return failures.filter(Boolean);
        }
        """,
        {"timeoutMs": timeout_ms},
    )


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
            failed_images = _wait_for_visible_assets(page)
            for failed_url in failed_images:
                logger.warning("Image failed to load before screenshot: %s", failed_url)
            page.wait_for_timeout(LAYOUT_SETTLE_DELAY_MS)
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
