"""
Page Object Models for E2E tests.
Each class wraps one page/feature, exposing semantic actions and assertions.
"""
from __future__ import annotations
from playwright.sync_api import Page, expect

FRONTEND_URL = "http://localhost:3000"


class LoginPageObject:
    def __init__(self, page: Page):
        self.page = page
        self.email_input    = page.locator('input[type="email"]')
        self.password_input = page.locator('input[type="password"]')
        self.submit_btn     = page.locator('button[type="submit"]')
        self.error_msg      = page.locator('text=Invalid email or password')

    def navigate(self):
        self.page.goto(f"{FRONTEND_URL}/login")
        expect(self.page).to_have_url(f"{FRONTEND_URL}/login")

    def login(self, email: str, password: str):
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.submit_btn.click()

    def assert_error_visible(self):
        expect(self.error_msg).to_be_visible()

    def assert_redirected_to_dashboard(self):
        expect(self.page).to_have_url(f"{FRONTEND_URL}/", timeout=8_000)


class OverviewPageObject:
    def __init__(self, page: Page):
        self.page    = page
        self.heading = page.locator('h1', has_text="Overview")

    def navigate(self):
        self.page.goto(FRONTEND_URL)

    def assert_loaded(self):
        expect(self.heading).to_be_visible(timeout=8_000)

    def assert_health_status_visible(self):
        # Health card shows either "All systems operational" or "Degraded"
        health = self.page.locator('text=All systems operational').or_(
            self.page.locator('text=Degraded')
        )
        expect(health).to_be_visible(timeout=10_000)

    def assert_stats_visible(self):
        expect(self.page.locator('text=Products tracked')).to_be_visible()
        expect(self.page.locator('text=Sellers monitored')).to_be_visible()


class ProductsPageObject:
    def __init__(self, page: Page):
        self.page           = page
        self.heading        = page.locator('h1', has_text="Products")
        self.search_input   = page.locator('input[placeholder*="Search"]')
        self.marketplace_select = page.locator('select').nth(0)
        self.table_rows     = page.locator('table tbody tr')
        self.empty_state    = page.locator('text=No products found')

    def navigate(self):
        self.page.goto(f"{FRONTEND_URL}/products")

    def assert_loaded(self):
        expect(self.heading).to_be_visible(timeout=8_000)

    def search(self, query: str):
        self.search_input.fill(query)
        self.page.wait_for_timeout(500)  # debounce

    def filter_marketplace(self, marketplace: str):
        self.marketplace_select.select_option(marketplace)
        self.page.wait_for_timeout(300)

    def click_first_product(self):
        self.table_rows.first.click()

    def assert_drawer_open(self):
        # Drawer contains price section heading
        expect(self.page.locator('text=Current price')).to_be_visible(timeout=5_000)

    def assert_row_count_gte(self, n: int):
        expect(self.table_rows).to_have_count(n, timeout=8_000)

    def assert_empty_state(self):
        expect(self.empty_state).to_be_visible()


class AnalyticsPageObject:
    def __init__(self, page: Page):
        self.page           = page
        self.heading        = page.locator('h1', has_text="Analytics")
        self.product_select = page.locator('select').nth(0)
        self.period_select  = page.locator('select').nth(1)

    def navigate(self):
        self.page.goto(f"{FRONTEND_URL}/analytics")

    def assert_loaded(self):
        expect(self.heading).to_be_visible(timeout=8_000)
        # Should show the empty prompt before selecting a product
        expect(self.page.locator('text=Select a product to view')).to_be_visible()

    def select_first_product(self):
        # Wait for options to populate
        self.page.wait_for_function(
            "document.querySelectorAll('select')[0].options.length > 1",
            timeout=8_000,
        )
        self.product_select.select_option(index=1)

    def select_period(self, days: str):
        self.period_select.select_option(days)

    def assert_stats_visible(self):
        expect(self.page.locator('text=Current price')).to_be_visible(timeout=8_000)


class ScrapingPageObject:
    def __init__(self, page: Page):
        self.page             = page
        self.heading          = page.locator('h1', has_text="Scraping Control")
        self.marketplace_sel  = page.locator('select').nth(0)
        self.trigger_btn      = page.locator('button', has_text="Trigger scrape")
        self.keyword_input    = page.locator('input[placeholder*="keyword"]').or_(
                                    page.locator('input[placeholder*="e.g."]')
                                )
        self.search_btn       = page.locator('button', has_text="Search & track")

    def navigate(self):
        self.page.goto(f"{FRONTEND_URL}/scraping")

    def assert_loaded(self):
        expect(self.heading).to_be_visible(timeout=8_000)

    def trigger_marketplace_scrape(self, marketplace: str = "shopee"):
        self.marketplace_sel.select_option(marketplace)
        self.trigger_btn.click()

    def assert_task_queued(self):
        # After triggering, a task row should appear
        task_row = self.page.locator('text=PENDING').or_(
            self.page.locator('text=STARTED')
        ).or_(
            self.page.locator('text=SUCCESS')
        )
        expect(task_row).to_be_visible(timeout=10_000)

    def search_keyword(self, keyword: str, marketplace: str = "shopee"):
        self.marketplace_sel.select_option(marketplace)
        self.keyword_input.fill(keyword)
        self.search_btn.click()
