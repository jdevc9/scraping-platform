import uuid
from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.seller import Marketplace


class Product(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "products"

    # Identity
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace", create_constraint=False),
        nullable=False,
        index=True,
    )
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Pricing
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    promotions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Ratings
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Stock
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Tracking
    last_scraped_at: Mapped[str | None] = mapped_column(nullable=True)
    scrape_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # FK
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    seller: Mapped["Seller | None"] = relationship("Seller", back_populates="products")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product {self.title[:40]}... [{self.marketplace}]>"
