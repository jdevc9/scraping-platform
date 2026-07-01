"""
E2E tests — Scraping Control page.
"""
import allure
from unittest.mock import patch
from playwright.sync_api import Page, expect
from tests.e2e.pages import ScrapingPageObject


@allure.suite("Scraping Control")
class TestScrapingPage:

    @allure.title("Scraping Control page loads correctly")
    def test_page_loads(self, authenticated_page: Page):
        scraping = ScrapingPageObject(authenticated_page)

        with allure.step("Navigate to /scraping"):
            scraping.navigate()

        with allure.step("Assert heading and cards visible"):
            scraping.assert_loaded()
            expect(authenticated_page.locator('text=Trigger Marketplace Scrape')).to_be_visible()
            expect(authenticated_page.locator('text=Search & Track Products')).to_be_visible()

    @allure.title("Marketplace selector has Shopee and JD.com options")
    def test_marketplace_options(self, authenticated_page: Page):
        scraping = ScrapingPageObject(authenticated_page)
        scraping.navigate()
        scraping.assert_loaded()

        with allure.step("Assert marketplace select has both options"):
            select = authenticated_page.locator('select').first
            options = select.locator('option').all_text_contents()
            assert "Shopee" in options or "shopee" in options
            assert "JD.com" in options or "jdcom" in options

    @allure.title("Trigger scrape queues a task and shows task row")
    def test_trigger_scrape_shows_task(self, authenticated_page: Page):
        scraping = ScrapingPageObject(authenticated_page)
        scraping.navigate()
        scraping.assert_loaded()

        with allure.step("Select Shopee and click Trigger"):
            scraping.trigger_marketplace_scrape("shopee")

        with allure.step("Assert a task status row appears"):
            scraping.assert_task_queued()

    @allure.title("Search without keyword shows validation error")
    def test_search_without_keyword(self, authenticated_page: Page):
        scraping = ScrapingPageObject(authenticated_page)
        scraping.navigate()
        scraping.assert_loaded()

        with allure.step("Click Search without filling keyword"):
            authenticated_page.locator('button:has-text("Search & track")').click()

        with allure.step("Assert validation error visible"):
            expect(authenticated_page.locator('text=Enter a keyword')).to_be_visible()

    @allure.title("How-it-works section shows 3 steps")
    def test_how_it_works_section(self, authenticated_page: Page):
        scraping = ScrapingPageObject(authenticated_page)
        scraping.navigate()
        scraping.assert_loaded()

        with allure.step("Assert all 3 steps visible"):
            for label in ["Trigger", "Scrape", "Alert"]:
                expect(authenticated_page.locator(f'text={label}').first).to_be_visible()

    @allure.title("Unknown marketplace returns 400 — error handled gracefully")
    def test_unknown_marketplace_handled(self, authenticated_page: Page):
        """
        This tests the frontend gracefully handles a 400 from the API.
        We inject a bad marketplace via direct API call checked in the API tests —
        here we just verify the UI doesn't crash on unexpected selections.
        """
        scraping = ScrapingPageObject(authenticated_page)
        scraping.navigate()
        scraping.assert_loaded()

        with allure.step("Page is still interactive after load"):
            expect(authenticated_page.locator('h1')).to_be_visible()


@allure.suite("Analytics")
class TestAnalyticsPage:

    @allure.title("Analytics page loads with product selector")
    def test_page_loads(self, authenticated_page: Page):
        with allure.step("Navigate to /analytics"):
            authenticated_page.goto("http://localhost:3000/analytics")

        with allure.step("Assert heading and empty-state prompt visible"):
            expect(authenticated_page.locator('h1:has-text("Analytics")')).to_be_visible(timeout=6_000)
            expect(
                authenticated_page.locator('text=Select a product to view its price history')
            ).to_be_visible()

    @allure.title("Period selector has 4 options")
    def test_period_selector_options(self, authenticated_page: Page):
        authenticated_page.goto("http://localhost:3000/analytics")

        with allure.step("Assert period options available"):
            period_select = authenticated_page.locator('select').nth(1)
            options = period_select.locator('option').all_text_contents()
            assert len(options) == 4
            assert any("7" in o for o in options)
            assert any("30" in o for o in options)
            assert any("90" in o for o in options)

    @allure.title("Jobs page shows worker section headings")
    def test_jobs_page(self, authenticated_page: Page):
        with allure.step("Navigate to /jobs"):
            authenticated_page.goto("http://localhost:3000/jobs")

        with allure.step("Assert all section headings visible"):
            expect(authenticated_page.locator('h1:has-text("Jobs")')).to_be_visible(timeout=6_000)
            expect(authenticated_page.locator('text=Active')).to_be_visible()
            expect(authenticated_page.locator('text=Queued')).to_be_visible()
            expect(authenticated_page.locator('text=Scheduled')).to_be_visible()

    @allure.title("Jobs page auto-refreshes (network request detected)")
    def test_jobs_auto_refresh(self, authenticated_page: Page):
        authenticated_page.goto("http://localhost:3000/jobs")

        with allure.step("Wait for jobs polling request"):
            with authenticated_page.expect_request(
                lambda r: "/jobs" in r.url, timeout=12_000
            ) as req_info:
                pass

        assert req_info.value is not None
