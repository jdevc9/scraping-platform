"""
Tests for scraper parsing logic — no real browser, no network.
We mock the page/driver and test parsers directly.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.scrapers.shopee import ShopeeScraper
from app.scrapers.jdcom import JDComScraper
from app.scrapers.schemas import ScrapedProduct


# ── Shopee parser tests ───────────────────────────────────────────────────────

class TestShopeeParser:
    def _make_scraper(self) -> ShopeeScraper:
        scraper = ShopeeScraper.__new__(ShopeeScraper)
        scraper.marketplace = "shopee"
        scraper.proxy_pool = MagicMock()
        scraper.proxy_pool.get_next.return_value = None
        scraper.captcha_solver = MagicMock()
        scraper.max_retries = 3
        scraper.timeout = 30
        scraper._request_count = 0
        scraper._last_request_time = 0.0
        return scraper

    def test_parse_api_response_full_data(self):
        scraper = self._make_scraper()
        api_data = {
            "data": {
                "name": "iPhone 15 Pro",
                "price": 599000000,          # R$ 5990.00 (× 100_000)
                "price_before_discount": 699000000,
                "stock": 50,
                "itemid": 67890,
                "shopid": 12345,
                "shop_name": "Apple Store BR",
                "shop_rating": 4.9,
                "shop_item_count": 200,
                "description": "Latest iPhone",
                "images": ["abc123def456"],
                "discount": "14%",
                "item_rating": {
                    "rating_star": 4.8,
                    "rating_count": [1500],
                },
            }
        }
        result = scraper._parse_api_response(api_data, "12345.67890", "https://shopee.com.br/test")

        assert result.title == "iPhone 15 Pro"
        assert result.price == pytest.approx(5990.0)
        assert result.original_price == pytest.approx(6990.0)
        assert result.stock_quantity == 50
        assert result.is_available is True
        assert result.rating == pytest.approx(4.8)
        assert result.reviews_count == 1500
        assert result.seller is not None
        assert result.seller.name == "Apple Store BR"
        assert result.seller.score == pytest.approx(4.9)
        assert len(result.images) == 1
        assert "cf.shopee.com.br" in result.images[0]
        assert result.promotions.get("discount") == "14%"

    def test_parse_api_response_minimal(self):
        scraper = self._make_scraper()
        api_data = {
            "data": {
                "name": "Basic Product",
                "itemid": 111,
                "shopid": 222,
            }
        }
        result = scraper._parse_api_response(api_data, "222.111", "https://shopee.com.br/x")
        assert result.title == "Basic Product"
        assert result.price is None
        assert result.is_available is False  # no stock

    def test_parse_api_empty_raises(self):
        scraper = self._make_scraper()
        with pytest.raises(ValueError, match="Empty Shopee API data"):
            scraper._parse_api_response({}, "1.1", "http://x")

    def test_parse_search_item(self):
        scraper = self._make_scraper()
        item = {
            "shopid": 999,
            "itemid": 888,
            "name": "Search Result",
            "price": 250000,   # R$ 2.50
            "stock": 100,
            "item_rating": {"rating_star": 4.2, "rating_count": 300},
        }
        result = scraper._parse_search_item(item)
        assert result.external_id == "999.888"
        assert result.price == pytest.approx(2.5)
        assert result.rating == pytest.approx(4.2)

    def test_price_parser(self):
        assert ShopeeScraper._parse_price("R$ 1.299,90") == pytest.approx(1299.90)
        assert ShopeeScraper._parse_price("99,90") == pytest.approx(99.90)
        assert ShopeeScraper._parse_price("") is None
        assert ShopeeScraper._parse_price("no price here") is None

    def test_blocked_detection(self):
        assert ShopeeScraper._is_blocked("Access Denied - Robot Check")
        assert ShopeeScraper._is_blocked("Please verify you are human")
        assert not ShopeeScraper._is_blocked("<html><body>Normal page</body></html>")

    def test_external_id_validation(self):
        """scrape_product should raise on bad external_id format."""
        scraper = self._make_scraper()
        with pytest.raises(ValueError, match="Invalid Shopee external_id format"):
            import asyncio
            asyncio.run(scraper._do_scrape_product("badformat", None))

    def test_stealth_js_contains_key_overrides(self):
        js = ShopeeScraper._inject_stealth_js()
        assert "navigator.webdriver" in js
        assert "plugins" in js
        assert "chrome" in js


# ── JD.com parser tests ───────────────────────────────────────────────────────

class TestJDComParser:
    def _make_scraper(self) -> JDComScraper:
        scraper = JDComScraper.__new__(JDComScraper)
        scraper.marketplace = "jdcom"
        scraper.proxy_pool = MagicMock()
        scraper.proxy_pool.get_next.return_value = None
        scraper.captcha_solver = MagicMock()
        scraper.max_retries = 3
        scraper.timeout = 30
        scraper._request_count = 0
        scraper._last_request_time = 0.0
        scraper._driver = None
        return scraper

    def test_parse_jsonld(self):
        scraper = self._make_scraper()
        data = {
            "@type": "Product",
            "name": "Xiaomi 14 Pro",
            "description": "Flagship phone",
            "sku": "SKU123",
            "image": ["https://img.jd.com/1.jpg", "https://img.jd.com/2.jpg"],
            "offers": {
                "price": "4999.00",
                "availability": "https://schema.org/InStock",
                "seller": {"name": "JD Self-operated"},
            },
            "aggregateRating": {
                "ratingValue": "4.9",
                "reviewCount": "5000",
            },
        }
        result = scraper._parse_jsonld(data, "item123", "https://item.jd.com/123.html")
        assert result.title == "Xiaomi 14 Pro"
        assert result.price == pytest.approx(4999.0)
        assert result.is_available is True
        assert result.sku == "SKU123"
        assert len(result.images) == 2
        assert result.rating == pytest.approx(4.9)
        assert result.reviews_count == 5000
        assert result.seller.name == "JD Self-operated"

    def test_parse_jsonld_out_of_stock(self):
        scraper = self._make_scraper()
        data = {
            "@type": "Product",
            "name": "Product",
            "offers": {
                "price": "100",
                "availability": "https://schema.org/OutOfStock",
            },
        }
        result = scraper._parse_jsonld(data, "x", "https://x")
        assert result.is_available is False

    def test_parse_global_data(self):
        scraper = self._make_scraper()
        data = {
            "product": {
                "name": "Samsung TV",
                "sku": "TV55",
                "stockState": 1,
                "stockNum": 30,
                "commentScore": 4.7,
                "commentCount": 800,
            },
            "price": {"p": "3299.00"},
            "shop": {
                "shopId": "999",
                "shopName": "Samsung Official",
                "score": 4.8,
            },
        }
        result = scraper._parse_global_data(data, "tv123", "https://item.jd.com/tv123.html")
        assert result.title == "Samsung TV"
        assert result.price == pytest.approx(3299.0)
        assert result.stock_quantity == 30
        assert result.is_available is True
        assert result.seller.name == "Samsung Official"

    def test_parse_price_utility(self):
        assert JDComScraper._parse_price("¥3,299.00") == pytest.approx(3299.0)
        assert JDComScraper._parse_price("1999") == pytest.approx(1999.0)
        assert JDComScraper._parse_price("") is None
        assert JDComScraper._parse_price("abc") is None

    def test_parse_dom_fallback(self):
        scraper = self._make_scraper()
        html = """
        <html><body>
          <div class="sku-name">Lenovo ThinkPad X1</div>
          <div class="p-price"><span class="price">8999.00</span></div>
          <div class="percent-con">4.8</div>
          <div id="comment-count">2万+</div>
          <a class="seller-name"><a>JD自营</a></a>
        </body></html>
        """
        result = scraper._parse_dom(html, "item999", "https://item.jd.com/999.html")
        assert "ThinkPad" in result.title
        assert result.external_id == "item999"
        assert result.marketplace == "jdcom"

    def test_script_json_extraction_jsonld(self):
        scraper = self._make_scraper()
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Test Item", "offers": {"price": "299"}}
        </script>
        </head><body></body></html>
        """
        result = scraper._extract_from_script_json(html, "item1", "https://item.jd.com/1.html")
        assert result is not None
        assert result.title == "Test Item"

    def test_blocked_detection_inherited(self):
        # JDComScraper inherits _is_blocked from BaseScraper
        assert JDComScraper._is_blocked("Security Check - Unusual Traffic Detected")
        assert not JDComScraper._is_blocked("<html>Normal product page</html>")


# ── Factory tests ─────────────────────────────────────────────────────────────

class TestScraperFactory:
    def test_get_scraper_shopee(self):
        from app.scrapers.factory import get_scraper
        scraper = get_scraper("shopee")
        assert scraper.marketplace == "shopee"

    def test_get_scraper_jdcom(self):
        from app.scrapers.factory import get_scraper
        scraper = get_scraper("jdcom")
        assert scraper.marketplace == "jdcom"

    def test_get_scraper_unknown_raises(self):
        from app.scrapers.factory import get_scraper
        with pytest.raises(ValueError, match="No scraper registered"):
            get_scraper("unknown_market")

    def test_list_marketplaces(self):
        from app.scrapers.factory import list_marketplaces
        markets = list_marketplaces()
        assert "shopee" in markets
        assert "jdcom" in markets
