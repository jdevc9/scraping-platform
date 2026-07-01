# Production Deployment Guide

## Prerequisites

- Ubuntu 24.04 server (2+ vCPUs, 4GB+ RAM recommended)
- Docker 26+ and Docker Compose v2
- A domain or IP for the platform
- GHCR credentials (or any Docker registry)
- Optional: a proxy list (HTTP/SOCKS5) for scraping

---

## 1. Server Setup

```bash
# On the production server
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin curl git

# Add your deploy user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Create app directory
sudo mkdir -p /opt/scraping-platform
sudo chown $USER:$USER /opt/scraping-platform
cd /opt/scraping-platform

# Clone repo (or rsync from CI)
git clone https://github.com/YOUR_ORG/scraping-platform.git .
```

---

## 2. Environment Configuration

```bash
# Copy and fill out production env
cp .env.example .env.production
nano .env.production
```

Critical values to set in `.env.production`:

```bash
# Strong random key — never reuse dev key
SECRET_KEY=$(openssl rand -hex 32)

# Real database credentials
POSTGRES_USER=scraping_prod
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=scraping_platform

DATABASE_URL=postgresql+asyncpg://scraping_prod:<pw>@db:5432/scraping_platform
DATABASE_URL_SYNC=postgresql://scraping_prod:<pw>@db:5432/scraping_platform

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Scraping
PROXY_LIST_URL=http://your-proxy-provider/list.txt   # or leave empty
CAPTCHA_SERVICE_KEY=your-2captcha-key                # or leave empty
ALERT_WEBHOOK_URL=https://hooks.slack.com/...        # optional

# Monitoring
GRAFANA_PASSWORD=<strong-grafana-password>
FLOWER_USER=admin
FLOWER_PASS=<flower-password>

APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

---

## 3. First Deploy

```bash
cd /opt/scraping-platform

# Pull images from registry
export BACKEND_IMAGE=ghcr.io/YOUR_ORG/scraping-platform-backend:latest
export FRONTEND_IMAGE=ghcr.io/YOUR_ORG/scraping-platform-frontend:latest

docker compose -f docker-compose.prod.yml pull

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Run DB migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create initial admin user
docker compose -f docker-compose.prod.yml exec backend python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models.user import User, UserRole
from app.core.security import hash_password
import os

engine = create_engine(os.getenv('DATABASE_URL_SYNC'))
with Session(engine) as s:
    s.add(User(
        email='admin@yourcompany.com',
        hashed_password=hash_password('CHANGE_THIS_PASSWORD'),
        full_name='Platform Admin',
        role=UserRole.admin,
    ))
    s.commit()
    print('Admin user created')
"
```

---

## 4. Health Verification

```bash
# Check all containers are running
docker compose -f docker-compose.prod.yml ps

# Check API health
curl http://localhost:8000/api/v1/health

# Check frontend
curl -I http://localhost:3000

# Tail logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery_worker
```

Expected health response:
```json
{
  "status": "ok",
  "environment": "production",
  "services": {
    "database": "ok",
    "redis": "ok"
  }
}
```

---

## 5. Rolling Updates (CI/CD triggered)

The GitHub Actions deploy pipeline handles this automatically via SSH.
For manual updates:

```bash
cd /opt/scraping-platform

# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Rolling restart (zero-downtime for stateless services)
docker compose -f docker-compose.prod.yml up -d --no-build backend celery_worker celery_beat frontend

# Run any new migrations
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# Verify health
curl -f http://localhost:8000/api/v1/health
```

---

## 6. Nginx Reverse Proxy (optional, recommended)

If you want HTTPS via Let's Encrypt:

```nginx
server {
    listen 443 ssl;
    server_name scraping.yourcompany.com;

    ssl_certificate     /etc/letsencrypt/live/scraping.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/scraping.yourcompany.com/privkey.pem;

    # Dashboard
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }

    # Metrics (restrict access)
    location /grafana/ {
        proxy_pass http://localhost:3001/;
        auth_basic "Monitoring";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

---

## 7. Backup Strategy

```bash
# Database backup (run as cron job)
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip \
  > /backups/scraping_$(date +%Y%m%d_%H%M%S).sql.gz

# Crontab entry (daily at 03:00)
0 3 * * * /opt/scraping-platform/scripts/backup.sh >> /var/log/scraping-backup.log 2>&1
```

---

## 8. Troubleshooting

| Symptom | Check |
|---------|-------|
| Scrapers returning 0 products | Check proxy health: `make proxy-check` |
| CAPTCHA errors in logs | Verify `CAPTCHA_SERVICE_KEY` and 2captcha balance |
| Celery tasks stuck in PENDING | Redis connection: `docker compose exec redis redis-cli ping` |
| High API latency | Check DB slow query log, price_history index health |
| Frontend 502 | Backend container health: `docker compose ps` |
| Alembic migration fails | Check `DATABASE_URL_SYNC` matches running DB |

```bash
# Force re-create a stuck container
docker compose -f docker-compose.prod.yml up -d --force-recreate celery_worker

# Check Celery worker connectivity
docker compose -f docker-compose.prod.yml exec backend \
  celery -A app.tasks.celery_app inspect active

# Purge all queued tasks (emergency)
docker compose -f docker-compose.prod.yml exec backend \
  celery -A app.tasks.celery_app purge -f
```
