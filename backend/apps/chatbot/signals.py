from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings
import logging

from apps.orders.models import Order
from apps.chatbot.twilio_service import TwilioService

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Order)
def order_cancel_message(sender, instance, **kwargs):
    if not getattr(settings, "CHATBOT_AUTO_VERIFY_ENABLED", True):
        return

    if instance.pk:
        old_order = Order.objects.filter(pk=instance.pk).first()
        if old_order and old_order.status != "cancelled" and instance.status == "cancelled":
            # The order was just cancelled by the system or admin
            if instance.customer and instance.customer.phone:
                msg = "Aapka order cancel kar diya gaya hai kyun ke address in-complete tha. Shukriya."
                try:
                    sid = TwilioService.send_whatsapp(to_phone=instance.customer.phone, body=msg)
                    if sid:
                        logger.info("Sent cancellation WhatsApp to %s for order %s", instance.customer.phone, instance.order_id)
                except Exception as e:
                    logger.error("Failed to send cancellation WhatsApp to %s: %s", instance.customer.phone, e)
