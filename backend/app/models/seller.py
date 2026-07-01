import enum
from sqlalchemy import Float, Integer, String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Marketplace(str, enum.Enum):
    shopee = "shopee"
    jdcom = "jdcom"


class Seller(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sellers"

    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reputation: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_products: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    products: Mapped[list["Product"]] = relationship("Product", back_populates="seller")

    def __repr__(self) -> str:
        return f"<Seller {self.name} [{self.marketplace}]>"
