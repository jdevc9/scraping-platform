import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from sqlalchemy import func, select
from app.api.dependencies import CurrentUser, DbSession
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.models.seller import Seller

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/prices")
async def price_analytics(
    db: DbSession,
    _: CurrentUser,
    product_id: uuid.UUID,
    days: int = Query(30, ge=1, le=365),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id, PriceHistory.scraped_at >= since)
        .order_by(PriceHistory.scraped_at.asc())
    )
    history = result.scalars().all()

    prices = [h.price for h in history]

    return {
        "product_id": product_id,
        "period_days": days,
        "data_points": len(history),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
        "current_price": prices[-1] if prices else None,
        "history": [
            {
                "price": h.price,
                "scraped_at": h.scraped_at.isoformat(),
                "price_changed": h.price_changed,
                "price_diff": h.price_diff,
            }
            for h in history
        ],
    }


@router.get("/sellers")
async def seller_analytics(
    db: DbSession,
    _: CurrentUser,
    marketplace: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    query = select(
        Seller.id,
        Seller.name,
        Seller.marketplace,
        Seller.score,
        Seller.total_products,
        func.count(Product.id).label("tracked_products"),
    ).outerjoin(Product, Product.seller_id == Seller.id)

    if marketplace:
        query = query.where(Seller.marketplace == marketplace)

    query = query.group_by(Seller.id).order_by(Seller.score.desc().nullslast()).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return {
        "sellers": [
            {
                "id": str(r.id),
                "name": r.name,
                "marketplace": r.marketplace,
                "score": r.score,
                "total_products": r.total_products,
                "tracked_products": r.tracked_products,
            }
            for r in rows
        ]
    }
