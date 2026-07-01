from __future__ import annotations
import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any
from app.core.config import get_settings
from app.core.logging import get_logger
from app.scrapers.captcha import BaseCaptchaSolver, get_captcha_solver
from app.scrapers.proxy import ProxyPool, get_proxy_pool
from app.scrapers.schemas import ScrapedProduct
from app.scrapers.useragent import playwright_fingerprint

logger = get_logger(__name__)
settings = get_settings()


class ScraperError(Exception):
    """Raised when a scraper fails after all retries."""


class RateLimitError(ScraperError):
    """Raised on 429 / anti-bot block detection."""


class CaptchaError(ScraperError):
    """Raised when CAPTCHA cannot be solved."""


class BaseScraper(ABC):
    """
    Contract every marketplace scraper must implement.

    Lifecycle:
        async with ShopeeeScraper() as s:
            product = await s.scrape_product(external_id, url)
    """

    marketplace: str = ""

    def __init__(
        self,
        proxy_pool: ProxyPool | None = None,
        captcha_solver: BaseCaptchaSolver | None = None,
        max_retries: int | None = None,
        timeout: int | None = None,
    ):
        self.proxy_pool = proxy_pool or get_proxy_pool()
        self.captcha_solver = captcha_solver or get_captcha_solver()
        self.max_retries = max_retries or settings.max_retries
        self.timeout = timeout or settings.scrape_timeout_seconds
        self._request_count = 0
        self._last_request_time: float = 0.0

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def scrape_product(self, external_id: str, url: str | None = None) -> ScrapedProduct:
        """Scrape a single product. Must be idempotent."""
        ...

    @abstractmethod
    async def search_products(self, keyword: str, max_results: int = 20) -> list[ScrapedProduct]:
        """Search marketplace and return a list of product snapshots."""
        ...

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "BaseScraper":
        await self._setup()
        return self

    async def __aexit__(self, *_) -> None:
        await self._teardown()

    async def _setup(self) -> None:
        """Override to initialise browser / session."""

    async def _teardown(self) -> None:
        """Override to close browser / session."""

    # ── Retry decorator ───────────────────────────────────────────────────────

    async def _with_retry(self, coro_fn, *args, **kwargs) -> Any:
        """
        Executes an async callable with exponential backoff.
        Rotates proxy on each retry.
        """
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                await self._human_delay()
                result = await coro_fn(*args, **kwargs)
                self._request_count += 1
                return result
            except RateLimitError as e:
                logger.warning(
                    "rate_limit_hit",
                    marketplace=self.marketplace,
                    attempt=attempt,
                    wait=attempt * 10,
                )
                last_exc = e
                await asyncio.sleep(attempt * 10)
            except CaptchaError as e:
                logger.warning("captcha_encountered", marketplace=self.marketplace, attempt=attempt)
                last_exc = e
                await asyncio.sleep(5)
            except Exception as e:
                logger.warning(
                    "scrape_attempt_failed",
                    marketplace=self.marketplace,
                    attempt=attempt,
                    error=str(e),
                )
                last_exc = e
                backoff = min(2 ** attempt + random.uniform(0, 1), 60)
                await asyncio.sleep(backoff)

        raise ScraperError(
            f"{self.marketplace} scrape failed after {self.max_retries} retries"
        ) from last_exc

    # ── Human-like timing ─────────────────────────────────────────────────────

    async def _human_delay(self, min_s: float = 1.5, max_s: float = 4.5) -> None:
        """Random delay to mimic human browsing rhythm."""
        # Extra cool-down if we've been making requests rapidly
        since_last = time.time() - self._last_request_time
        if since_last < 1.0:
            await asyncio.sleep(1.0 - since_last)

        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)
        self._last_request_time = time.time()

    async def _human_scroll(self, page, pixels: int = 600) -> None:
        """Scroll in steps to trigger lazy-loaded content."""
        steps = random.randint(3, 7)
        step_size = pixels // steps
        for _ in range(steps):
            await page.mouse.wheel(0, step_size + random.randint(-20, 20))
            await asyncio.sleep(random.uniform(0.1, 0.4))

    async def _human_type(self, page, selector: str, text: str) -> None:
        """Type text character by character with random delays."""
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.18))

    # ── Anti-bot detection helpers ────────────────────────────────────────────

    @staticmethod
    def _is_blocked(html: str) -> bool:
        """Heuristic check for common anti-bot pages."""
        blocked_signals = [
            "access denied",
            "robot check",
            "unusual traffic",
            "verify you are human",
            "captcha",
            "blocked",
            "security check",
            "your ip",
        ]
        lower = html.lower()
        return any(sig in lower for sig in blocked_signals)

    @staticmethod
    def _inject_stealth_js() -> str:
        """
        JavaScript injected before page load to mask Playwright/Selenium signatures.
        Covers: navigator.webdriver, permissions API, plugin list, chrome object.
        """
        return """
        // Mask navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        // Fake plugins list
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        // Fake language
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
        });

        // Add chrome object if missing
        if (!window.chrome) {
            window.chrome = { runtime: {} };
        }

        // Override permissions
        const origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : origQuery(parameters);
        """
