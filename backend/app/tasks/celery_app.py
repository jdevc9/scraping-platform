from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "scraping_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scrape_tasks",
        "app.tasks.alert_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.scrape_tasks.*": {"queue": "scraping"},
        "app.tasks.alert_tasks.*": {"queue": "alerts"},
    },
    task_default_queue="default",
    beat_schedule={
        "scrape-shopee-every-hour": {
            "task": "app.tasks.scrape_tasks.trigger_marketplace_scrape",
            "schedule": 3600.0,
            "args": ["shopee"],
            "options": {"queue": "scraping"},
        },
        "scrape-jdcom-every-hour": {
            "task": "app.tasks.scrape_tasks.trigger_marketplace_scrape",
            "schedule": 3600.0,
            "args": ["jdcom"],
            "options": {"queue": "scraping"},
        },
    },
)
