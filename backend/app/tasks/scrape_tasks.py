"""
Celery scrape tasks — Phase 2 real implementation.

Architecture:
  trigger_marketplace_scrape(marketplace)
      └── fan-out → scrape_product(product_id, marketplace) × N
                        └── scraper.scrape_product()
                            └── PersistenceService.save_scraped_product()
                                └── ChangeDetector.analyse()
                                    └── dispatch alert tasks if events found

All tasks are synchronous (Celery workers are sync).
Async scrapers are run via asyncio.run() inside the task.
"""
from __future__ import annotations

import asyncio
from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.scrapers.factory import get_scraper
from app.services.change_detector import AlertType, ChangeDetector
from app.services.persistence import PersistenceService

logger = get_logger(__name__)
settings = get_settings()


def _sync_engine():
    """Create a sync engine for Celery task use."""
    return create_engine(
        settings.database_url_sync,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# ── Individual product scrape ─────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="app.tasks.scrape_tasks.scrape_product",
    max_retries=3,
    default_retry_delay=90,
    acks_late=True,
    reject_on_worker_lost=True,
    queue="scraping",
)
def scrape_product(self, product_id: str, marketplace: str) -> dict:
    """
    Scrape one product, persist result, detect changes, fire alerts.
    product_id is the internal DB UUID.
    """
    logger.info("scrape_product_started", product_id=product_id, marketplace=marketplace)

    engine = _sync_engine()
    with Session(engine) as session:
        from app.models.product import Product
        product_row = session.execute(
            select(Product).where(Product.id == product_id)
        ).scalar_one_or_none()

        if not product_row:
            logger.error("scrape_product_not_found", product_id=product_id)
            return {"status": "error", "reason": "product_not_found"}

        external_id = product_row.external_id
        url = product_row.url

    # Run async scraper in sync context
    try:
        scraped = asyncio.run(_async_scrape(marketplace, external_id, url))
    except Exception as exc:
        logger.error(
            "scrape_failed",
            product_id=product_id,
            marketplace=marketplace,
            error=str(exc),
        )
        # Increment error counter
        with Session(engine) as session:
            from app.models.product import Product
            row = session.get(Product, product_id)
            if row:
                row.scrape_errors = (row.scrape_errors or 0) + 1
                session.commit()
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    # Persist + detect changes
    with Session(engine) as session:
        svc = PersistenceService(session)
        detector = ChangeDetector()

        try:
            product_model, history = svc.save_scraped_product(scraped)
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("persist_failed", product_id=product_id, error=str(exc))
            raise self.retry(exc=exc)

        # Fire alerts if we got a history record with changes
        if history:
            events = detector.analyse(product_model, history)
            _dispatch_alerts(events)

    logger.info(
        "scrape_product_done",
        product_id=product_id,
        price=scraped.price,
        available=scraped.is_available,
    )
    return {
        "status": "ok",
        "product_id": product_id,
        "price": scraped.price,
        "available": scraped.is_available,
        "marketplace": marketplace,
    }


async def _async_scrape(marketplace: str, external_id: str, url: str | None):
    """Thin async wrapper — keeps asyncio.run() call isolated."""
    async with get_scraper(marketplace) as scraper:
        return await scraper.scrape_product(external_id, url)


# ── Search task (discover new products) ──────────────────────────────────────

@shared_task(
    bind=True,
    name="app.tasks.scrape_tasks.search_and_track",
    max_retries=2,
    default_retry_delay=120,
    queue="scraping",
)
def search_and_track(self, marketplace: str, keyword: str, max_results: int = 20) -> dict:
    """
    Search a marketplace for a keyword, upsert all found products into the DB,
    then queue individual scrape_product tasks for deep data.
    """
    logger.info("search_and_track_started", marketplace=marketplace, keyword=keyword)

    try:
        products = asyncio.run(_async_search(marketplace, keyword, max_results))
    except Exception as exc:
        logger.error("search_failed", marketplace=marketplace, keyword=keyword, error=str(exc))
        raise self.retry(exc=exc)

    engine = _sync_engine()
    queued = 0

    with Session(engine) as session:
        svc = PersistenceService(session)
        for scraped in products:
            try:
                product_model, _ = svc.save_scraped_product(scraped)
                session.flush()
                # Queue deep scrape for each discovered product
                scrape_product.apply_async(
                    args=[str(product_model.id), marketplace],
                    queue="scraping",
                    countdown=queued * 2,  # stagger by 2s each
                )
                queued += 1
            except Exception as e:
                logger.warning("search_item_persist_failed", error=str(e))
                continue
        session.commit()

    logger.info("search_and_track_done", marketplace=marketplace, keyword=keyword, queued=queued)
    return {"status": "ok", "marketplace": marketplace, "keyword": keyword, "queued": queued}


async def _async_search(marketplace: str, keyword: str, max_results: int):
    async with get_scraper(marketplace) as scraper:
        return await scraper.search_products(keyword, max_results)


# ── Marketplace fan-out ───────────────────────────────────────────────────────

@shared_task(
    name="app.tasks.scrape_tasks.trigger_marketplace_scrape",
    queue="default",
)
def trigger_marketplace_scrape(marketplace: str) -> dict:
    """
    Fan-out: queue scrape_product for every tracked product in the marketplace.
    Called by Celery Beat on a schedule.
    """
    from app.models.product import Product

    engine = _sync_engine()
    with Session(engine) as session:
        rows = session.execute(
            select(Product.id, Product.marketplace).where(
                Product.marketplace == marketplace,
                Product.is_available.is_(True),
            )
        ).all()

    task_ids = []
    for i, row in enumerate(rows):
        task = scrape_product.apply_async(
            args=[str(row.id), marketplace],
            queue="scraping",
            countdown=i * 3,  # stagger 3s apart to avoid bursts
        )
        task_ids.append(task.id)

    logger.info(
        "marketplace_fan_out",
        marketplace=marketplace,
        total=len(rows),
        queued=len(task_ids),
    )
    return {"marketplace": marketplace, "queued": len(task_ids)}


# ── Alert dispatch helper ─────────────────────────────────────────────────────

def _dispatch_alerts(events) -> None:
    from app.tasks.alert_tasks import send_price_alert, send_stock_alert

    for event in events:
        try:
            if event.alert_type in (AlertType.price_drop, AlertType.price_spike):
                send_price_alert.apply_async(
                    kwargs={
                        "product_id": event.product_id,
                        "alert_type": event.alert_type,
                        "payload": event.payload,
                    },
                    queue="alerts",
                )
            elif event.alert_type in (AlertType.out_of_stock, AlertType.back_in_stock):
                send_stock_alert.apply_async(
                    kwargs={
                        "product_id": event.product_id,
                        "alert_type": event.alert_type,
                        "payload": event.payload,
                    },
                    queue="alerts",
                )
        except Exception as e:
            logger.error("alert_dispatch_failed", event=str(event), error=str(e))
