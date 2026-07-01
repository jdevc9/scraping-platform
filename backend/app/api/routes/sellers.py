import uuid
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from app.api.dependencies import CurrentUser, DbSession
from app.api.schemas import PaginatedResponse, SellerRead
from app.models.seller import Seller

router = APIRouter(prefix="/sellers", tags=["sellers"])


@router.get("", response_model=PaginatedResponse[SellerRead])
async def list_sellers(
    db: DbSession,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    marketplace: str | None = Query(None),
):
    query = select(Seller)
    if marketplace:
        query = query.where(Seller.marketplace == marketplace)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Seller.score.desc().nullslast())
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{seller_id}", response_model=SellerRead)
async def get_seller(seller_id: uuid.UUID, db: DbSession, _: CurrentUser):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    return seller
