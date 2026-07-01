# Architecture Documentation

## System Overview

Senior Automation & Scraping Platform is a six-layer enterprise system for collecting,
processing, storing, and exposing e-commerce product data from Shopee and JD.com.

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — Scheduler & Triggers                          │
│  Celery Beat · Webhook endpoints · Manual API triggers   │
├─────────────────────────────────────────────────────────┤
│  Layer 2 — Scraping Layer                                │
│  Playwright (Shopee SPA) · Selenium+BS4 (JD.com)         │
│  Proxy rotation · User-agent spoofing · CAPTCHA handling │
├─────────────────────────────────────────────────────────┤
│  Layer 3 — Queue & Processing                            │
│  Celery Workers · Redis Broker · Change Detector         │
│  PersistenceService · Alert dispatcher                   │
├─────────────────────────────────────────────────────────┤
│  Layer 4 — Data Layer                                    │
│  PostgreSQL · SQLAlchemy async ORM · Alembic migrations  │
│  Products · PriceHistory (append-only) · Sellers · Users │
├─────────────────────────────────────────────────────────┤
│  Layer 5 — API & Dashboard                               │
│  FastAPI · JWT/RBAC · REST endpoints                     │
│  React + TypeScript + Tailwind + Recharts                │
├─────────────────────────────────────────────────────────┤
│  Layer 6 — DevOps & Observability                        │
│  Docker Compose · GitHub Actions · Jenkins               │
│  Prometheus · Grafana · Allure Reports                   │
└─────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Backend (`backend/app/`)

| Module | Responsibility |
|--------|---------------|
| `core/config.py` | All settings via pydantic-settings, sourced from env |
| `core/database.py` | Async SQLAlchemy engine + session factory |
| `core/security.py` | JWT creation/decode, bcrypt password hashing |
| `core/logging.py` | Structured JSON logging via structlog |
| `models/` | SQLAlchemy ORM models — User, Seller, Product, PriceHistory |
| `scrapers/base.py` | BaseScraper: retry logic, rate limiting, proxy injection |
| `scrapers/shopee.py` | Playwright scraper, Shopee API v4 + DOM fallback |
| `scrapers/jdcom.py` | Selenium + BS4, JSON-LD + globalThis parser |
| `scrapers/factory.py` | `@register` decorator + `get_scraper(marketplace)` |
| `scrapers/proxy.py` | ProxyPool: round-robin, health tracking, auto-disable |
| `services/persistence.py` | Upsert products/sellers, append price history on change |
| `services/change_detector.py` | Threshold-based alert event generation (no I/O) |
| `tasks/celery_app.py` | Celery config: queues, Beat schedule, serializer |
| `tasks/scrape_tasks.py` | Fan-out trigger → scrape → persist → detect → alert |
| `tasks/alert_tasks.py` | Webhook + structured log dispatch |
| `api/routes/` | FastAPI routers per domain: auth, products, sellers, analytics, monitoring, scraping |
| `api/dependencies.py` | `get_current_user`, `require_role()` dependency factories |

### Database Schema

```
users
  id UUID PK | email | hashed_password | role | is_active | timestamps

sellers
  id UUID PK | external_id | marketplace | name | score | reputation
  total_products | is_active | timestamps

products
  id UUID PK | external_id | marketplace | title | price | original_price
  currency | promotions JSON | rating | reviews_count | stock_quantity
  is_available | images JSON | sku | url | seller_id FK | last_scraped_at
  scrape_errors | timestamps

price_history                          ← append-only, never UPDATE
  id UUID PK | product_id FK | price | original_price | currency
  stock_quantity | is_available | scraped_at | price_changed | stock_changed
  price_diff
  INDEX: (product_id, scraped_at)     ← hot path for analytics queries
  INDEX: (scraped_at)                 ← range scans for cleanup jobs
```

### Scraping Architecture

**Anti-bot strategy (layered):**

1. Playwright stealth JS injection — overrides `navigator.webdriver`, spoofs plugins
2. Per-request proxy rotation via `ProxyPool` with health tracking
3. User-agent + viewport randomization from realistic device fingerprints
4. Request rate limiting (configurable min delay between requests)
5. Automatic retry with exponential backoff (Celery `max_retries=3`)
6. CAPTCHA handler interface — pluggable (2captcha, AntiCaptcha, manual)

**Shopee flow:**
```
scrape_product(external_id="shopid.itemid")
  → intercept /api/v4/item/get network request (Playwright)
  → parse JSON response (_parse_api_response)
  → fallback: _parse_dom if API blocked
```

**JD.com flow:**
```
scrape_product(external_id="item_id")
  → Selenium loads item page
  → Try 1: extract <script type="application/ld+json">  (_parse_jsonld)
  → Try 2: extract window.__INITIAL_STATE__ / globalThis  (_parse_global_data)
  → Try 3: CSS selector DOM parse  (_parse_dom)
```

### Change Detection

`ChangeDetector` is a pure function — no I/O, no Celery, no DB:

```python
events = detector.analyse(product, price_history_record)
# Returns AlertEvent list if:
#   price dropped ≥ DROP_THRESHOLD_PCT (default 5%)
#   price spiked ≥ SPIKE_THRESHOLD_PCT (default 20%)
#   stock went to 0 (out_of_stock)
#   stock came back from 0 (back_in_stock)
```

Thresholds configurable via `.env`:  `PRICE_DROP_THRESHOLD_PCT`, `PRICE_SPIKE_THRESHOLD_PCT`

### RBAC

| Role | Can do |
|------|--------|
| `admin` | All endpoints including register, trigger scrapes, view everything |
| `analyst` | Read all data, trigger scrapes, search |
| `viewer` | Read-only: products, sellers, analytics |

## Celery Queues

| Queue | Purpose | Workers |
|-------|---------|---------|
| `scraping` | `scrape_product`, `search_and_track` | Playwright/Selenium workers |
| `alerts` | `send_price_alert`, `send_stock_alert` | Lightweight alert workers |
| `default` | `trigger_marketplace_scrape` (fan-out) | General workers |

## Frontend Architecture

```
src/
  api/index.ts          ← Axios client; interceptors for JWT + 401 redirect
  types/index.ts        ← TypeScript interfaces mirroring Pydantic schemas
  hooks/
    useAuth.tsx         ← JWT context: login, logout, isRole()
    useApi.ts           ← Generic fetch hook: loading, error, pollInterval
  components/
    ui/index.tsx        ← Card, Badge, Button, Input, StatCard, etc.
    charts/             ← Recharts wrappers (PriceTrendChart)
    layout/AppLayout    ← Sidebar nav + <Outlet />
  pages/
    LoginPage           ← JWT form → localStorage
    OverviewPage        ← Health + stats + recent products
    ProductsPage        ← Table + search/filter + detail drawer
    SellersPage         ← Table + score bars + bar chart
    AnalyticsPage       ← Price trend explorer
    JobsPage            ← Live Celery worker status (polls /jobs every 5s)
    ScrapingPage        ← Trigger scrapes + task status polling
  lib/utils.ts          ← formatCurrency, formatRelative, etc.
```

## Security Considerations

- Secrets: never committed. Use `.env` locally, CI secrets for pipelines.
- JWT: HS256, 60-minute expiry (configurable). Rotate `SECRET_KEY` in production.
- Passwords: bcrypt with default work factor 12.
- Database: credentials injected at runtime, not baked into images.
- Proxies: credentials stored in env, never logged.
- CAPTCHA service key: env var only, masked in logs.
- Docker images: non-root where possible (frontend nginx).

## Performance Notes

- `price_history` composite index on `(product_id, scraped_at)` makes analytics
  queries O(log n) instead of O(n) even at 10M+ rows.
- `PersistenceService` skips writing `price_history` when nothing changed —
  keeps the table append-only and prevents runaway growth.
- Celery `max-tasks-per-child=200` prevents memory leaks from Playwright/Selenium
  browser accumulation over long-running workers.
- Frontend uses React lazy + Suspense for code splitting — initial bundle ~90KB.
- API uses async SQLAlchemy throughout request handlers (no thread blocking).
