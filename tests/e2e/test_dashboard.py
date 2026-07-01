"""
E2E tests — Overview Dashboard.
"""
import allure
from playwright.sync_api import Page, expect
from tests.e2e.pages import OverviewPageObject, ProductsPageObject


@allure.suite("Dashboard")
class TestDashboard:

    @allure.title("Overview page loads with all stat cards")
    def test_overview_loads(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)

        with allure.step("Navigate to Overview"):
            overview.navigate()

        with allure.step("Assert heading visible"):
            overview.assert_loaded()

        with allure.step("Assert stat cards visible"):
            overview.assert_stats_visible()

    @allure.title("Health status card displays service statuses")
    def test_health_card(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()

        with allure.step("Wait for health card to populate"):
            authenticated_page.wait_for_timeout(3_000)
            overview.assert_health_status_visible()

        with allure.step("Assert DB and Redis services shown"):
            expect(authenticated_page.locator("text=database")).to_be_visible()
            expect(authenticated_page.locator("text=redis")).to_be_visible()

    @allure.title("Sidebar navigation links work correctly")
    def test_sidebar_navigation(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()
        overview.assert_loaded()

        nav_items = [
            ("/products",  "Products"),
            ("/sellers",   "Sellers"),
            ("/analytics", "Analytics"),
            ("/jobs",      "Jobs"),
            ("/scraping",  "Scraping Control"),
        ]

        for path, heading_text in nav_items:
            with allure.step(f"Navigate to {path}"):
                authenticated_page.locator(f'a[href="{path}"]').click()
                expect(authenticated_page.locator(f'h1:has-text("{heading_text}")')).to_be_visible(
                    timeout=6_000
                )

    @allure.title("Recent products table appears on overview")
    def test_recent_products_section(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()

        with allure.step("Assert Recent Products card visible"):
            expect(authenticated_page.locator('text=Recent Products')).to_be_visible(timeout=6_000)

    @allure.title("Page title matches brand name")
    def test_page_title(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()

        with allure.step("Assert document title contains platform name"):
            expect(authenticated_page).to_have_title("Scraping Platform")

    @allure.title("Overview auto-refreshes health without user action")
    def test_health_auto_refresh(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()

        with allure.step("Wait 20s for at least one polling cycle"):
            # Health polls every 15s — capture network request
            with authenticated_page.expect_request(
                lambda r: "/health" in r.url, timeout=20_000
            ) as req_info:
                pass  # just waiting for the request

        with allure.step("Assert health endpoint was polled"):
            assert req_info.value is not None
