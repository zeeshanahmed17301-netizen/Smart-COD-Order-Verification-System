import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from celery import shared_task

from apps.chatbot.models import Conversation
from apps.orders.models import Order

logger = logging.getLogger(__name__)

@shared_task
def check_chat_timeouts():
    """Identify conversations that have been abandoned by the customer.
    
    If no reply is received within CHATBOT_NO_REPLY_TIMEOUT_HOURS (default 5),
    mark the conversation as timeout and recommend manual review.
    """
    timeout_hours = getattr(settings, 'CHATBOT_NO_REPLY_TIMEOUT_HOURS', 5)
    cutoff_time = timezone.now() - timedelta(hours=timeout_hours)
    
    # Find active or awaiting_reply conversations that haven't been updated
    stale_convos = Conversation.objects.filter(
        status__in=["active", "awaiting_reply"],
        last_message_at__lte=cutoff_time
    ).select_related('order')
    
    count = 0
    for convo in stale_convos:
        # Update conversation status
        convo.status = "timeout"
        convo.completed_at = timezone.now()
        convo.save(update_fields=["status", "completed_at"])
        
        # Update related order
        order = convo.order
        order.chat_status = "timeout"
        order.customer.ghosted_count += 1
        order.save(update_fields=["chat_status", "updated_at"])
        order.customer.save(update_fields=["ghosted_count", "updated_at"])

        # Re-score so the ghost is reflected in fraud/RTO/contactability. The new
        # recommended_action comes out of the engine rather than being hardcoded.
        try:
            from apps.risk_engine.services import RiskScoringEngine

            RiskScoringEngine.score_and_save(order, skip_chatbot=True)
        except Exception:
            logger.exception("Re-scoring after chat timeout failed for order %s", order.order_id)

        logger.info("Conversation %s for order %s timed out after %s hours; order re-scored.", convo.id, order.order_id, timeout_hours)
        count += 1
        
    return f"Timed out {count} conversations."
