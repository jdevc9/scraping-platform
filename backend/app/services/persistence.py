"""
ScrapingPersistenceService
--------------------------
Single responsibility: take a ScrapedProduct snapshot and persist it to the
database using the correct upsert / diff logic.

Calling code (Celery tasks) must pass a sync SQLAlchemy Session because Celery
workers are synchronous. Async sessions are only used in FastAPI request handlers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.models.seller import Marketplace, Seller
from app.scrapers.schemas import ScrapedProduct

logger = get_logger(__name__)


class PersistenceService:
    def __init__(self, session: Session):
        self.db = session

    # ── Public entry point ────────────────────────────────────────────────────

    def save_scraped_product(self, scraped: ScrapedProduct) -> tuple[Product, PriceHistory | None]:
        """
        Upsert product + seller, detect changes, write price history if anything changed.
        Returns (product, price_history_record | None).
        """
        if not scraped.is_valid():
            raise ValueError(f"Invalid scraped product: {scraped!r}")

        seller = self._upsert_seller(scraped) if scraped.seller else None
        product, created = self._upsert_product(scraped, seller)
        history = self._record_price_history(product, scraped, created)
        self._update_scrape_metadata(product, scraped)

        self.db.flush()

        logger.info(
            "product_persisted",
            product_id=str(product.id),
            marketplace=scraped.marketplace,
            created=created,
            price_changed=history.price_changed if history else False,
            stock_changed=history.stock_changed if history else False,
        )
        return product, history

    # ── Seller ────────────────────────────────────────────────────────────────

    def _upsert_seller(self, scraped: ScrapedProduct) -> Seller:
        s = scraped.seller
        marketplace = Marketplace(scraped.marketplace)

        result = self.db.execute(
            select(Seller).where(
                Seller.external_id == s.external_id,
                Seller.marketplace == marketplace,
            )
        ).scalar_one_or_none()

        if result is None:
            result = Seller(
                external_id=s.external_id,
                marketplace=marketplace,
                name=s.name,
                profile_url=s.profile_url,
                score=s.score,
                reputation=s.reputation,
                total_products=s.total_products,
            )
            self.db.add(result)
            logger.info("seller_created", external_id=s.external_id, name=s.name)
        else:
            # Update mutable fields
            result.name = s.name or result.name
            if s.score is not None:
                result.score = s.score
            if s.reputation is not None:
                result.reputation = s.reputation
            if s.total_products:
                result.total_products = s.total_products
            if s.profile_url:
                result.profile_url = s.profile_url

        return result

    # ── Product ───────────────────────────────────────────────────────────────

    def _upsert_product(
        self, scraped: ScrapedProduct, seller: Seller | None
    ) -> tuple[Product, bool]:
        marketplace = Marketplace(scraped.marketplace)

        existing = self.db.execute(
            select(Product).where(
                Product.external_id == scraped.external_id,
                Product.marketplace == marketplace,
            )
        ).scalar_one_or_none()

        if existing is None:
            product = Product(
                external_id=scraped.external_id,
                marketplace=marketplace,
                title=scraped.title,
                description=scraped.description,
                sku=scraped.sku,
                url=scraped.url,
                price=scraped.price,
                original_price=scraped.original_price,
                currency=scraped.currency,
                promotions=scraped.promotions,
                rating=scraped.rating,
                reviews_count=scraped.reviews_count,
                stock_quantity=scraped.stock_quantity,
                is_available=scraped.is_available,
                images=scraped.images,
                seller=seller,
            )
            self.db.add(product)
            return product, True

        # Selective updates — don't overwrite with None
        if scraped.title:
            existing.title = scraped.title
        if scraped.description is not None:
            existing.description = scraped.description
        if scraped.images:
            existing.images = scraped.images
        if scraped.rating is not None:
            existing.rating = scraped.rating
        if scraped.reviews_count:
            existing.reviews_count = scraped.reviews_count
        if scraped.promotions:
            existing.promotions = scraped.promotions
        if seller:
            existing.seller = seller

        # Price + stock are always updated (we want the latest)
        existing.price = scraped.price
        existing.original_price = scraped.original_price
        existing.stock_quantity = scraped.stock_quantity
        existing.is_available = scraped.is_available

        return existing, False

    # ── Price history ─────────────────────────────────────────────────────────

    def _record_price_history(
        self,
        product: Product,
        scraped: ScrapedProduct,
        created: bool,
    ) -> PriceHistory | None:
        """
        Always write a history record on creation.
        On subsequent scrapes, write only if price OR stock changed.
        """
        if scraped.price is None:
            return None

        price_changed = False
        stock_changed = False
        price_diff: float | None = None

        if not created:
            last = self._get_last_history(product)
            if last:
                price_changed = last.price != scraped.price
                stock_changed = last.stock_quantity != scraped.stock_quantity
                if price_changed and last.price:
                    price_diff = round(scraped.price - last.price, 4)

                # Nothing changed — skip the write (keeps table lean)
                if not price_changed and not stock_changed:
                    return None

        record = PriceHistory(
            product=product,
            price=scraped.price,
            original_price=scraped.original_price,
            currency=scraped.currency,
            stock_quantity=scraped.stock_quantity,
            is_available=scraped.is_available,
            scraped_at=scraped.scraped_at or datetime.now(timezone.utc),
            price_changed=price_changed,
            stock_changed=stock_changed,
            price_diff=price_diff,
        )
        self.db.add(record)
        return record

    def _get_last_history(self, product: Product) -> PriceHistory | None:
        return self.db.execute(
            select(PriceHistory)
            .where(PriceHistory.product == product)
            .order_by(PriceHistory.scraped_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    # ── Metadata ──────────────────────────────────────────────────────────────

    def _update_scrape_metadata(self, product: Product, scraped: ScrapedProduct) -> None:
        product.last_scraped_at = scraped.scraped_at.isoformat() if scraped.scraped_at else None
