"""
ChangeDetectorService
---------------------
Analyses a persisted PriceHistory record and decides whether to fire an alert.

Rules (all configurable):
  - Price drop ≥ DROP_THRESHOLD_PCT  → fire price alert
  - Price increase ≥ SPIKE_THRESHOLD_PCT → fire spike alert (optional)
  - Stock goes to 0 (out of stock)   → fire stock alert
  - Stock comes back from 0 (in stock) → fire restock alert
  - Seller score drops > 0.5 pts     → fire seller alert

This service is a pure decision engine — it doesn't talk to Celery directly,
it returns a list of AlertEvent objects. Callers decide whether to enqueue them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.core.logging import get_logger
from app.models.price_history import PriceHistory
from app.models.product import Product

logger = get_logger(__name__)


class AlertType(str, Enum):
    price_drop = "price_drop"
    price_spike = "price_spike"
    out_of_stock = "out_of_stock"
    back_in_stock = "back_in_stock"
    seller_score_drop = "seller_score_drop"


@dataclass
class AlertEvent:
    alert_type: AlertType
    product_id: str
    marketplace: str
    payload: dict = field(default_factory=dict)


class ChangeDetector:
    DROP_THRESHOLD_PCT: float = 5.0    # fire if price drops ≥ 5%
    SPIKE_THRESHOLD_PCT: float = 20.0  # fire if price spikes ≥ 20%
    SELLER_SCORE_DROP: float = 0.5     # fire if seller score drops by ≥ 0.5 pts

    def __init__(
        self,
        drop_threshold: float = DROP_THRESHOLD_PCT,
        spike_threshold: float = SPIKE_THRESHOLD_PCT,
    ):
        self.drop_threshold = drop_threshold
        self.spike_threshold = spike_threshold

    def analyse(self, product: Product, history: PriceHistory) -> list[AlertEvent]:
        """
        Given a freshly-persisted history record, return any triggered alerts.
        Called synchronously after persistence — no I/O inside.
        """
        events: list[AlertEvent] = []

        if history.price_changed and history.price_diff is not None:
            events.extend(self._check_price(product, history))

        if history.stock_changed:
            events.extend(self._check_stock(product, history))

        if events:
            logger.info(
                "change_events_detected",
                product_id=str(product.id),
                count=len(events),
                types=[e.alert_type for e in events],
            )

        return events

    # ── Price checks ──────────────────────────────────────────────────────────

    def _check_price(self, product: Product, history: PriceHistory) -> list[AlertEvent]:
        events = []
        diff = history.price_diff  # positive = price went up, negative = price went down
        if diff is None:
            return events

        # Previous price: current minus diff
        prev_price = history.price - diff
        if prev_price <= 0:
            return events

        pct_change = (diff / prev_price) * 100

        if pct_change <= -self.drop_threshold:
            events.append(AlertEvent(
                alert_type=AlertType.price_drop,
                product_id=str(product.id),
                marketplace=product.marketplace,
                payload={
                    "old_price": prev_price,
                    "new_price": history.price,
                    "diff": diff,
                    "pct": round(pct_change, 2),
                    "currency": history.currency,
                    "title": product.title,
                },
            ))

        elif pct_change >= self.spike_threshold:
            events.append(AlertEvent(
                alert_type=AlertType.price_spike,
                product_id=str(product.id),
                marketplace=product.marketplace,
                payload={
                    "old_price": prev_price,
                    "new_price": history.price,
                    "diff": diff,
                    "pct": round(pct_change, 2),
                    "currency": history.currency,
                    "title": product.title,
                },
            ))

        return events

    # ── Stock checks ──────────────────────────────────────────────────────────

    def _check_stock(self, product: Product, history: PriceHistory) -> list[AlertEvent]:
        events = []

        if not history.is_available:
            events.append(AlertEvent(
                alert_type=AlertType.out_of_stock,
                product_id=str(product.id),
                marketplace=product.marketplace,
                payload={
                    "stock_quantity": history.stock_quantity,
                    "title": product.title,
                },
            ))
        else:
            # Came back in stock — check previous record was out
            events.append(AlertEvent(
                alert_type=AlertType.back_in_stock,
                product_id=str(product.id),
                marketplace=product.marketplace,
                payload={
                    "stock_quantity": history.stock_quantity,
                    "price": history.price,
                    "title": product.title,
                },
            ))

        return events
