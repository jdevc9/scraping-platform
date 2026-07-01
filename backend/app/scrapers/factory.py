"""
ScraperFactory
--------------
Returns the correct scraper instance for a given marketplace string.
Centralises import and instantiation so tasks never import scrapers directly.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.scrapers.base import BaseScraper

logger = get_logger(__name__)

_REGISTRY: dict[str, type[BaseScraper]] = {}


def register(marketplace: str):
    """Decorator that registers a scraper class under a marketplace key."""
    def _inner(cls: type[BaseScraper]) -> type[BaseScraper]:
        _REGISTRY[marketplace] = cls
        logger.info("scraper_registered", marketplace=marketplace, cls=cls.__name__)
        return cls
    return _inner


def get_scraper(marketplace: str, **kwargs) -> BaseScraper:
    """
    Instantiate and return a scraper for the given marketplace.

    Usage:
        async with get_scraper("shopee") as scraper:
            product = await scraper.scrape_product(external_id, url)
    """
    # Lazy import — registers scrapers on first use (avoids circular imports)
    _ensure_registered()

    cls = _REGISTRY.get(marketplace.lower())
    if cls is None:
        supported = list(_REGISTRY.keys())
        raise ValueError(f"No scraper registered for '{marketplace}'. Supported: {supported}")

    return cls(**kwargs)


def _ensure_registered() -> None:
    if _REGISTRY:
        return
    # Import here to trigger @register decorators
    from app.scrapers import shopee, jdcom  # noqa: F401


def list_marketplaces() -> list[str]:
    _ensure_registered()
    return list(_REGISTRY.keys())
