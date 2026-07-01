from fastapi import APIRouter
from sqlalchemy import text
import redis.asyncio as aioredis
from app.api.dependencies import DbSession
from app.api.schemas import HealthResponse
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(tags=["monitoring"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: DbSession):
    services = {}

    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        services["database"] = "ok"
    except Exception as e:
        logger.error("db_health_failed", error=str(e))
        services["database"] = "error"

    # Check Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        services["redis"] = "ok"
    except Exception as e:
        logger.error("redis_health_failed", error=str(e))
        services["redis"] = "error"

    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        environment=settings.app_env,
        services=services,
    )


@router.get("/jobs")
async def list_jobs():
    """Returns active, reserved and scheduled Celery tasks via Redis inspection."""
    try:
        from celery.app.control import Control
        from app.tasks.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}

        return {
            "active": active,
            "reserved": reserved,
            "scheduled": scheduled,
        }
    except Exception as e:
        logger.warning("jobs_inspect_failed", error=str(e))
        return {"active": {}, "reserved": {}, "scheduled": {}, "error": str(e)}
