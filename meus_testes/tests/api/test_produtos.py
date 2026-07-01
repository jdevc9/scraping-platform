import requests
import pytest

def test_listar_sem_auth_retorna_401(base_url):
    r = requests.get(f"{base_url}/products")
    assert r.status_code == 401

def test_listar_com_auth_retorna_200(base_url, headers):
    r = requests.get(f"{base_url}/products", headers=headers)
    assert r.status_code == 200

def test_resposta_tem_paginacao(base_url, headers):
    r = requests.get(f"{base_url}/products", headers=headers)
    dados = r.json()
    for campo in ["items", "total", "page", "pages", "page_size"]:
        assert campo in dados, f"Campo '{campo}' não encontrado na resposta"

def test_id_invalido_retorna_404(base_url, headers):
    r = requests.get(
        f"{base_url}/products/00000000-0000-0000-0000-000000000000",
        headers=headers
    )
    assert r.status_code == 404

def test_criar_produto_retorna_201(base_url, headers):
    payload = {
        "external_id": f"auto-teste-001",
        "marketplace": "shopee",
        "title": "Produto Criado pelo Teste"
    }
    r = requests.post(f"{base_url}/products", json=payload, headers=headers)
    assert r.status_code in [201, 409]
    if r.status_code == 201:
        assert r.json()["title"] == "Produto Criado pelo Teste"
        assert r.json()["marketplace"] == "shopee"

def test_produto_duplicado_retorna_409(base_url, headers):
    payload = {
        "external_id": "duplicado-garantido-999",
        "marketplace": "jdcom",
        "title": "Teste de Duplicata"
    }
    requests.post(f"{base_url}/products", json=payload, headers=headers)
    r = requests.post(f"{base_url}/products", json=payload, headers=headers)
    assert r.status_code == 409

@pytest.mark.parametrize("marketplace", ["shopee", "jdcom"])
def test_filtrar_por_marketplace(base_url, headers, marketplace):
    r = requests.get(
        f"{base_url}/products",
        params={"marketplace": marketplace},
        headers=headers
    )
    assert r.status_code == 200
