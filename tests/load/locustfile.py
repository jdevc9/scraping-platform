"""
Load tests — Locust
====================
Tests the platform under concurrent load with three user profiles:

  APIUser       — programmatic API client (most common in production)
  DashboardUser — simulates a browser user navigating the dashboard
  ScrapeTrigger — ops user triggering scrape jobs

Run modes:
  # Dev smoke test (20 users, 30 seconds)
  locust -f tests/load/locustfile.py --headless -u 20 -r 5 -t 30s --host http://localhost:8000

  # CI load test
  locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 60s --host http://localhost:8000 \
    --csv tests/load/results --html tests/load/report.html --exit-code-on-error 1

  # Interactive UI
  locust -f tests/load/locustfile.py --host http://localhost:8000
"""
import random
import json
import os
from locust import HttpUser, TaskSet, task, between, events
from locust.exception import RescheduleTask

# ── Credentials ───────────────────────────────────────────────────────────────

LOAD_EMAIL = os.getenv("LOAD_TEST_EMAIL", "admin@platform.local")
LOAD_PASS  = os.getenv("LOAD_TEST_PASS",  "admin123")
API_PREFIX = "/api/v1"


# ── Auth mixin ────────────────────────────────────────────────────────────────

class AuthMixin:
    """Logs in once on_start and sets Authorization header."""
    token: str = ""

    def on_start(self):
        resp = self.client.post(
            f"{API_PREFIX}/auth/token",
            data={"username": LOAD_EMAIL, "password": LOAD_PASS},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise RescheduleTask()
        self.token = resp.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


# ── Task sets ─────────────────────────────────────────────────────────────────

class ProductTasks(TaskSet):
    """Read-heavy product operations."""

    product_ids: list[str] = []

    def on_start(self):
        # Pre-fetch some product IDs to use in detail requests
        resp = self.client.get(f"{API_PREFIX}/products?page_size=20")
        if resp.status_code == 200:
            self.product_ids = [p["id"] for p in resp.json().get("items", [])]

    @task(5)
    def list_products(self):
        page = random.randint(1, 3)
        self.client.get(
            f"{API_PREFIX}/products?page={page}&page_size=20",
            name="/products [list]",
        )

    @task(3)
    def search_products(self):
        keywords = ["phone", "laptop", "headphone", "watch", "tablet"]
        kw = random.choice(keywords)
        self.client.get(
            f"{API_PREFIX}/products?search={kw}",
            name="/products [search]",
        )

    @task(2)
    def get_product_detail(self):
        if not self.product_ids:
            return
        pid = random.choice(self.product_ids)
        self.client.get(
            f"{API_PREFIX}/products/{pid}",
            name="/products/{id}",
        )

    @task(1)
    def filter_by_marketplace(self):
        mkt = random.choice(["shopee", "jdcom"])
        self.client.get(
            f"{API_PREFIX}/products?marketplace={mkt}&page_size=20",
            name="/products [filter:marketplace]",
        )

    @task(1)
    def stop(self):
        self.interrupt()


class AnalyticsTasks(TaskSet):
    """Analytics endpoint load."""

    product_ids: list[str] = []

    def on_start(self):
        resp = self.client.get(f"{API_PREFIX}/products?page_size=10")
        if resp.status_code == 200:
            self.product_ids = [p["id"] for p in resp.json().get("items", [])]

    @task(3)
    def price_analytics(self):
        if not self.product_ids:
            return
        pid = random.choice(self.product_ids)
        days = random.choice([7, 14, 30, 90])
        self.client.get(
            f"{API_PREFIX}/analytics/prices?product_id={pid}&days={days}",
            name="/analytics/prices",
        )

    @task(2)
    def seller_analytics(self):
        mkt = random.choice(["shopee", "jdcom", ""])
        params = f"?marketplace={mkt}" if mkt else ""
        self.client.get(
            f"{API_PREFIX}/analytics/sellers{params}",
            name="/analytics/sellers",
        )

    @task(1)
    def stop(self):
        self.interrupt()


class MonitoringTasks(TaskSet):
    """Monitoring endpoints — health + jobs."""

    @task(4)
    def health_check(self):
        with self.client.get(
            f"{API_PREFIX}/health",
            name="/health",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health returned {resp.status_code}")
            elif resp.json().get("status") == "degraded":
                resp.failure("System degraded")

    @task(1)
    def jobs_check(self):
        self.client.get(f"{API_PREFIX}/jobs", name="/jobs")

    @task(1)
    def stop(self):
        self.interrupt()


# ── User profiles ─────────────────────────────────────────────────────────────

class APIUser(AuthMixin, HttpUser):
    """
    Typical programmatic API consumer.
    Splits time between products, analytics, and monitoring.
    """
    weight      = 60
    wait_time   = between(0.5, 2.0)

    tasks = {
        ProductTasks:    5,
        AnalyticsTasks:  3,
        MonitoringTasks: 2,
    }

    def on_start(self):
        AuthMixin.on_start(self)


class DashboardUser(AuthMixin, HttpUser):
    """
    Browser dashboard user — navigates between pages.
    Heavier on analytics since the dashboard polls charts.
    """
    weight    = 30
    wait_time = between(1.5, 5.0)

    tasks = {
        ProductTasks:    3,
        AnalyticsTasks:  5,
        MonitoringTasks: 2,
    }

    def on_start(self):
        AuthMixin.on_start(self)

    @task
    def list_sellers(self):
        self.client.get(f"{API_PREFIX}/sellers?page_size=20", name="/sellers [list]")


class ScrapeTrigger(AuthMixin, HttpUser):
    """
    Operations user triggering scrapes.
    Lower frequency — scraping is expensive.
    """
    weight    = 10
    wait_time = between(10, 30)

    def on_start(self):
        AuthMixin.on_start(self)

    @task(3)
    def list_marketplaces(self):
        self.client.get(f"{API_PREFIX}/scraping/marketplaces", name="/scraping/marketplaces")

    @task(1)
    def trigger_shopee(self):
        self.client.post(
            f"{API_PREFIX}/scraping/trigger/marketplace?marketplace=shopee",
            name="/scraping/trigger/marketplace",
        )


# ── Custom event hooks ────────────────────────────────────────────────────────

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Flag any 5xx responses as failures regardless of locust's detection."""
    if hasattr(response, "status_code") and response.status_code >= 500:
        response.failure(f"Server error: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n🚀 Load test starting — target: {environment.host}")
    print(f"   Users: {environment.runner.target_user_count if environment.runner else '?'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.runner.stats.total if environment.runner else None
    if stats:
        print(f"\n📊 Load test complete")
        print(f"   Requests:     {stats.num_requests}")
        print(f"   Failures:     {stats.num_failures}")
        print(f"   Avg response: {stats.avg_response_time:.0f}ms")
        print(f"   95th pct:     {stats.get_response_time_percentile(0.95):.0f}ms")
        print(f"   RPS:          {stats.current_rps:.1f}")
