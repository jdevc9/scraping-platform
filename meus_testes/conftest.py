import pytest
import requests

BASE_URL = "http://localhost:8000/api/v1"

@pytest.fixture(scope="session")  # roda UMA VEZ para toda a sessão
def token():
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "admin@platform.local", "password": "admin123"}
    )
    assert response.status_code == 200, "Login falhou — backend está no ar?"
    return response.json()["access_token"]

@pytest.fixture(scope="session")
def headers(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def base_url():
    return BASE_URL
