from __future__ import annotations
import json
import re
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PWTimeout
from app.core.logging import get_logger
from app.scrapers.base import BaseScraper, RateLimitError, CaptchaError
from app.scrapers.factory import register
from app.scrapers.schemas import ScrapedProduct, ScrapedSeller
from app.scrapers.useragent import playwright_fingerprint

logger = get_logger(__name__)

# Shopee API endpoints (reverse-engineered from browser network tab)
SHOPEE_API_ITEM = "https://shopee.com.br/api/v4/item/get?itemid={item_id}&shopid={shop_id}"
SHOPEE_API_SEARCH = "https://shopee.com.br/api/v4/search/search_items?by=relevancy&keyword={keyword}&limit={limit}&newest=0&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2"
SHOPEE_PRODUCT_URL = "https://shopee.com.br/{slug}-i.{shop_id}.{item_id}"


@register("shopee")
class ShopeeScraper(BaseScraper):
    """
    Shopee scraper using Playwright (headful optional) + API interception.

    Strategy:
    1. Primary: intercept Shopee's internal JSON API — fast, structured, no parsing fragility.
    2. Fallback: DOM parsing for data not in API response.
    3. Anti-bot: stealth JS injection, fingerprint rotation, human-like behaviour.
    """

    marketplace = "shopee"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._playwright = None
        self._browser: Browser | None = None

    async def _setup(self) -> None:
        self._playwright = await async_playwright().start()
        proxy = self.proxy_pool.get_next()
        launch_kwargs = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        }
        if proxy:
            launch_kwargs["proxy"] = proxy.to_playwright_dict()

        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        logger.info("shopee_browser_started", proxy=proxy.host if proxy else "direct")

    async def _teardown(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _new_context(self) -> BrowserContext:
        fp = playwright_fingerprint("chrome")
        ctx = await self._browser.new_context(**fp)
        # Inject stealth JS on every new document
        await ctx.add_init_script(self._inject_stealth_js())
        # Block images/fonts/media to speed up loads
        await ctx.route(
            "**/*.{png,jpg,jpeg,gif,svg,webp,ico,woff,woff2,ttf,otf,mp4,webm}",
            lambda route: route.abort(),
        )
        return ctx

    # ── Public interface ──────────────────────────────────────────────────────

    async def scrape_product(self, external_id: str, url: str | None = None) -> ScrapedProduct:
        """
        external_id format: "{shop_id}.{item_id}"  e.g. "12345.67890"
        """
        return await self._with_retry(self._do_scrape_product, external_id, url)

    async def search_products(self, keyword: str, max_results: int = 20) -> list[ScrapedProduct]:
        return await self._with_retry(self._do_search, keyword, max_results)

    # ── Internal implementation ───────────────────────────────────────────────

    async def _do_scrape_product(self, external_id: str, url: str | None) -> ScrapedProduct:
        parts = external_id.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid Shopee external_id format: '{external_id}'. Expected 'shop_id.item_id'")

        shop_id, item_id = parts
        api_url = SHOPEE_API_ITEM.format(shop_id=shop_id, item_id=item_id)

        async with await self._new_context() as ctx:
            page: Page = await ctx.new_page()
            api_data: dict = {}

            # Intercept the product API call
            async def capture_api(response):
                if f"item/get?itemid={item_id}" in response.url:
                    try:
                        body = await response.json()
                        api_data.update(body)
                    except Exception:
                        pass

            page.on("response", capture_api)

            # Navigate to product page (triggers the API call)
            product_url = url or SHOPEE_PRODUCT_URL.format(
                slug="product", shop_id=shop_id, item_id=item_id
            )
            try:
                await page.goto(product_url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            except PWTimeout:
                logger.warning("shopee_page_timeout", url=product_url)

            # Check for blocks / CAPTCHA
            content = await page.content()
            if self._is_blocked(content):
                if "verify" in content.lower() or "captcha" in content.lower():
                    await self._handle_captcha(page)
                else:
                    proxy = self.proxy_pool.get_next()
                    raise RateLimitError(f"Shopee blocked, proxy={proxy.host if proxy else 'direct'}")

            await self._human_scroll(page)
            await asyncio.sleep(1.5)  # let API intercepts settle

            if api_data:
                return self._parse_api_response(api_data, external_id, product_url)

            # Fallback: DOM parsing
            return await self._parse_dom(page, external_id, product_url)

    async def _do_search(self, keyword: str, max_results: int) -> list[ScrapedProduct]:
        search_url = SHOPEE_API_SEARCH.format(keyword=keyword, limit=min(max_results, 60))
        products = []

        async with await self._new_context() as ctx:
            page: Page = await ctx.new_page()
            search_results: dict = {}

            async def capture_search(response):
                if "search_items" in response.url:
                    try:
                        body = await response.json()
                        search_results.update(body)
                    except Exception:
                        pass

            page.on("response", capture_search)
            await page.goto(
                f"https://shopee.com.br/search?keyword={keyword}",
                wait_until="domcontentloaded",
                timeout=self.timeout * 1000,
            )
            await self._human_scroll(page, pixels=800)
            await asyncio.sleep(2)

        items = search_results.get("items") or []
        for raw in items[:max_results]:
            item = raw.get("item_basic") or raw
            try:
                products.append(self._parse_search_item(item))
            except Exception as e:
                logger.warning("shopee_search_item_parse_failed", error=str(e))

        logger.info("shopee_search_done", keyword=keyword, found=len(products))
        return products

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_api_response(self, data: dict, external_id: str, url: str) -> ScrapedProduct:
        item = data.get("data") or data.get("item") or data
        if not item:
            raise ValueError("Empty Shopee API data")

        price_raw = item.get("price") or item.get("price_min") or 0
        orig_raw = item.get("price_before_discount") or item.get("price_max") or 0

        # Shopee stores prices × 100000
        price = price_raw / 100_000 if price_raw else None
        orig_price = orig_raw / 100_000 if orig_raw else None

        seller_data = item.get("shop_location") and {
            "shopid": item.get("shopid"),
            "shop_name": item.get("shop_name", ""),
            "shop_rating": item.get("shop_rating"),
        }

        seller = None
        if item.get("shopid"):
            seller = ScrapedSeller(
                external_id=str(item.get("shopid", "")),
                name=item.get("shop_name", ""),
                marketplace="shopee",
                score=item.get("shop_rating"),
                total_products=item.get("shop_item_count", 0),
            )

        images = []
        for img in item.get("images") or []:
            images.append(f"https://cf.shopee.com.br/file/{img}")

        promotions = {}
        if item.get("discount"):
            promotions["discount"] = item["discount"]
        if item.get("hidden_price_display"):
            promotions["label"] = item["hidden_price_display"]

        stock = item.get("stock") or item.get("item_status", {}).get("stock")

        return ScrapedProduct(
            external_id=external_id,
            marketplace="shopee",
            title=item.get("name", ""),
            price=price,
            original_price=orig_price if orig_price and orig_price > (price or 0) else None,
            currency="BRL",
            description=item.get("description"),
            images=images,
            sku=str(item.get("itemid", "")),
            url=url,
            rating=item.get("item_rating", {}).get("rating_star"),
            reviews_count=item.get("item_rating", {}).get("rating_count", [0])[0]
            if isinstance(item.get("item_rating", {}).get("rating_count"), list)
            else item.get("comment_count", 0),
            stock_quantity=int(stock) if stock is not None else None,
            is_available=item.get("stock", 1) > 0,
            seller=seller,
            promotions=promotions,
            raw_data=item,
        )

    def _parse_search_item(self, item: dict) -> ScrapedProduct:
        shop_id = item.get("shopid", "")
        item_id = item.get("itemid", "")
        price_raw = item.get("price") or item.get("price_min") or 0
        price = price_raw / 100_000 if price_raw else None

        return ScrapedProduct(
            external_id=f"{shop_id}.{item_id}",
            marketplace="shopee",
            title=item.get("name", ""),
            price=price,
            currency="BRL",
            url=SHOPEE_PRODUCT_URL.format(slug="product", shop_id=shop_id, item_id=item_id),
            rating=item.get("item_rating", {}).get("rating_star"),
            reviews_count=item.get("item_rating", {}).get("rating_count", 0),
            stock_quantity=item.get("stock"),
            is_available=item.get("stock", 0) > 0,
            raw_data=item,
        )

    async def _parse_dom(self, page: Page, external_id: str, url: str) -> ScrapedProduct:
        """Fallback DOM parser when API interception yields nothing."""
        logger.info("shopee_dom_fallback", external_id=external_id)

        title = await self._safe_text(page, "._44qnta, [class*='product-title'], h1")
        price_text = await self._safe_text(page, "._3n5NQx, [class*='price--current']")
        price = self._parse_price(price_text)
        rating_text = await self._safe_text(page, "._3Yx_67, [class*='rating']")

        return ScrapedProduct(
            external_id=external_id,
            marketplace="shopee",
            title=title or "Unknown",
            price=price,
            currency="BRL",
            url=url,
            rating=self._parse_float(rating_text),
            is_available=price is not None,
        )

    # ── CAPTCHA handling ──────────────────────────────────────────────────────

    async def _handle_captcha(self, page: Page) -> None:
        logger.info("shopee_captcha_detected", url=page.url)

        # Try slider first (most common on Shopee BR)
        result = await self.captcha_solver.solve_slider(page)
        if result.solved:
            logger.info("shopee_captcha_solved", method=result.method)
            await asyncio.sleep(2)
            return

        # Try reCAPTCHA if present
        site_key_match = re.search(r'data-sitekey="([^"]+)"', await page.content())
        if site_key_match:
            result = await self.captcha_solver.solve_recaptcha_v2(
                site_key=site_key_match.group(1),
                page_url=page.url,
            )
            if result.solved:
                await page.evaluate(
                    f"document.getElementById('g-recaptcha-response').value = '{result.token}'"
                )
                await page.click('[type=submit], [class*="submit"]')
                await asyncio.sleep(2)
                return

        raise CaptchaError("Shopee CAPTCHA could not be solved")

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    async def _safe_text(page: Page, selector: str) -> str:
        try:
            el = await page.query_selector(selector)
            return (await el.inner_text()).strip() if el else ""
        except Exception:
            return ""

    @staticmethod
    def _parse_price(text: str) -> float | None:
        if not text:
            return None
        cleaned = re.sub(r"[^\d,.]", "", text).replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _parse_float(text: str) -> float | None:
        if not text:
            return None
        match = re.search(r"[\d.]+", text)
        return float(match.group()) if match else None
