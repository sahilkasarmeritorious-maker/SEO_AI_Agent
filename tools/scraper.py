import base64
import time
from dataclasses import dataclass
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


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
        """Screenshot size in kilobytes."""
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


class PageScraper:
    """Async web scraper using Playwright."""
    
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        timeout_ms: int = 60000,  # ✅ CHANGED: 30s -> 60s
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

        self._playwright = None
        self._browser = None
        self._context = None

    async def start(self) -> "PageScraper":
        """Start async Playwright and launch browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport_w, "height": self.viewport_h},
            user_agent=self.user_agent,
        )
        return self

    async def stop(self) -> None:
        """Stop browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._context = None

    async def __aenter__(self) -> "PageScraper":
        """Async context manager entry."""
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Async context manager exit."""
        await self.stop()
        return False

    async def scrape(self, url: str) -> ScrapeResult:
        """Scrape a website asynchronously."""
        if not self._context:
            raise RuntimeError("Browser not started. Call scraper.start() first.")

        start_time = time.time()
        
        try:
            # Create a new page
            page = await self._context.new_page()
            
            try:
                # ADDED: Try networkidle first, fallback to load if timeout
                try:
                    await page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
                except PlaywrightTimeout:
                    # Fallback: use 'load' instead of 'networkidle' for slow websites
                    print(f"⚠️  networkidle timeout for {url}, retrying with 'load' condition...")
                    await page.goto(url, wait_until="load", timeout=30000)
                
                # Get title
                title = await page.title()
                
                # Get final URL (after redirects)
                final_url = page.url
                
                # Get HTML
                html = await page.content()
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
                
                # Wait a bit for any dynamic content
                await page.wait_for_timeout(self.wait_after_ms)
                
                load_time = (time.time() - start_time) * 1000
                
                return ScrapeResult(
                    url=url,
                    final_url=final_url,
                    status_code=200,
                    html=html,
                    title=title,
                    screenshot_bytes=screenshot_bytes,
                    screenshot_b64=screenshot_b64,
                    load_time_ms=load_time,
                    error=None,
                )
                
            finally:
                await page.close()
                
        except Exception as e:
            return ScrapeResult(
                url=url,
                final_url=url,
                status_code=0,
                html="",
                title="",
                screenshot_bytes=b"",
                screenshot_b64="",
                load_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )