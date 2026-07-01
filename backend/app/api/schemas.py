from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole
from app.models.seller import Marketplace


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None
    role: UserRole = UserRole.viewer


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


# ── Seller ────────────────────────────────────────────────────────────────────

class SellerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    marketplace: Marketplace
    name: str
    profile_url: str | None
    score: float | None
    reputation: float | None
    total_products: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Product ───────────────────────────────────────────────────────────────────

class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    marketplace: Marketplace
    sku: str | None
    url: str | None
    title: str
    price: float | None
    original_price: float | None
    currency: str
    rating: float | None
    reviews_count: int
    stock_quantity: int | None
    is_available: bool
    seller_id: uuid.UUID | None
    last_scraped_at: str | None
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    external_id: str
    marketplace: Marketplace
    title: str
    url: str | None = None
    sku: str | None = None


# ── Price History ─────────────────────────────────────────────────────────────

class PriceHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    price: float
    original_price: float | None
    currency: str
    stock_quantity: int | None
    is_available: bool
    price_changed: bool
    stock_changed: bool
    price_diff: float | None
    scraped_at: datetime


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "1.0.0"
    services: dict[str, str]
