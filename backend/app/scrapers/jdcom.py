from __future__ import annotations

import json
import re
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.core.logging import get_logger
from app.scrapers.base import BaseScraper, RateLimitError, CaptchaError
from app.scrapers.factory import register
from app.scrapers.schemas import ScrapedProduct, ScrapedSeller
from app.scrapers.useragent import random_user_agent, random_viewport

logger = get_logger(__name__)

# JD.com endpoints — Brazilian operation (jd.com/br) uses same API structure
JDCOM_PRODUCT_URL = "https://item.jd.com/{item_id}.html"
JDCOM_SEARCH_URL = "https://search.jd.com/Search?keyword={keyword}&page=1&s=1&click=0"
JDCOM_PRICE_API = "https://p.3.cn/prices/mgets?skuIds=J_{item_id}"
JDCOM_STOCK_API = "https://c0.3.cn/stock?skuId={item_id}&area=1_72_2799_0&cat=1"


def _build_chrome_options(proxy=None, user_agent: str = "") -> Options:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--window-size=1920,1080")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    if user_agent:
        opts.add_argument(f"--user-agent={user_agent}")

    if proxy:
        opts.add_argument(f"--proxy-server={proxy.url}")

    return opts


@register("jdcom")
class JDComScraper(BaseScraper):
    """
    JD.com scraper using Selenium (sync) wrapped in asyncio via ThreadPoolExecutor.

    Strategy:
    1. Load product page with stealth Chrome (undetected-chromedriver approach via options).
    2. Intercept inline JSON embedded in <script> tags — JD embeds product data as
       window.__GLOBAL_DATA__ or script[type=application/ld+json].
    3. Hit price + stock APIs separately (they use different CDN domains, less protected).
    4. BeautifulSoup for DOM fallback on any missing fields.

    Why Selenium (not Playwright) for JD:
    JD.com uses TDX (Tencent security SDK) which fingerprints headless browsers.
    Selenium + undetected-chromedriver options defeat it more reliably than Playwright
    on JD.com specifically. Shopee (React SPA) benefits more from Playwright's network
    interception API.
    """

    marketplace = "jdcom"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._driver: webdriver.Chrome | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def _setup(self) -> None:
        await asyncio.get_event_loop().run_in_executor(self._executor, self._init_driver)

    async def _teardown(self) -> None:
        await asyncio.get_event_loop().run_in_executor(self._executor, self._quit_driver)
        self._executor.shutdown(wait=False)

    def _init_driver(self) -> None:
        proxy = self.proxy_pool.get_next()
        ua = random_user_agent("chrome")
        opts = _build_chrome_options(proxy=proxy, user_agent=ua)
        self._driver = webdriver.Chrome(options=opts)

        # CDP commands to mask automation — same effect as undetected-chromedriver
        self._driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": self._inject_stealth_js()},
        )
        self._driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": ua},
        )
        vp = random_viewport()
        self._driver.set_window_size(vp["width"], vp["height"])
        logger.info("jdcom_driver_started", proxy=proxy.host if proxy else "direct", ua=ua[:40])

    def _quit_driver(self) -> None:
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass

    # ── Public interface ──────────────────────────────────────────────────────

    async def scrape_product(self, external_id: str, url: str | None = None) -> ScrapedProduct:
        return await self._with_retry(self._async_scrape_product, external_id, url)

    async def search_products(self, keyword: str, max_results: int = 20) -> list[ScrapedProduct]:
        return await self._with_retry(self._async_search, keyword, max_results)

    # ── Async wrappers (Selenium is sync — run in executor) ───────────────────

    async def _async_scrape_product(self, external_id: str, url: str | None) -> ScrapedProduct:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_scrape_product, external_id, url
        )

    async def _async_search(self, keyword: str, max_results: int) -> list[ScrapedProduct]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._sync_search, keyword, max_results
        )

    # ── Sync Selenium implementation ──────────────────────────────────────────

    def _sync_scrape_product(self, external_id: str, url: str | None) -> ScrapedProduct:
        item_id = external_id
        product_url = url or JDCOM_PRODUCT_URL.format(item_id=item_id)

        logger.info("jdcom_scraping_product", item_id=item_id, url=product_url)
        self._driver.get(product_url)

        # Wait for core content
        try:
            WebDriverWait(self._driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sku-name, #name, h1"))
            )
        except TimeoutException:
            logger.warning("jdcom_page_load_timeout", url=product_url)

        # Block / CAPTCHA detection
        html = self._driver.page_source
        if self._is_blocked(html):
            if self._has_slider_captcha():
                self._solve_slider_sync()
                html = self._driver.page_source
            else:
                raise RateLimitError("JD.com blocked the request")

        self._human_scroll_sync(pixels=800)
        time.sleep(1.0)

        # Try extracting embedded JSON first (fastest, most reliable)
        product = self._extract_from_script_json(html, item_id, product_url)
        if product:
            # Enrich with separate price/stock API calls
            product = self._enrich_price_stock(product, item_id)
            return product

        # Fallback: full DOM parse
        return self._parse_dom(html, item_id, product_url)

    def _sync_search(self, keyword: str, max_results: int) -> list[ScrapedProduct]:
        search_url = JDCOM_SEARCH_URL.format(keyword=keyword)
        self._driver.get(search_url)

        try:
            WebDriverWait(self._driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#J_goodsList, .gl-warp"))
            )
        except TimeoutException:
            logger.warning("jdcom_search_load_timeout")
            return []

        self._human_scroll_sync(pixels=1200)
        time.sleep(1.5)

        soup = BeautifulSoup(self._driver.page_source, "lxml")
        return self._parse_search_results(soup, max_results)

    # ── Extraction strategies ─────────────────────────────────────────────────

    def _extract_from_script_json(
        self, html: str, item_id: str, url: str
    ) -> ScrapedProduct | None:
        """
        JD.com embeds product data in multiple <script> formats:
          - window.__GLOBAL_DATA__ = {...}
          - var pageConfig = {...}
          - JSON-LD: <script type="application/ld+json">
        """
        soup = BeautifulSoup(html, "lxml")

        # Strategy A: JSON-LD (most structured, least fragile)
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, dict) and data.get("@type") in ("Product", "ItemPage"):
                    return self._parse_jsonld(data, item_id, url)
            except (json.JSONDecodeError, TypeError):
                continue

        # Strategy B: window.__GLOBAL_DATA__
        for tag in soup.find_all("script"):
            text = tag.string or ""
            if "__GLOBAL_DATA__" in text:
                match = re.search(r"window\.__GLOBAL_DATA__\s*=\s*(\{.+?\});", text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        return self._parse_global_data(data, item_id, url)
                    except (json.JSONDecodeError, KeyError):
                        continue

        # Strategy C: pageConfig variable
        for tag in soup.find_all("script"):
            text = tag.string or ""
            if "pageConfig" in text and "product" in text:
                match = re.search(r"var\s+pageConfig\s*=\s*(\{.+?\});", text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        return self._parse_page_config(data, item_id, url)
                    except (json.JSONDecodeError, KeyError):
                        continue

        return None

    def _parse_jsonld(self, data: dict, item_id: str, url: str) -> ScrapedProduct:
        offers = data.get("offers", {})
        price_raw = offers.get("price") or offers.get("lowPrice")
        price = float(price_raw) if price_raw else None

        seller_data = offers.get("seller", {})
        seller = None
        if seller_data.get("name"):
            seller = ScrapedSeller(
                external_id=seller_data.get("url", item_id),
                name=seller_data.get("name", ""),
                marketplace="jdcom",
            )

        images = []
        if data.get("image"):
            imgs = data["image"] if isinstance(data["image"], list) else [data["image"]]
            images = [str(i) for i in imgs]

        return ScrapedProduct(
            external_id=item_id,
            marketplace="jdcom",
            title=data.get("name", ""),
            description=data.get("description"),
            price=price,
            currency="CNY",
            url=url,
            images=images,
            sku=data.get("sku") or data.get("mpn"),
            rating=float(data.get("aggregateRating", {}).get("ratingValue", 0) or 0) or None,
            reviews_count=int(data.get("aggregateRating", {}).get("reviewCount", 0) or 0),
            is_available=offers.get("availability", "") != "https://schema.org/OutOfStock",
            seller=seller,
            raw_data=data,
        )

    def _parse_global_data(self, data: dict, item_id: str, url: str) -> ScrapedProduct:
        product = data.get("product", data.get("skuInfo", {}))
        price_info = data.get("price", {})
        shop_info = data.get("shop", {})

        price = float(price_info.get("p", 0) or 0) or None

        seller = None
        if shop_info.get("shopName"):
            seller = ScrapedSeller(
                external_id=str(shop_info.get("shopId", item_id)),
                name=shop_info.get("shopName", ""),
                marketplace="jdcom",
                score=float(shop_info.get("score", 0) or 0) or None,
            )

        return ScrapedProduct(
            external_id=item_id,
            marketplace="jdcom",
            title=product.get("name", ""),
            description=product.get("desc"),
            price=price,
            currency="CNY",
            url=url,
            sku=str(product.get("sku", item_id)),
            rating=float(product.get("commentScore", 0) or 0) or None,
            reviews_count=int(product.get("commentCount", 0) or 0),
            stock_quantity=int(product.get("stockNum", 0) or 0) or None,
            is_available=product.get("stockState", 1) == 1,
            seller=seller,
            raw_data=data,
        )

    def _parse_page_config(self, data: dict, item_id: str, url: str) -> ScrapedProduct:
        product = data.get("product", {})
        return ScrapedProduct(
            external_id=item_id,
            marketplace="jdcom",
            title=product.get("name", ""),
            price=float(product.get("price", 0) or 0) or None,
            currency="CNY",
            url=url,
            sku=str(product.get("skuId", item_id)),
            is_available=True,
            raw_data=data,
        )

    def _parse_dom(self, html: str, item_id: str, url: str) -> ScrapedProduct:
        """Full DOM fallback parser — handles JD.com's standard product page structure."""
        logger.info("jdcom_dom_fallback", item_id=item_id)
        soup = BeautifulSoup(html, "lxml")

        # Title
        title = ""
        for sel in (".sku-name", "#name h1", "h1.itemInfo-wrap"):
            tag = soup.select_one(sel)
            if tag:
                title = tag.get_text(strip=True)
                break

        # Price (JD uses dynamic loading — may be empty, enriched via API later)
        price = None
        for sel in (".p-price .price", "#jd-price", ".price-b"):
            tag = soup.select_one(sel)
            if tag:
                price = self._parse_price(tag.get_text(strip=True))
                break

        # Images
        images = []
        gallery = soup.select(".spec-items img, #spec-list img")
        for img in gallery[:10]:
            src = img.get("src") or img.get("data-src", "")
            if src:
                images.append("https:" + src if src.startswith("//") else src)

        # Rating
        rating = None
        rating_tag = soup.select_one(".percent-con, [class*='score']")
        if rating_tag:
            rating = self._parse_float(rating_tag.get_text(strip=True))

        # Reviews count
        reviews_count = 0
        review_tag = soup.select_one("#comment-count, .count")
        if review_tag:
            reviews_count = int(re.sub(r"[^\d]", "", review_tag.get_text()) or "0")

        # Description
        desc_tag = soup.select_one("#detail-tag-id-3, .item-detail")
        description = desc_tag.get_text(strip=True)[:2000] if desc_tag else None

        # Seller
        seller = None
        shop_tag = soup.select_one("#shop-name a, .seller-name a")
        if shop_tag:
            seller = ScrapedSeller(
                external_id=item_id,
                name=shop_tag.get_text(strip=True),
                marketplace="jdcom",
            )

        return ScrapedProduct(
            external_id=item_id,
            marketplace="jdcom",
            title=title or f"JD Product {item_id}",
            price=price,
            currency="CNY",
            url=url,
            images=images,
            description=description,
            rating=rating,
            reviews_count=reviews_count,
            is_available=price is not None,
            seller=seller,
        )

    def _enrich_price_stock(self, product: ScrapedProduct, item_id: str) -> ScrapedProduct:
        """
        Hit JD's price and stock CDN APIs — less protected, returns JSON directly.
        These endpoints don't require cookies or JS execution.
        """
        import urllib.request

        # Price API
        try:
            price_url = JDCOM_PRICE_API.format(item_id=item_id)
            req = urllib.request.Request(
                price_url,
                headers={"User-Agent": random_user_agent("chrome"), "Referer": "https://item.jd.com/"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                prices = json.loads(resp.read().decode())
                if prices:
                    p_data = prices[0]
                    if p_data.get("p"):
                        product.price = float(p_data["p"])
                    if p_data.get("op") and float(p_data["op"]) > (product.price or 0):
                        product.original_price = float(p_data["op"])
        except Exception as e:
            logger.warning("jdcom_price_api_failed", item_id=item_id, error=str(e))

        # Stock API
        try:
            stock_url = JDCOM_STOCK_API.format(item_id=item_id)
            req = urllib.request.Request(
                stock_url,
                headers={"User-Agent": random_user_agent("chrome"), "Referer": "https://item.jd.com/"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                stock_data = json.loads(resp.read().decode())
                stock_state = stock_data.get("stock", {}).get("StockState")
                product.is_available = stock_state in (33, 40)  # 33=in stock, 40=adequate
                if stock_data.get("stock", {}).get("num"):
                    product.stock_quantity = int(stock_data["stock"]["num"])
        except Exception as e:
            logger.warning("jdcom_stock_api_failed", item_id=item_id, error=str(e))

        return product

    def _parse_search_results(self, soup: BeautifulSoup, max_results: int) -> list[ScrapedProduct]:
        products = []
        items = soup.select("#J_goodsList .gl-item, .gl-warp .gl-item")

        for item in items[:max_results]:
            try:
                item_id = item.get("data-sku") or item.get("data-pid", "")
                if not item_id:
                    continue

                title_tag = item.select_one(".p-name em, .p-name a")
                title = title_tag.get_text(strip=True) if title_tag else ""

                price_tag = item.select_one(".p-price strong i, .p-price .price")
                price = self._parse_price(price_tag.get_text(strip=True)) if price_tag else None

                img_tag = item.select_one("img.lazy, img[data-lazy-img]")
                src = ""
                if img_tag:
                    src = img_tag.get("data-lazy-img") or img_tag.get("src", "")

                comment_tag = item.select_one(".p-commit a, .comment")
                reviews_count = 0
                if comment_tag:
                    reviews_count = int(re.sub(r"[^\d]", "", comment_tag.get_text()) or "0")

                products.append(
                    ScrapedProduct(
                        external_id=str(item_id),
                        marketplace="jdcom",
                        title=title,
                        price=price,
                        currency="CNY",
                        url=JDCOM_PRODUCT_URL.format(item_id=item_id),
                        images=["https:" + src] if src.startswith("//") else ([src] if src else []),
                        reviews_count=reviews_count,
                        is_available=price is not None,
                    )
                )
            except Exception as e:
                logger.warning("jdcom_search_item_parse_failed", error=str(e))

        logger.info("jdcom_search_done", found=len(products))
        return products

    # ── CAPTCHA / Anti-bot (sync Selenium) ───────────────────────────────────

    def _has_slider_captcha(self) -> bool:
        try:
            self._driver.find_element(By.CSS_SELECTOR, "#JDJRV-wrap-loginsubmit, .JDJRV-slide-btn")
            return True
        except NoSuchElementException:
            return False

    def _solve_slider_sync(self) -> None:
        logger.info("jdcom_slider_captcha_detected")
        try:
            slider = self._driver.find_element(
                By.CSS_SELECTOR, ".JDJRV-slide-btn, #JDJRV-wrap-loginsubmit"
            )
            actions = ActionChains(self._driver)
            actions.click_and_hold(slider)

            # Human-like movement with acceleration curve
            import random
            x_offset = 0
            for i in range(20):
                progress = i / 19
                speed = progress * (1 - progress) * 4
                step = int(260 * speed / 10)
                jitter = random.randint(-2, 2)
                x_offset += max(step, 1)
                actions.move_by_offset(max(step, 1), jitter)
                actions.pause(random.uniform(0.01, 0.05))

            actions.release().perform()
            time.sleep(2)
        except Exception as e:
            logger.warning("jdcom_slider_solve_failed", error=str(e))
            raise CaptchaError("JD.com slider CAPTCHA failed")

    def _human_scroll_sync(self, pixels: int = 600) -> None:
        import random
        steps = random.randint(4, 8)
        for _ in range(steps):
            step_px = pixels // steps + random.randint(-30, 30)
            self._driver.execute_script(f"window.scrollBy(0, {step_px});")
            time.sleep(random.uniform(0.15, 0.45))

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_price(text: str) -> float | None:
        if not text:
            return None
        cleaned = re.sub(r"[^\d.,]", "", text).replace(",", ".")
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
