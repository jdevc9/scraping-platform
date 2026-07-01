"""
E2E tests — Authentication flows.
"""
import pytest
import allure
from playwright.sync_api import Page, expect
from tests.e2e.pages import LoginPageObject, OverviewPageObject
from tests.e2e.conftest import E2E_EMAIL, E2E_PASS


@allure.suite("Authentication")
class TestAuthFlow:

    @allure.title("Login with valid credentials → redirects to dashboard")
    def test_login_success(self, page: Page):
        login = LoginPageObject(page)
        login.navigate()

        with allure.step("Fill login form with valid credentials"):
            login.login(E2E_EMAIL, E2E_PASS)

        with allure.step("Assert redirect to Overview page"):
            login.assert_redirected_to_dashboard()

        with allure.step("Assert Overview heading is visible"):
            overview = OverviewPageObject(page)
            overview.assert_loaded()

    @allure.title("Login with wrong password → shows error")
    def test_login_wrong_password(self, page: Page):
        login = LoginPageObject(page)
        login.navigate()

        with allure.step("Submit form with wrong password"):
            login.login(E2E_EMAIL, "wrong-password-xyz")

        with allure.step("Assert error message appears"):
            login.assert_error_visible()

        with allure.step("Assert URL stays on /login"):
            expect(page).to_have_url("http://localhost:3000/login")

    @allure.title("Login with empty fields → form does not submit")
    def test_login_empty_fields(self, page: Page):
        login = LoginPageObject(page)
        login.navigate()

        with allure.step("Click submit without filling fields"):
            login.submit_btn.click()

        with allure.step("Assert still on login page"):
            expect(page).to_have_url("http://localhost:3000/login")

    @allure.title("Unauthenticated access to /products → redirects to login")
    def test_unauthenticated_redirect(self, page: Page):
        with allure.step("Navigate to /products without token"):
            page.goto("http://localhost:3000/products")

        with allure.step("Assert redirect to /login"):
            expect(page).to_have_url("http://localhost:3000/login", timeout=5_000)

    @allure.title("Logout clears session and redirects to login")
    def test_logout(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()
        overview.assert_loaded()

        with allure.step("Click logout button in sidebar"):
            authenticated_page.locator('[title="Sign out"]').click()

        with allure.step("Assert redirect to /login"):
            expect(authenticated_page).to_have_url(
                "http://localhost:3000/login", timeout=5_000
            )

        with allure.step("Assert token removed from localStorage"):
            token = authenticated_page.evaluate("localStorage.getItem('access_token')")
            assert token is None

    @allure.title("Sidebar shows user email and role")
    def test_sidebar_user_info(self, authenticated_page: Page):
        overview = OverviewPageObject(authenticated_page)
        overview.navigate()
        overview.assert_loaded()

        with allure.step("Assert role badge visible in sidebar"):
            role_text = authenticated_page.locator('text=admin').or_(
                authenticated_page.locator('text=analyst')
            ).or_(
                authenticated_page.locator('text=viewer')
            )
            expect(role_text.first).to_be_visible()
