# Senior Automation & Scraping Platform

<img width="2752" height="1536" alt="Shopee_Scraper_PostgreSQL_API_Da…_202607011945" src="https://github.com/user-attachments/assets/d5ee72c7-3080-4b45-a1fd-6504d68cbb11" />


Plataforma enterprise de scraping e monitoramento de preços para Shopee e JD.com.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![React](https://img.shields.io/badge/React-18-blue)
![Tests](https://img.shields.io/badge/Tests-14%20passing-brightgreen)

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery
- **Frontend:** React, TypeScript, Tailwind CSS, Recharts
- **Scraping:** Playwright, Selenium, BeautifulSoup, proxy rotation
- **DevOps:** Docker, Docker Compose, GitHub Actions, Jenkins
- **Testes:** Pytest, Playwright E2E, Locust load tests, Allure reports

## Funcionalidades

- Monitoramento de preços em tempo real (Shopee e JD.com)
- Detecção automática de mudanças de preço e estoque
- Dashboard com gráficos de tendência de preços
- Sistema de alertas via webhook
- API REST completa com autenticação JWT e RBAC
- Pipeline CI/CD com testes automatizados

## Como rodar

### Pré-requisitos
- Docker e Docker Compose instalados

### Subir o projeto

```bash
git clone https://github.com/jdevc9/scraping-platform.git
cd scraping-platform
cp .env.example .env
docker compose up -d db redis backend
docker compose exec -w /app backend alembic upgrade head
docker compose exec -w /app backend python -c "
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password
async def seed():
    async with AsyncSessionLocal() as db:
        db.add(User(email='admin@platform.local', hashed_password=hash_password('admin123'), full_name='Admin', role=UserRole.admin))
        await db.commit()
        print('Admin criado: admin@platform.local / admin123')
asyncio.run(seed())
"
```

### Acessar

| Serviço | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Flower | http://localhost:5555 |
| Grafana | http://localhost:3001 |

**Login:** admin@platform.local / admin123

## Testes automatizados

```bash
cd meus_testes
pip install pytest requests pytest-playwright
playwright install chromium
python -m pytest tests/ -v --html=relatorio.html
```

## Arquitetura

```
┌─────────────────────────────────────┐
│  React Dashboard (TypeScript)        │
├─────────────────────────────────────┤
│  FastAPI REST API (Python 3.12)      │
├─────────────────────────────────────┤
│  Celery Workers + Redis              │
├─────────────────────────────────────┤
│  Playwright + Selenium Scrapers      │
├─────────────────────────────────────┤
│  PostgreSQL (dados + histórico)      │
└─────────────────────────────────────┘
```
