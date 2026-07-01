import requests

def test_login_retorna_token(base_url):
    r = requests.post(
        f"{base_url}/auth/token",
        data={"username": "admin@platform.local", "password": "admin123"}
    )
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json()["token_type"] == "bearer"

def test_login_senha_errada_retorna_401(base_url):
    r = requests.post(
        f"{base_url}/auth/token",
        data={"username": "admin@platform.local", "password": "errada"}
    )
    assert r.status_code == 401

def test_login_usuario_inexistente_retorna_401(base_url):
    r = requests.post(
        f"{base_url}/auth/token",
        data={"username": "fantasma@test.com", "password": "qualquer"}
    )
    assert r.status_code == 401
