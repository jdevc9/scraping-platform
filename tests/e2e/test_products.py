"""
E2E tests — Products page: listing, search, filters, detail drawer.
"""
import allure
import httpx
from playwright.sync_api import Page, expect
from tests.e2e.pages import ProductsPageObject
from tests.e2e.conftest import API_PREFIX


@allure.suite("Products")
class TestProductsPage:

    @allure.title("Products page loads and shows table")
    def test_page_loads(self, authenticated_page: Page):
        products = ProductsPageObject(authenticated_page)

        with allure.step("Navigate to /products"):
            products.navigate()

        with allure.step("Assert page heading visible"):
            products.assert_loaded()

        with allure.step("Assert table header columns visible"):
            for col in ["Product", "Marketplace", "Price", "Stock"]:
                expect(authenticated_page.locator(f'th:has-text("{col}")')).to_be_visible()

    @allure.title("Search filters products by title")
    def test_search_filters_results(self, authenticated_page: Page, seed_product):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        with allure.step("Search for the seeded product title"):
            products.search("E2E Test Product")

        with allure.step("Assert at least one matching row appears"):
            expect(
                authenticated_page.locator('td:has-text("E2E Test Product")')
            ).to_be_visible(timeout=6_000)

    @allure.title("Search with no matches shows empty state")
    def test_search_empty_state(self, authenticated_page: Page):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        with allure.step("Search for something that won't exist"):
            products.search("zzzzzz-product-that-does-not-exist-xyz")

        with allure.step("Assert empty state message"):
            products.assert_empty_state()

    @allure.title("Marketplace filter shows only filtered results")
    def test_marketplace_filter(self, authenticated_page: Page):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        with allure.step("Filter by Shopee"):
            products.filter_marketplace("shopee")

        with allure.step("Assert all visible badges are 'Shopee'"):
            authenticated_page.wait_for_timeout(500)
            badges = authenticated_page.locator('td span:has-text("Shopee")')
            jd_badges = authenticated_page.locator('td span:has-text("JD.com")')
            # If any rows visible, none should be JD.com
            if badges.count() > 0:
                expect(jd_badges).to_have_count(0)

    @allure.title("Clicking a product row opens the detail drawer")
    def test_product_drawer_opens(self, authenticated_page: Page, seed_product):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        with allure.step("Search for seeded product"):
            products.search("E2E Test Product")
            authenticated_page.wait_for_timeout(600)

        with allure.step("Click first product row"):
            products.click_first_product()

        with allure.step("Assert drawer opens with price section"):
            products.assert_drawer_open()

    @allure.title("Product drawer has Scrape Now button")
    def test_drawer_scrape_button(self, authenticated_page: Page, seed_product):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        products.search("E2E Test Product")
        authenticated_page.wait_for_timeout(600)
        products.click_first_product()
        products.assert_drawer_open()

        with allure.step("Assert Scrape now button visible in drawer"):
            expect(authenticated_page.locator('button:has-text("Scrape now")')).to_be_visible()

    @allure.title("Drawer closes when clicking backdrop")
    def test_drawer_closes_on_backdrop(self, authenticated_page: Page, seed_product):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        products.search("E2E Test Product")
        authenticated_page.wait_for_timeout(600)
        products.click_first_product()
        products.assert_drawer_open()

        with allure.step("Click drawer backdrop to close"):
            # The backdrop is the first child div of the fixed overlay
            authenticated_page.locator('.fixed.inset-0 > div').first.click()

        with allure.step("Assert drawer is gone"):
            expect(
                authenticated_page.locator('text=Current price')
            ).not_to_be_visible(timeout=3_000)

    @allure.title("Pagination controls appear when there are multiple pages")
    def test_pagination_visible(self, authenticated_page: Page, api_client: httpx.Client):
        products = ProductsPageObject(authenticated_page)
        products.navigate()
        products.assert_loaded()

        with allure.step("Check total count from API"):
            resp = api_client.get("/products?page=1&page_size=1")
            total = resp.json().get("total", 0)

        if total > 20:
            with allure.step("Assert pagination visible for large result sets"):
                expect(authenticated_page.locator('text=Page 1 of')).to_be_visible()
        else:
            pytest.skip("Not enough products to test pagination (need >20)")
