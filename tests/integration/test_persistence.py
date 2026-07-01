"""
Integration tests for PersistenceService.
Runs against a real SQLite in-memory DB (via conftest fixtures).
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.scrapers.schemas import ScrapedProduct, ScrapedSeller
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.seller import Seller


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_scraped(
    external_id: str = "shop1.item1",
    marketplace: str = "shopee",
    title: str = "Test Product",
    price: float = 99.90,
    stock: int = 10,
    available: bool = True,
    with_seller: bool = True,
) -> ScrapedProduct:
    seller = ScrapedSeller(
        external_id="seller-001",
        name="Test Seller",
        marketplace=marketplace,
        score=4.8,
        total_products=120,
    ) if with_seller else None

    return ScrapedProduct(
        external_id=external_id,
        marketplace=marketplace,
        title=title,
        price=price,
        original_price=120.00,
        currency="BRL",
        description="A test product",
        images=["https://img.test/1.jpg"],
        sku="SKU-001",
        url=f"https://shopee.com.br/product-i.{external_id}",
        rating=4.5,
        reviews_count=200,
        stock_quantity=stock,
        is_available=available,
        seller=seller,
        scraped_at=datetime.now(timezone.utc),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_new_product_creates_record(db_session: AsyncSession):
    """First save of a product creates product row and initial price history."""
    from sqlalchemy.orm import Session
    from app.services.persistence import PersistenceService

    # Use sync session (PersistenceService is sync)
    from sqlalchemy import create_engine
    sync_engine = create_engine("sqlite:///:memory:")
    from app.core.database import Base
    Base.metadata.create_all(sync_engine)

    from sqlalchemy.orm import Session as SyncSession
    with SyncSession(sync_engine) as session:
        svc = PersistenceService(session)
        scraped = _make_scraped()
        product, history = svc.save_scraped_product(scraped)
        session.commit()

        assert product.id is not None
        assert product.title == "Test Product"
        assert product.price == 99.90
        assert product.marketplace.value == "shopee"

        # First save always creates a history record
        assert history is not None
        assert history.price == 99.90
        assert history.price_changed is False  # first record, no change


@pytest.mark.asyncio
async def test_save_creates_seller(db_session: AsyncSession):
    """Seller is created and linked to product on first save."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import Base
    from app.services.persistence import PersistenceService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        svc = PersistenceService(session)
        scraped = _make_scraped(with_seller=True)
        product, _ = svc.save_scraped_product(scraped)
        session.commit()

        seller = session.execute(
            select(Seller).where(Seller.external_id == "seller-001")
        ).scalar_one_or_none()

        assert seller is not None
        assert seller.name == "Test Seller"
        assert seller.score == 4.8
        assert product.seller_id == seller.id


@pytest.mark.asyncio
async def test_upsert_updates_existing_product(db_session: AsyncSession):
    """Scraping the same product twice updates the existing row."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import Base
    from app.services.persistence import PersistenceService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        svc = PersistenceService(session)

        # First scrape
        scraped1 = _make_scraped(price=100.0)
        p1, h1 = svc.save_scraped_product(scraped1)
        session.commit()
        product_id = p1.id

        # Second scrape — same external_id, different price
        scraped2 = _make_scraped(price=85.0, title="Updated Title")
        p2, h2 = svc.save_scraped_product(scraped2)
        session.commit()

        # Should be same product row
        assert p2.id == product_id
        assert p2.title == "Updated Title"
        assert p2.price == 85.0

        # New history record created because price changed
        assert h2 is not None
        assert h2.price_changed is True
        assert h2.price_diff == pytest.approx(-15.0)


@pytest.mark.asyncio
async def test_no_history_record_when_nothing_changed(db_session: AsyncSession):
    """Second scrape with identical price/stock writes no history row."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import Base
    from app.services.persistence import PersistenceService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        svc = PersistenceService(session)

        scraped = _make_scraped(price=100.0, stock=10)
        p1, h1 = svc.save_scraped_product(scraped)
        session.commit()

        # Second scrape — identical data
        scraped2 = _make_scraped(price=100.0, stock=10)
        p2, h2 = svc.save_scraped_product(scraped2)
        session.commit()

        # h2 should be None — no changes detected
        assert h2 is None


@pytest.mark.asyncio
async def test_stock_change_triggers_history_record(db_session: AsyncSession):
    """Stock change (even without price change) writes a history record."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import Base
    from app.services.persistence import PersistenceService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        svc = PersistenceService(session)

        scraped1 = _make_scraped(price=100.0, stock=10, available=True)
        svc.save_scraped_product(scraped1)
        session.commit()

        # Stock goes to 0 — out of stock
        scraped2 = _make_scraped(price=100.0, stock=0, available=False)
        _, h2 = svc.save_scraped_product(scraped2)
        session.commit()

        assert h2 is not None
        assert h2.stock_changed is True
        assert not h2.is_available
        assert h2.price_changed is False  # price didn't change


@pytest.mark.asyncio
async def test_product_without_seller(db_session: AsyncSession):
    """Products without seller data should persist cleanly."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import Base
    from app.services.persistence import PersistenceService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        svc = PersistenceService(session)
        scraped = _make_scraped(with_seller=False)
        product, _ = svc.save_scraped_product(scraped)
        session.commit()

        assert product.seller_id is None
        assert product.id is not None


@pytest.mark.asyncio
async def test_invalid_scraped_raises(db_session: AsyncSession):
    """Saving an invalid ScrapedProduct raises ValueError."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import Base
    from app.services.persistence import PersistenceService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        svc = PersistenceService(session)
        invalid = ScrapedProduct(external_id="", marketplace="shopee", title="")
        with pytest.raises(ValueError, match="Invalid scraped product"):
            svc.save_scraped_product(invalid)
