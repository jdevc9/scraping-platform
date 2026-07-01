"""
/scraping/* routes — operational control of the scraping layer.
Admin and Analyst roles only.
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies import AnalystOrAdmin, DbSession
from app.models.product import Product
from app.scrapers.factory import list_marketplaces

router = APIRouter(prefix="/scraping", tags=["scraping"])


# ── Request / Response schemas ────────────────────────────────────────────────

class ScrapeProductRequest(BaseModel):
    product_id: uuid.UUID


class SearchRequest(BaseModel):
    marketplace: str
    keyword: str
    max_results: int = 20


class TriggerResponse(BaseModel):
    task_id: str
    status: str
    detail: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/trigger/product", response_model=TriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_single_product(
    body: ScrapeProductRequest,
    db: DbSession,
    _: AnalystOrAdmin,
):
    """Queue an immediate scrape for a single tracked product."""
    result = await db.execute(select(Product).where(Product.id == body.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    from app.tasks.scrape_tasks import scrape_product
    task = scrape_product.apply_async(
        args=[str(product.id), str(product.marketplace)],
        queue="scraping",
    )

    return TriggerResponse(
        task_id=task.id,
        status="queued",
        detail=f"Scrape queued for product {body.product_id}",
    )


@router.post("/trigger/marketplace", response_model=TriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_marketplace(
    marketplace: str = Query(..., description="shopee | jdcom"),
    _: AnalystOrAdmin = None,
):
    """Fan-out scrape for all tracked products in a marketplace."""
    supported = list_marketplaces()
    if marketplace not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown marketplace '{marketplace}'. Supported: {supported}",
        )

    from app.tasks.scrape_tasks import trigger_marketplace_scrape
    task = trigger_marketplace_scrape.apply_async(args=[marketplace], queue="default")

    return TriggerResponse(
        task_id=task.id,
        status="queued",
        detail=f"Marketplace fan-out queued for '{marketplace}'",
    )


@router.post("/search", response_model=TriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def search_and_track(body: SearchRequest, _: AnalystOrAdmin):
    """
    Search a marketplace by keyword, discover products, add them to tracking,
    and queue deep scrapes for each.
    """
    supported = list_marketplaces()
    if body.marketplace not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown marketplace. Supported: {supported}",
        )

    from app.tasks.scrape_tasks import search_and_track as search_task
    task = search_task.apply_async(
        args=[body.marketplace, body.keyword, body.max_results],
        queue="scraping",
    )

    return TriggerResponse(
        task_id=task.id,
        status="queued",
        detail=f"Search '{body.keyword}' on {body.marketplace} queued ({body.max_results} max)",
    )


@router.get("/task/{task_id}")
async def get_task_status(task_id: str, _: AnalystOrAdmin):
    """Poll Celery task result by ID."""
    from celery.result import AsyncResult
    from app.tasks.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback if result.failed() else None,
    }


@router.get("/marketplaces")
async def list_supported_marketplaces(_: AnalystOrAdmin):
    """List all registered marketplace scrapers."""
    return {"marketplaces": list_marketplaces()}
