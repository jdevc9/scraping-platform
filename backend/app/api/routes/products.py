import uuid
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from app.api.dependencies import CurrentUser, DbSession
from app.api.schemas import PaginatedResponse, ProductCreate, ProductRead
from app.models.product import Product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductRead])
async def list_products(
    db: DbSession,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    marketplace: str | None = Query(None),
    is_available: bool | None = Query(None),
    search: str | None = Query(None),
):
    query = select(Product)

    if marketplace:
        query = query.where(Product.marketplace == marketplace)
    if is_available is not None:
        query = query.where(Product.is_available == is_available)
    if search:
        query = query.where(Product.title.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Product.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: uuid.UUID, db: DbSession, _: CurrentUser):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, db: DbSession, _: CurrentUser):
    existing = await db.execute(
        select(Product).where(
            Product.external_id == payload.external_id,
            Product.marketplace == payload.marketplace,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Product already tracked")

    product = Product(**payload.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product
