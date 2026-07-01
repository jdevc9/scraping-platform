from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    project_name: str = "Senior Automation Platform"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://scraping:scraping_pass@db:5432/scraping_platform"
    database_url_sync: str = "postgresql://scraping:scraping_pass@db:5432/scraping_platform"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Scraping
    max_concurrent_scrapers: int = 5
    scrape_timeout_seconds: int = 30
    max_retries: int = 3
    proxy_list_url: str = ""
    captcha_service_key: str = ""
    alert_webhook_url: str = ""
    price_drop_threshold_pct: float = 5.0
    price_spike_threshold_pct: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
