"""
E2E API Contract Tests — validates the live API matches expected response shapes.
Uses httpx directly (no browser) with a real running stack.
"""
import allure
import httpx
import pytest
from tests.e2e.conftest import API_PREFIX


@allure.suite("API Contracts")
class TestAPIContracts:

    @allure.title("GET /health returns correct shape")
    def test_health_shape(self, api_client: httpx.Client):
        with allure.step("Call /health"):
            resp = api_client.get("/health")

        with allure.step("Assert 200 and required fields"):
            assert resp.status_code == 200
            body = resp.json()
            assert "status" in body
            assert body["status"] in ("ok", "degraded")
            assert "services" in body
            assert "database" in body["services"]
            assert "redis" in body["services"]

    @allure.title("GET /products returns paginated shape")
    def test_products_pagination_shape(self, api_client: httpx.Client):
        resp = api_client.get("/products?page=1&page_size=5")
        assert resp.status_code == 200
        body = resp.json()
        for field in ("items", "total", "page", "page_size", "pages"):
            assert field in body, f"Missing field: {field}"
        assert isinstance(body["items"], list)
        assert body["page"] == 1
        assert body["page_size"] == 5

    @allure.title("GET /products with search returns filtered results")
    def test_products_search(self, api_client: httpx.Client):
        resp = api_client.get("/products?search=E2E+Test+Product")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        for item in body["items"]:
            assert "E2E Test Product" in item["title"] or item["title"]

    @allure.title("POST /products with duplicate returns 409")
    def test_products_duplicate_409(self, api_client: httpx.Client):
        payload = {
            "external_id": "contract-test-dupe-001",
            "marketplace": "shopee",
            "title": "Contract Test Product",
        }
        r1 = api_client.post("/products", json=payload)
        assert r1.status_code in (201, 409)

        if r1.status_code == 201:
            r2 = api_client.post("/products", json=payload)
            assert r2.status_code == 409

    @allure.title("GET /products/{id} with unknown ID returns 404")
    def test_product_not_found(self, api_client: httpx.Client):
        import uuid
        resp = api_client.get(f"/products/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "detail" in resp.json()

    @allure.title("GET /sellers returns paginated sellers")
    def test_sellers_shape(self, api_client: httpx.Client):
        resp = api_client.get("/sellers")
        assert resp.status_code == 200
        body = resp.json()
        for field in ("items", "total", "page", "pages"):
            assert field in body

    @allure.title("GET /analytics/prices requires product_id param")
    def test_analytics_prices_missing_param(self, api_client: httpx.Client):
        resp = api_client.get("/analytics/prices")
        assert resp.status_code == 422  # Unprocessable Entity

    @allure.title("GET /analytics/sellers returns seller list")
    def test_analytics_sellers_shape(self, api_client: httpx.Client):
        resp = api_client.get("/analytics/sellers")
        assert resp.status_code == 200
        body = resp.json()
        assert "sellers" in body
        assert isinstance(body["sellers"], list)

    @allure.title("GET /scraping/marketplaces returns known marketplaces")
    def test_scraping_marketplaces(self, api_client: httpx.Client):
        resp = api_client.get("/scraping/marketplaces")
        assert resp.status_code == 200
        body = resp.json()
        assert "marketplaces" in body
        assert "shopee" in body["marketplaces"]
        assert "jdcom" in body["marketplaces"]

    @allure.title("POST /scraping/trigger/marketplace with unknown marketplace → 400")
    def test_scraping_unknown_marketplace(self, api_client: httpx.Client):
        resp = api_client.post("/scraping/trigger/marketplace?marketplace=aliexpress")
        assert resp.status_code == 400
        assert "Unknown marketplace" in resp.json()["detail"]

    @allure.title("Unauthenticated requests return 401")
    def test_unauthenticated_returns_401(self):
        client = httpx.Client(base_url=API_PREFIX, timeout=10)
        endpoints = ["/products", "/sellers", "/analytics/sellers", "/scraping/marketplaces"]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 401, f"Expected 401 for {ep}, got {resp.status_code}"

    @allure.title("POST /auth/token with wrong credentials returns 401")
    def test_login_wrong_credentials(self):
        client = httpx.Client(base_url=API_PREFIX, timeout=10)
        resp = client.post(
            "/auth/token",
            data={"username": "noone@nowhere.com", "password": "badpass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401
