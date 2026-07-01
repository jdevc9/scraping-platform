#!/bin/bash
set -e

cd /app

echo "[entrypoint] Waiting for PostgreSQL..."
until python -c "
import os, sys
try:
    import psycopg2
    psycopg2.connect(os.environ.get('DATABASE_URL_SYNC',''))
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; do
    sleep 2
done
echo "[entrypoint] PostgreSQL ready."

# Só roda migrate se o alembic.ini existir
if [ -f "/app/alembic.ini" ]; then
    echo "[entrypoint] Running migrations..."
    cd /app && alembic upgrade head
    echo "[entrypoint] Migrations done."
else
    echo "[entrypoint] WARNING: alembic.ini not found, skipping migrations."
    echo "[entrypoint] Run manually: docker compose exec backend alembic upgrade head"
fi

exec "$@"
