"""
Alert tasks — dispatched by scrape_tasks after ChangeDetector fires events.

Notification channels (Phase 2: webhook + log):
  - Webhook POST (configurable URL per alert type)
  - Structured log (always — queryable via Grafana/Loki)
  - Email stub (Phase 3)
  - Slack stub (Phase 3)
"""
from __future__ import annotations

import json
import httpx
from celery import shared_task
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@shared_task(
    name="app.tasks.alert_tasks.send_price_alert",
    max_retries=3,
    default_retry_delay=30,
    queue="alerts",
)
def send_price_alert(product_id: str, alert_type: str, payload: dict) -> dict:
    """
    Dispatch a price-change alert.
    alert_type: "price_drop" | "price_spike"
    """
    logger.info(
        "price_alert_fired",
        product_id=product_id,
        alert_type=alert_type,
        old_price=payload.get("old_price"),
        new_price=payload.get("new_price"),
        pct=payload.get("pct"),
        title=payload.get("title", "")[:60],
    )

    result = {"product_id": product_id, "alert_type": alert_type, "channels": []}

    # Webhook dispatch (if configured)
    webhook_url = getattr(settings, "alert_webhook_url", None)
    if webhook_url:
        try:
            resp = httpx.post(
                webhook_url,
                json={
                    "event": alert_type,
                    "product_id": product_id,
                    "data": payload,
                },
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result["channels"].append("webhook")
            logger.info("webhook_alert_sent", status=resp.status_code)
        except httpx.HTTPError as e:
            logger.warning("webhook_alert_failed", error=str(e))

    result["channels"].append("log")
    return result


@shared_task(
    name="app.tasks.alert_tasks.send_stock_alert",
    max_retries=3,
    default_retry_delay=30,
    queue="alerts",
)
def send_stock_alert(product_id: str, alert_type: str, payload: dict) -> dict:
    """
    Dispatch a stock-change alert.
    alert_type: "out_of_stock" | "back_in_stock"
    """
    logger.info(
        "stock_alert_fired",
        product_id=product_id,
        alert_type=alert_type,
        stock_quantity=payload.get("stock_quantity"),
        title=payload.get("title", "")[:60],
    )

    result = {"product_id": product_id, "alert_type": alert_type, "channels": ["log"]}

    webhook_url = getattr(settings, "alert_webhook_url", None)
    if webhook_url:
        try:
            resp = httpx.post(
                webhook_url,
                json={"event": alert_type, "product_id": product_id, "data": payload},
                timeout=10,
            )
            resp.raise_for_status()
            result["channels"].append("webhook")
        except httpx.HTTPError as e:
            logger.warning("webhook_stock_alert_failed", error=str(e))

    return result
