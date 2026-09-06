"""Celery tasks for the rule-based risk engine."""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction


logger = logging.getLogger(__name__)


@shared_task(
    name="risk_engine.score_order",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def score_order(self, order_id: int) -> dict:
    """Score or re-score an order asynchronously."""
    from apps.orders.models import Order
    from apps.risk_engine.services import RiskScoringEngine

    try:
        order = (
            Order.objects.select_related(
                "customer", "address", "merchant", "source_snapshot", "enrichment"
            )
            .prefetch_related("items")
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        logger.warning("score_order: order id=%s no longer exists", order_id)
        return {"status": "missing", "order_id": order_id}

    result = RiskScoringEngine.score_and_save(order)
    logger.info(
        "Scored order %s async: risk=%.1f level=%s action=%s",
        order.order_id,
        result.risk_score,
        result.risk_level,
        result.recommended_action,
    )
    return {
        "status": "scored",
        "order_id": order_id,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "recommended_action": result.recommended_action,
    }


def enqueue_score_order(order_id: int) -> None:
    """Schedule a scoring task after the current DB transaction commits."""

    transaction.on_commit(lambda: score_order.delay(order_id))