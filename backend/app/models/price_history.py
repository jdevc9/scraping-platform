import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin


class PriceHistory(Base, UUIDMixin):
    """
    Append-only table. Never update rows — only insert.
    Index on (product_id, scraped_at) is the hot path for all analytics queries.
    """

    __tablename__ = "price_history"

    __table_args__ = (
        Index("ix_price_history_product_time", "product_id", "scraped_at"),
        Index("ix_price_history_scraped_at", "scraped_at"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    price: Mapped[float] = mapped_column(Float, nullable=False)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="BRL", nullable=False)
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Diff tracking
    price_changed: Mapped[bool] = mapped_column(default=False, nullable=False)
    stock_changed: Mapped[bool] = mapped_column(default=False, nullable=False)
    price_diff: Mapped[float | None] = mapped_column(Float, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory product={self.product_id} price={self.price} at={self.scraped_at}>"
