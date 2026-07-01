import requests

def test_health_status_ok(base_url):
    r = requests.get(f"{base_url}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_health_database_ok(base_url):
    r = requests.get(f"{base_url}/health")
    assert r.json()["services"]["database"] == "ok"

def test_health_redis_ok(base_url):
    r = requests.get(f"{base_url}/health")
    assert r.json()["services"]["redis"] == "ok"
