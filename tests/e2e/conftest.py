"""
E2E test fixtures using Playwright.

Prerequisites — stack must be running before executing:
    make up           # starts docker compose
    make migrate      # creates DB tables
    make seed         # creates admin@platform.local / admin123

Or use the all-in-one target:
    make e2e-up       # starts stack, waits for health, then runs tests
"""
import os
import time
import httpx
import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_URL     = os.getenv("BASE_URL",     "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
E2E_EMAIL    = os.getenv("E2E_EMAIL",    "admin@platform.local")
E2E_PASS     = os.getenv("E2E_PASS",     "admin123")
API_PREFIX   = f"{BASE_URL}/api/v1"


# ── Stack readiness check ─────────────────────────────────────────────────────

def _is_reachable(url: str, timeout: int = 15) -> tuple[bool, str]:
    """Returns (ok, error_message). Never raises."""
    deadline = time.time() + timeout
    last_error = "timeout"
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code < 500:
                return True, ""
        except Exception as e:
            last_error = str(e)
        time.sleep(1)
    return False, last_error


def pytest_sessionstart(session: pytest.Session) -> None:  # type: ignore[name-defined]
    """
    Called once before any tests. Uses pytest.exit() — NOT raise —
    so pytest shuts down cleanly instead of producing INTERNALERROR.
    """
    ok, err = _is_reachable(f"{API_PREFIX}/health")
    if not ok:
        pytest.exit(
            reason=(
                f"\n\n{'='*60}\n"
                f"  Backend API not reachable at {API_PREFIX}/health\n"
                f"  Error: {err}\n\n"
                f"  Start the stack first:\n"
                f"    make up && make migrate && make seed\n"
                f"  Then re-run:  make e2e\n"
                f"  Or use:       make e2e-up  (does everything)\n"
                f"{'='*60}\n"
            ),
            returncode=1,
        )

    ok, err = _is_reachable(FRONTEND_URL)
    if not ok:
        pytest.exit(
            reason=(
                f"\n\n{'='*60}\n"
                f"  Frontend not reachable at {FRONTEND_URL}\n"
                f"  Error: {err}\n\n"
                f"  Make sure the frontend container is running:\n"
                f"    docker compose ps\n"
                f"{'='*60}\n"
            ),
            returncode=1,
        )

    print(f"\n[e2e] Backend ✓  Frontend ✓  Stack is ready.\n")


# ── Playwright fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def api_token() -> str:
    """Get JWT once per session via API login."""
    resp = httpx.post(
        f"{API_PREFIX}/auth/token",
        data={"username": E2E_EMAIL, "password": E2E_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"Login failed ({resp.status_code}). "
        f"Did you run 'make seed' to create the admin user?\n{resp.text}"
    )
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def api_client(api_token: str) -> httpx.Client:
    """Authenticated HTTPX client for direct API operations."""
    return httpx.Client(
        base_url=API_PREFIX,
        headers={"Authorization": f"Bearer {api_token}"},
        timeout=15,
    )


@pytest.fixture
def context(browser_instance: Browser) -> BrowserContext:
    ctx = browser_instance.new_context(
        viewport={"width": 1280, "height": 800},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext) -> Page:
    p = context.new_page()
    yield p
    p.close()


@pytest.fixture
def authenticated_page(context: BrowserContext, api_token: str) -> Page:
    """Page with JWT pre-injected into localStorage — skips the login form."""
    p = context.new_page()
    p.goto(FRONTEND_URL)
    p.evaluate(f"localStorage.setItem('access_token', '{api_token}')")
    yield p
    p.close()


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def seed_product(api_client: httpx.Client):
    """Create a test product via API. 409 = already exists (idempotent)."""
    resp = api_client.post("/products", json={
        "external_id": "e2e-test-99.88",
        "marketplace": "shopee",
        "title": "E2E Test Product",
        "url": "https://shopee.com.br/test-i.99.88",
    })
    if resp.status_code not in (201, 409):
        pytest.fail(f"Failed to seed product: {resp.status_code} {resp.text}")
    yield resp.json() if resp.status_code == 201 else {"id": None, "title": "E2E Test Product"}
