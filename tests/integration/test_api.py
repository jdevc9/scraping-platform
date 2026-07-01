import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@test.com", "password": "password123", "role": "viewer"},
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == "new@test.com"

    # Login
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": "new@test.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_products_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/products")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_and_get_product(client: AsyncClient, auth_headers: dict):
    # Create
    create = await client.post(
        "/api/v1/products",
        json={
            "external_id": "shopee-12345",
            "marketplace": "shopee",
            "title": "Test Product",
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    # Get by ID
    get = await client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
    assert get.status_code == 200
    assert get.json()["title"] == "Test Product"

    # List
    lst = await client.get("/api/v1/products", headers=auth_headers)
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1


@pytest.mark.asyncio
async def test_duplicate_product_returns_409(client: AsyncClient, auth_headers: dict):
    payload = {"external_id": "dup-001", "marketplace": "jdcom", "title": "Dup Product"}
    r1 = await client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert r2.status_code == 409
