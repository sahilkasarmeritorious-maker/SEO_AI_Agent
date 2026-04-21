import base64
import time
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# =============================================================================
# DATA CLASS — ScrapeResult
# =============================================================================
# A dataclass is a clean way to group related return values.
# Instead of returning a raw dict (where keys can be misspelled and there's
# no type info), we return a typed object. Every field is documented below.

@dataclass
class ScrapeResult:
    url: str
    final_url: str
    status_code: int
    html: str
    title: str
    screenshot_bytes: bytes
    screenshot_b64: str
    load_time_ms: float
    error: str | None = None

    @property
    def success(self) -> bool:
        """Convenience property — True if scrape succeeded with no error."""
        return self.error is None and len(self.html) > 0

    @property
    def screenshot_size_kb(self) -> float:
        """Screenshot size in kilobytes — useful for logging."""
        return round(len(self.screenshot_bytes) / 1024, 2)

    def save_screenshot(self, path: str) -> None:
        """Save the screenshot PNG to a file path on disk."""
        with open(path, "wb") as f:
            f.write(self.screenshot_bytes)

    def save_html(self, path: str) -> None:
        """Save the rendered HTML to a file path on disk."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.html)

    def summary(self) -> dict:

        return {
            "url": self.url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "title": self.title,
            "load_time_ms": self.load_time_ms,
            "html_length_chars": len(self.html),
            "screenshot_size_kb": self.screenshot_size_kb,
            "success": self.success,
            "error": self.error,
        }


# =============================================================================
# MAIN CLASS — PageScraper
# =============================================================================

class PageScraper:
    # Class-level constant — shared across all instances.
    # Mimics a real Chrome browser on macOS to avoid bot-detection blocks.
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        timeout_ms: int = 30000,
        viewport_w: int = 1440,
        viewport_h: int = 900,
        user_agent: str = None,
        wait_after_ms: int = 1500,
    ):
        self.timeout_ms = timeout_ms
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.wait_after_ms = wait_after_ms

        # Private attributes (prefix _ = internal use only).
        # These are None until start() is called.
        self._playwright = None   # the Playwright driver instance
        self._browser = None      # the Chromium browser instance
        self._context = None      # browser context (isolated session, like incognito)

    # -------------------------------------------------------------------------
    # LIFECYCLE METHODS
    # -------------------------------------------------------------------------

    def start(self) -> "PageScraper":
        # sync_playwright() is Playwright's synchronous API entry point.
        # .start() boots the Playwright server process that controls browsers.
        self._playwright = sync_playwright().start()

        # Launch Chromium in headless mode (no visible browser window).
        # headless=True is required in server/Docker/CI environments.
        self._browser = self._playwright.chromium.launch(headless=True)

        # new_context() creates an isolated browser session.
        # Think of it as a fresh incognito window — no cookies, no cache,
        # no state carried over from previous scrapes.
        # This ensures consistent results across different URLs.
        self._context = self._browser.new_context(
            viewport={"width": self.viewport_w, "height": self.viewport_h},
            user_agent=self.user_agent,
        )

        return self

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._context = None

    # -------------------------------------------------------------------------
    # CONTEXT MANAGER PROTOCOL  (__enter__ / __exit__)
    # -------------------------------------------------------------------------
    # These two dunder methods allow the class to work with Python's 'with'
    # statement, which is the cleanest way to manage resources that need
    # explicit cleanup (file handles, DB connections, browsers, etc.)

    def __enter__(self) -> "PageScraper":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.stop()
        return False

    # -------------------------------------------------------------------------
    # CORE METHOD — scrape()
    # -------------------------------------------------------------------------

    def scrape(self, url: str) -> ScrapeResult:
        if not self._context:
            raise RuntimeError(
                "Browser not started. Use 'with PageScraper() as scraper:' "
                "or call scraper.start() first."
            )

        # new_page() opens a fresh browser tab within our context
        page = self._context.new_page()

        # We'll capture HTTP status via Playwright's response event system.
        # nonlocal lets our callback modify variables in the outer scope.
        status_code = 0
        final_url = url

        def _on_response(response):
            nonlocal status_code, final_url
            if response.url == page.url or final_url == url:
                status_code = response.status
                final_url = response.url

        # page.on() registers our callback to the "response" event stream.
        # Every time any HTTP response comes in, _on_response is called.
        page.on("response", _on_response)

        try:
            start_time = time.time()

            # page.goto() navigates to the URL.
            # wait_until="networkidle": Playwright waits until there have been
            # no network connections for at least 500ms — meaning the page
            # and all its resources (JS, CSS, API calls) have finished loading.
            # timeout=self.timeout_ms: raises PlaywrightTimeout if exceeded.
            page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)

            load_time_ms = (time.time() - start_time) * 1000

            # Extra pause for JS frameworks (React, Vue, Next.js, etc.).
            # These often continue rendering components after networkidle.
            # 1500ms is a safe buffer for most frameworks.
            page.wait_for_timeout(self.wait_after_ms)

            # page.content() returns the full DOM as an HTML string.
            # This is the RENDERED HTML — dynamic content is included.
            html = page.content()

            # page.title() reads the current document.title value
            title = page.title()

            # page.url gives the final URL after any 301/302 redirects
            final_url = page.url

            # full_page=True stitches together the entire scrollable height,
            # not just the visible viewport (above the fold).
            # Returns raw PNG bytes.
            screenshot_bytes = page.screenshot(full_page=True)

            # base64 encoding converts binary PNG bytes into a text string.
            # Vision LLMs expect images as base64-encoded strings inside
            # the API request JSON body.
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            page.close()

            return ScrapeResult(
                url=url,
                final_url=final_url,
                status_code=status_code or 200,
                html=html,
                title=title,
                screenshot_bytes=screenshot_bytes,
                screenshot_b64=screenshot_b64,
                load_time_ms=round(load_time_ms, 2),
                error=None,
            )

        except PlaywrightTimeout:
            page.close()
            return ScrapeResult(
                url=url, final_url=final_url, status_code=0,
                html="", title="", screenshot_bytes=b"", screenshot_b64="",
                load_time_ms=0,
                error=f"Timeout: page did not finish loading within {self.timeout_ms}ms",
            )

        except Exception as e:
            # Catches DNS failures, SSL errors, invalid URLs, network errors, etc.
            page.close()
            return ScrapeResult(
                url=url, final_url=final_url, status_code=0,
                html="", title="", screenshot_bytes=b"", screenshot_b64="",
                load_time_ms=0,
                error=f"{type(e).__name__}: {str(e)}",
            )


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    import sys
    import json

    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(f"\n🌐  Scraping: {target}")
    print("-" * 55)

    with PageScraper(timeout_ms=30000) as scraper:
        result = scraper.scrape(target)

    if not result.success:
        print(f"❌  Error: {result.error}")
        sys.exit(1)

    result.save_screenshot("/tmp/scraped_screenshot.png")
    result.save_html("/tmp/scraped_page.html")

    print(json.dumps(result.summary(), indent=2))
    print(f"\n📸  Screenshot → /tmp/scraped_screenshot.png")
    print(f"📄  HTML       → /tmp/scraped_page.html")