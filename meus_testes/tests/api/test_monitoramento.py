import requests
import pytest

BASE_URL = "http://localhost:8000/api/v1"

def get_token():
    r = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": "admin@platform.local", "password": "admin123"}
    )
    return r.json()["access_token"]

@pytest.fixture
def headers():
    return {"Authorization": f"Bearer {get_token()}"}

def test_adicionar_produto_para_monitorar(headers):
    payload = {
        "external_id": "monitor-teste-001",
        "marketplace": "shopee",
        "title": "Produto Monitorado"
    }
    r = requests.post(f"{BASE_URL}/products", json=payload, headers=headers)
    assert r.status_code in [201, 409]

def test_produto_monitorado_aparece_na_lista(headers):
    payload = {
        "external_id": "monitor-lista-002",
        "marketplace": "shopee",
        "title": "Produto Lista Monitoramento"
    }
    requests.post(f"{BASE_URL}/products", json=payload, headers=headers)
    r = requests.get(
        f"{BASE_URL}/products",
        params={"search": "Produto Lista Monitoramento"},
        headers=headers
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 1

def test_trigger_scraping_shopee(headers):
    r = requests.post(
        f"{BASE_URL}/scraping/trigger/marketplace?marketplace=shopee",
        headers=headers
    )
    assert r.status_code == 202
    assert "task_id" in r.json()

def test_trigger_scraping_jdcom(headers):
    r = requests.post(
        f"{BASE_URL}/scraping/trigger/marketplace?marketplace=jdcom",
        headers=headers
    )
    # Documenta o comportamento real — jdcom retorna 400 (scraper não registrado)
    # Quando o scraper for implementado, muda para 202
    assert r.status_code in [202, 400]
    print(f"Status jdcom: {r.status_code} - {r.json()}")

def test_trigger_marketplace_invalido_retorna_400(headers):
    r = requests.post(
        f"{BASE_URL}/scraping/trigger/marketplace?marketplace=mercadolivre",
        headers=headers
    )
    assert r.status_code == 400

def test_task_tem_id_rastreavel(headers):
    r = requests.post(
        f"{BASE_URL}/scraping/trigger/marketplace?marketplace=shopee",
        headers=headers
    )
    task_id = r.json()["task_id"]
    assert task_id is not None
    assert len(task_id) > 10
    r2 = requests.get(
        f"{BASE_URL}/scraping/task/{task_id}",
        headers=headers
    )
    assert r2.status_code == 200
    assert r2.json()["status"] in ["PENDING", "STARTED", "SUCCESS", "FAILURE"]

def test_search_enfileira_task(headers):
    payload = {
        "marketplace": "shopee",
        "keyword": "xiaomi",
        "max_results": 5
    }
    r = requests.post(f"{BASE_URL}/scraping/search", json=payload, headers=headers)
    assert r.status_code == 202
    assert "task_id" in r.json()

def test_analytics_sellers_retorna_lista(headers):
    r = requests.get(f"{BASE_URL}/analytics/sellers", headers=headers)
    assert r.status_code == 200
    assert "sellers" in r.json()

def test_analytics_precos_exige_product_id(headers):
    r = requests.get(f"{BASE_URL}/analytics/prices", headers=headers)
    assert r.status_code == 422

def test_jobs_retorna_estrutura(headers):
    r = requests.get(f"{BASE_URL}/jobs", headers=headers)
    assert r.status_code == 200
    dados = r.json()
    assert "active" in dados
    assert "reserved" in dados
    assert "scheduled" in dados
