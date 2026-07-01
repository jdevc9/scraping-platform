.PHONY: up down build logs shell test lint migrate seed

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up -d --build
	@echo ""
	@echo "Waiting for backend to be ready..."
	@sleep 5
	@timeout 60 bash -c 'until curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; do sleep 3; done' \
		|| (echo "Backend not healthy. Check: docker compose logs backend" && exit 1)
	@echo "Running migrations..."
	docker compose exec -w /app backend alembic upgrade head
	@echo ""
	@echo "✓ Platform running"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  Flower:    http://localhost:5555"
	@echo "  Grafana:   http://localhost:3001"

down:
	docker compose down

down-clean:
	docker compose down -v

build:
	docker compose build --no-cache

logs:
	docker compose logs -f backend

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	docker compose exec -w /app backend alembic upgrade head

seed:
	docker compose exec -w /app backend python -c "\
import asyncio; \
from sqlalchemy import select; \
from app.core.database import AsyncSessionLocal; \
from app.models.user import User, UserRole; \
from app.core.security import hash_password; \
async def seed(): \
    async with AsyncSessionLocal() as db: \
        existing = (await db.execute(select(User).where(User.email == 'admin@platform.local'))).scalar_one_or_none(); \
        print('Admin already exists') if existing else [db.add(User(email='admin@platform.local', hashed_password=hash_password('admin123'), full_name='Admin', role=UserRole.admin)), await db.commit(), print('Seeded: admin@platform.local / admin123')]; \
asyncio.run(seed())"

shell:
	docker compose exec -w /app backend bash

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	docker compose exec -w /app backend pytest ../tests/ -v

# ── Frontend ──────────────────────────────────────────────────────────────────
fe-dev:
	cd frontend && npm run dev

fe-install:
	cd frontend && npm ci

fe-build:
	cd frontend && npm run build

# ── E2E ───────────────────────────────────────────────────────────────────────
e2e:
	BASE_URL=http://localhost:8000 \
	FRONTEND_URL=http://localhost:3000 \
	E2E_EMAIL=admin@platform.local \
	E2E_PASS=admin123 \
	pytest tests/e2e/ -v --alluredir=allure-results

# ── Production ────────────────────────────────────────────────────────────────
prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-migrate:
	docker compose -f docker-compose.prod.yml exec -w /app -T backend alembic upgrade head
