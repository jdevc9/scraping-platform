import pytest
import requests

BASE_URL = "http://localhost:8000/api/v1"

# FIXTURE: roda uma vez, o token fica disponível para todos os testes
@pytest.fixture
def token():
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "admin@platform.local", "password": "admin123"}
    )
    return response.json()["access_token"]

# FIXTURE: headers prontos com o token
@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}

# --- TESTES DE HEALTH ---

def test_health_retorna_200():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200

def test_health_servicos_ok():
    response = requests.get(f"{BASE_URL}/health")
    dados = response.json()
    assert dados["services"]["database"] == "ok"
    assert dados["services"]["redis"] == "ok"

# --- TESTES DE AUTH ---

def test_login_valido():
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "admin@platform.local", "password": "admin123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_senha_errada():
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "admin@platform.local", "password": "senhaerrada"}
    )
    assert response.status_code == 401

def test_login_usuario_inexistente():
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "naoexiste@test.com", "password": "qualquer"}
    )
    assert response.status_code == 401

# --- TESTES DE PRODUTOS ---

def test_produtos_sem_token():
    response = requests.get(f"{BASE_URL}/products")
    assert response.status_code == 401

def test_produtos_retorna_paginacao(headers):  # recebe headers via fixture
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    assert response.status_code == 200
    dados = response.json()
    assert "items" in dados
    assert "total" in dados
    assert "page" in dados
    assert "pages" in dados

def test_produto_inexistente_retorna_404(headers):
    response = requests.get(
        f"{BASE_URL}/products/00000000-0000-0000-0000-000000000000",
        headers=headers
    )
    assert response.status_code == 404

def test_criar_produto(headers):
    payload = {
        "external_id": "teste-123",
        "marketplace": "shopee",
        "title": "Produto de Teste Automatizado"
    }
    response = requests.post(
        f"{BASE_URL}/products",
        json=payload,
        headers=headers
    )
    # 201 = criado, 409 = já existe (ambos são válidos aqui)
    assert response.status_code in [201, 409]

def test_criar_produto_duplicado_retorna_409(headers):
    payload = {
        "external_id": "produto-duplicado-xyz",
        "marketplace": "shopee",
        "title": "Produto Duplicado"
    }
    # Cria pela primeira vez
    requests.post(f"{BASE_URL}/products", json=payload, headers=headers)
    # Tenta criar de novo
    response = requests.post(
        f"{BASE_URL}/products",
        json=payload,
        headers=headers
    )
    assert response.status_code == 409

# --- TESTES DE SELLERS ---

def test_sellers_retorna_lista(headers):
    response = requests.get(f"{BASE_URL}/sellers", headers=headers)
    assert response.status_code == 200
    assert "items" in response.json()
