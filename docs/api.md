# API Documentation

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/docs` (Swagger UI)
Schema: `http://localhost:8000/api/v1/openapi.json`

---

## Authentication

All endpoints (except `/auth/token` and `/auth/register`) require a Bearer token.

### POST /auth/token
Login and receive a JWT.

**Request** (`application/x-www-form-urlencoded`)
```
username=admin@platform.local&password=admin123
```

**Response 200**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### POST /auth/register
Create a new user (admin role required to set non-viewer roles).

**Request**
```json
{
  "email": "analyst@company.com",
  "password": "strongpassword",
  "full_name": "Jane Analyst",
  "role": "analyst"
}
```

**Response 201**
```json
{
  "id": "uuid",
  "email": "analyst@company.com",
  "full_name": "Jane Analyst",
  "role": "analyst",
  "is_active": true,
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

## Products

### GET /products
List all tracked products with pagination and filters.

**Query params**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |
| `marketplace` | string | — | Filter: `shopee` or `jdcom` |
| `search` | string | — | Full-text search on title |
| `is_available` | bool | — | Filter by stock availability |

**Response 200**
```json
{
  "items": [
    {
      "id": "uuid",
      "external_id": "12345.67890",
      "marketplace": "shopee",
      "title": "iPhone 15 Pro 256GB",
      "price": 5990.00,
      "original_price": 6990.00,
      "currency": "BRL",
      "rating": 4.8,
      "reviews_count": 1500,
      "stock_quantity": 50,
      "is_available": true,
      "seller_id": "uuid",
      "last_scraped_at": "2025-01-15T09:30:00Z",
      "created_at": "2025-01-10T00:00:00Z",
      "updated_at": "2025-01-15T09:30:00Z"
    }
  ],
  "total": 247,
  "page": 1,
  "page_size": 20,
  "pages": 13
}
```

### GET /products/{id}
Get single product by UUID.

**Response 404** — `{"detail": "Product not found"}`

### POST /products
Manually add a product to tracking.

**Request**
```json
{
  "external_id": "99999.88888",
  "marketplace": "shopee",
  "title": "Samsung Galaxy S24",
  "url": "https://shopee.com.br/samsung-s24-i.99999.88888"
}
```

**Response 409** — Product already tracked.

---

## Sellers

### GET /sellers
**Query params:** `page`, `page_size`, `marketplace`

**Response 200** — Paginated `SellerRead` list.

### GET /sellers/{id}
Single seller by UUID.

---

## Analytics

### GET /analytics/prices
Price history for a product.

**Query params**
| Param | Required | Description |
|-------|----------|-------------|
| `product_id` | ✓ | Product UUID |
| `days` | — | 1-365, default 30 |

**Response 200**
```json
{
  "product_id": "uuid",
  "period_days": 30,
  "data_points": 120,
  "min_price": 4990.00,
  "max_price": 6290.00,
  "avg_price": 5487.50,
  "current_price": 5190.00,
  "history": [
    {
      "price": 5990.00,
      "scraped_at": "2025-01-01T10:00:00Z",
      "price_changed": false,
      "price_diff": null
    },
    {
      "price": 5490.00,
      "scraped_at": "2025-01-08T10:00:00Z",
      "price_changed": true,
      "price_diff": -500.00
    }
  ]
}
```

### GET /analytics/sellers
Top sellers by tracked products.

**Query params:** `marketplace`, `limit` (1-50, default 10)

---

## Scraping Control

### POST /scraping/trigger/product
Immediately queue a scrape for one product.

**Request**
```json
{ "product_id": "uuid" }
```

**Response 202**
```json
{
  "task_id": "celery-task-uuid",
  "status": "queued",
  "detail": "Scrape queued for product uuid"
}
```

### POST /scraping/trigger/marketplace
Fan-out scrape for all tracked products in a marketplace.

**Query params:** `marketplace` (required: `shopee` | `jdcom`)

**Response 202** — TriggerResponse with fan-out task ID.

### POST /scraping/search
Keyword search that discovers and tracks new products.

**Request**
```json
{
  "marketplace": "shopee",
  "keyword": "iphone 15 pro",
  "max_results": 20
}
```

### GET /scraping/task/{task_id}
Poll a Celery task result.

**Response 200**
```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": { "product_id": "uuid", "price": 5990.00, "available": true },
  "traceback": null
}
```

### GET /scraping/marketplaces
List registered marketplace scrapers.

**Response 200**
```json
{ "marketplaces": ["shopee", "jdcom"] }
```

---

## Monitoring

### GET /health
System health check.

**Response 200**
```json
{
  "status": "ok",
  "environment": "production",
  "version": "1.0.0",
  "services": {
    "database": "ok",
    "redis": "ok"
  }
}
```

### GET /jobs
Active, queued, and scheduled Celery tasks.

**Response 200**
```json
{
  "active":    { "celery@worker1": [...] },
  "reserved":  { "celery@worker1": [...] },
  "scheduled": { "celery@worker1": [...] }
}
```

---

## Error Responses

| Code | When |
|------|------|
| 400 | Bad request (invalid marketplace, missing required fields) |
| 401 | Missing or invalid JWT token |
| 403 | Insufficient role for this endpoint |
| 404 | Resource not found |
| 409 | Conflict (duplicate product) |
| 422 | Validation error (Pydantic schema failure) |
| 500 | Internal server error |

All errors return `{"detail": "human-readable message"}`.
