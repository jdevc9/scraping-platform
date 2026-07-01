"""
Integration tests for /api/v1/scraping/* endpoints.
Celery tasks are mocked — we test the HTTP layer only.
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_marketplaces(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/scraping/marketplaces", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "marketplaces" in data
    assert "shopee" in data["marketplaces"]
    assert "jdcom" in data["marketplaces"]


@pytest.mark.asyncio
async def test_trigger_product_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    response = await client.post(
        "/api/v1/scraping/trigger/product",
        json={"product_id": fake_id},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_product_queues_task(client: AsyncClient, auth_headers: dict):
    # Create a product first
    create = await client.post(
        "/api/v1/products",
        json={
            "external_id": "99.88",
            "marketplace": "shopee",
            "title": "Scrape Me",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    # Mock Celery task to avoid real broker
    mock_task = MagicMock()
    mock_task.id = "mock-task-id-123"

    with patch("app.tasks.scrape_tasks.scrape_product.apply_async", return_value=mock_task):
        response = await client.post(
            "/api/v1/scraping/trigger/product",
            json={"product_id": product_id},
            headers=auth_headers,
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["task_id"] == "mock-task-id-123"


@pytest.mark.asyncio
async def test_trigger_marketplace_valid(client: AsyncClient, auth_headers: dict):
    mock_task = MagicMock()
    mock_task.id = "marketplace-task-999"

    with patch("app.tasks.scrape_tasks.trigger_marketplace_scrape.apply_async", return_value=mock_task):
        response = await client.post(
            "/api/v1/scraping/trigger/marketplace?marketplace=shopee",
            headers=auth_headers,
        )

    assert response.status_code == 202
    assert response.json()["task_id"] == "marketplace-task-999"


@pytest.mark.asyncio
async def test_trigger_marketplace_invalid(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/scraping/trigger/marketplace?marketplace=taobao",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Unknown marketplace" in response.json()["detail"]


@pytest.mark.asyncio
async def test_search_and_track(client: AsyncClient, auth_headers: dict):
    mock_task = MagicMock()
    mock_task.id = "search-task-777"

    with patch("app.tasks.scrape_tasks.search_and_track.apply_async", return_value=mock_task):
        response = await client.post(
            "/api/v1/scraping/search",
            json={"marketplace": "jdcom", "keyword": "xiaomi", "max_results": 10},
            headers=auth_headers,
        )

    assert response.status_code == 202
    assert response.json()["task_id"] == "search-task-777"


@pytest.mark.asyncio
async def test_search_unknown_marketplace(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/scraping/search",
        json={"marketplace": "aliexpress", "keyword": "phone"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_task_status(client: AsyncClient, auth_headers: dict):
    mock_result = MagicMock()
    mock_result.status = "SUCCESS"
    mock_result.ready.return_value = True
    mock_result.result = {"product_id": "abc", "price": 99.0}
    mock_result.failed.return_value = False
    mock_result.traceback = None

    with patch("app.api.routes.scraping.AsyncResult", return_value=mock_result):
        with patch("app.api.routes.scraping.celery_app", MagicMock()):
            response = await client.get(
                "/api/v1/scraping/task/some-task-id",
                headers=auth_headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_scraping_routes_require_auth(client: AsyncClient):
    """All scraping endpoints must reject unauthenticated requests."""
    endpoints = [
        ("GET", "/api/v1/scraping/marketplaces"),
        ("POST", "/api/v1/scraping/trigger/product"),
        ("POST", "/api/v1/scraping/trigger/marketplace"),
        ("POST", "/api/v1/scraping/search"),
    ]
    for method, path in endpoints:
        if method == "GET":
            r = await client.get(path)
        else:
            r = await client.post(path, json={})
        assert r.status_code == 401, f"Expected 401 for {method} {path}, got {r.status_code}"
