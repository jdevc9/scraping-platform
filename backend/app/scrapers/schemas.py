from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ScrapedSeller:
    external_id: str
    name: str
    marketplace: str
    profile_url: str | None = None
    score: float | None = None
    reputation: float | None = None
    total_products: int = 0


@dataclass
class ScrapedProduct:
    """
    Pure data object returned by every scraper.
    No SQLAlchemy, no I/O — just a validated snapshot.
    """

    external_id: str
    marketplace: str
    title: str

    # Pricing
    price: float | None = None
    original_price: float | None = None
    currency: str = "BRL"
    promotions: dict = field(default_factory=dict)

    # Content
    description: str | None = None
    images: list[str] = field(default_factory=list)
    sku: str | None = None
    url: str | None = None

    # Ratings
    rating: float | None = None
    reviews_count: int = 0

    # Stock
    stock_quantity: int | None = None
    is_available: bool = True

    # Seller
    seller: ScrapedSeller | None = None

    # Meta
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: dict = field(default_factory=dict)  # original payload for debugging

    def is_valid(self) -> bool:
        """Minimum viability check before persisting."""
        return bool(self.external_id and self.title and self.marketplace)
