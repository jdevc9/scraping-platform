"""
Unit tests for Phase 2 scraping layer.
No browser, no DB, no network — pure logic tests.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

from app.scrapers.schemas import ScrapedProduct, ScrapedSeller
from app.scrapers.proxy import Proxy, ProxyPool
from app.scrapers.useragent import random_user_agent, playwright_fingerprint
from app.services.change_detector import AlertType, ChangeDetector


# ── ScrapedProduct ─────────────────────────────────────────────────────────────

class TestScrapedProduct:
    def test_valid_product(self):
        p = ScrapedProduct(
            external_id="123.456",
            marketplace="shopee",
            title="Test Product",
            price=99.90,
        )
        assert p.is_valid()

    def test_missing_title_is_invalid(self):
        p = ScrapedProduct(external_id="123", marketplace="shopee", title="")
        assert not p.is_valid()

    def test_missing_external_id_is_invalid(self):
        p = ScrapedProduct(external_id="", marketplace="shopee", title="Test")
        assert not p.is_valid()

    def test_default_values(self):
        p = ScrapedProduct(external_id="1", marketplace="shopee", title="T")
        assert p.reviews_count == 0
        assert p.is_available is True
        assert p.currency == "BRL"
        assert isinstance(p.scraped_at, datetime)
        assert p.images == []
        assert p.promotions == {}


# ── Proxy ─────────────────────────────────────────────────────────────────────

class TestProxy:
    def test_url_without_creds(self):
        p = Proxy(host="1.2.3.4", port=8080)
        assert p.url == "http://1.2.3.4:8080"

    def test_url_with_creds(self):
        p = Proxy(host="1.2.3.4", port=8080, username="user", password="pass")
        assert p.url == "http://user:pass@1.2.3.4:8080"

    def test_to_playwright_dict(self):
        p = Proxy(host="1.2.3.4", port=8080, username="u", password="p")
        d = p.to_playwright_dict()
        assert d["server"] == "http://1.2.3.4:8080"
        assert d["username"] == "u"
        assert d["password"] == "p"

    def test_mark_failure_disables_after_3(self):
        p = Proxy(host="1.2.3.4", port=8080)
        assert p.is_healthy
        p.mark_failure()
        p.mark_failure()
        assert p.is_healthy  # still healthy at 2 failures
        p.mark_failure()
        assert not p.is_healthy  # disabled at 3

    def test_mark_success_resets(self):
        p = Proxy(host="1.2.3.4", port=8080)
        p.mark_failure()
        p.mark_failure()
        p.mark_failure()
        assert not p.is_healthy
        p.mark_success()
        assert p.is_healthy
        assert p.failures == 0


class TestProxyPool:
    def _make_pool(self, n: int = 3) -> ProxyPool:
        strings = [f"http://user:pass@proxy{i}.test:{8080 + i}" for i in range(n)]
        return ProxyPool.from_list(strings)

    def test_load_from_list(self):
        pool = self._make_pool(3)
        assert len(pool) == 3

    def test_round_robin(self):
        pool = self._make_pool(3)
        hosts = [pool.get_next().host for _ in range(6)]
        # Should cycle through all 3
        assert len(set(hosts)) == 3

    def test_get_next_skips_unhealthy(self):
        pool = self._make_pool(2)
        # Disable first proxy
        pool.proxies[0].is_healthy = False
        for _ in range(5):
            p = pool.get_next()
            assert p.host == pool.proxies[1].host

    def test_empty_pool_returns_none(self):
        pool = ProxyPool()
        assert pool.get_next() is None

    def test_parse_bare_host_port(self):
        pool = ProxyPool.from_list(["192.168.1.1:3128"])
        assert len(pool) == 1
        assert pool.proxies[0].host == "192.168.1.1"
        assert pool.proxies[0].port == 3128

    def test_parse_with_protocol(self):
        pool = ProxyPool.from_list(["socks5://10.0.0.1:1080"])
        assert pool.proxies[0].protocol == "socks5"

    def test_invalid_proxy_skipped(self):
        pool = ProxyPool.from_list(["not-a-proxy", "192.168.1.1:8080"])
        assert len(pool) == 1


# ── User Agent ────────────────────────────────────────────────────────────────

class TestUserAgent:
    def test_chrome_user_agent_contains_chrome(self):
        ua = random_user_agent("chrome")
        assert "Chrome" in ua

    def test_firefox_user_agent_contains_firefox(self):
        ua = random_user_agent("firefox")
        assert "Firefox" in ua

    def test_playwright_fingerprint_has_required_keys(self):
        fp = playwright_fingerprint("chrome")
        assert "user_agent" in fp
        assert "viewport" in fp
        assert "locale" in fp
        assert "timezone_id" in fp

    def test_viewport_has_width_height(self):
        fp = playwright_fingerprint()
        vp = fp["viewport"]
        assert "width" in vp and "height" in vp
        assert vp["width"] > 800
        assert vp["height"] > 600


# ── ChangeDetector ─────────────────────────────────────────────────────────────

class TestChangeDetector:
    def _make_product(self):
        m = MagicMock()
        m.id = "prod-uuid-001"
        m.marketplace = "shopee"
        m.title = "Test Product"
        return m

    def _make_history(self, price, price_changed, stock_changed, price_diff=None,
                      is_available=True, stock_quantity=10):
        h = MagicMock()
        h.price = price
        h.price_changed = price_changed
        h.stock_changed = stock_changed
        h.price_diff = price_diff
        h.is_available = is_available
        h.stock_quantity = stock_quantity
        h.currency = "BRL"
        return h

    def test_no_changes_no_alerts(self):
        detector = ChangeDetector()
        product = self._make_product()
        history = self._make_history(100.0, False, False)
        events = detector.analyse(product, history)
        assert events == []

    def test_price_drop_above_threshold_fires_alert(self):
        detector = ChangeDetector(drop_threshold=5.0)
        product = self._make_product()
        # Price went from 100 → 90 = -10%
        history = self._make_history(90.0, True, False, price_diff=-10.0)
        events = detector.analyse(product, history)
        assert len(events) == 1
        assert events[0].alert_type == AlertType.price_drop
        assert events[0].payload["old_price"] == pytest.approx(100.0)
        assert events[0].payload["new_price"] == pytest.approx(90.0)

    def test_price_drop_below_threshold_no_alert(self):
        detector = ChangeDetector(drop_threshold=5.0)
        product = self._make_product()
        # Price went from 100 → 98 = -2% (below 5% threshold)
        history = self._make_history(98.0, True, False, price_diff=-2.0)
        events = detector.analyse(product, history)
        assert events == []

    def test_price_spike_fires_alert(self):
        detector = ChangeDetector(spike_threshold=20.0)
        product = self._make_product()
        # Price went from 100 → 130 = +30%
        history = self._make_history(130.0, True, False, price_diff=30.0)
        events = detector.analyse(product, history)
        assert len(events) == 1
        assert events[0].alert_type == AlertType.price_spike

    def test_out_of_stock_fires_alert(self):
        detector = ChangeDetector()
        product = self._make_product()
        history = self._make_history(99.0, False, True, is_available=False, stock_quantity=0)
        events = detector.analyse(product, history)
        assert any(e.alert_type == AlertType.out_of_stock for e in events)

    def test_back_in_stock_fires_alert(self):
        detector = ChangeDetector()
        product = self._make_product()
        history = self._make_history(99.0, False, True, is_available=True, stock_quantity=5)
        events = detector.analyse(product, history)
        assert any(e.alert_type == AlertType.back_in_stock for e in events)

    def test_multiple_events_same_scrape(self):
        detector = ChangeDetector(drop_threshold=5.0)
        product = self._make_product()
        # Both price dropped AND went out of stock
        history = self._make_history(
            price=85.0,
            price_changed=True,
            stock_changed=True,
            price_diff=-15.0,
            is_available=False,
            stock_quantity=0,
        )
        events = detector.analyse(product, history)
        types = {e.alert_type for e in events}
        assert AlertType.price_drop in types
        assert AlertType.out_of_stock in types

    def test_custom_thresholds(self):
        detector = ChangeDetector(drop_threshold=1.0, spike_threshold=5.0)
        product = self._make_product()
        # Only -2% drop — below 5% but above custom 1% threshold
        history = self._make_history(98.0, True, False, price_diff=-2.0)
        events = detector.analyse(product, history)
        assert len(events) == 1
        assert events[0].alert_type == AlertType.price_drop
