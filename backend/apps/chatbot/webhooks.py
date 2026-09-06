"""Twilio webhook endpoints for incoming WhatsApp messages."""

from __future__ import annotations

import logging

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .services import ConversationService
from .twilio_service import TwilioService

logger = logging.getLogger(__name__)


class TwilioIncomingWebhookView(APIView):
    """Receive incoming WhatsApp messages from Twilio.

    Endpoint: ``POST /api/chatbot/webhooks/twilio/incoming/``

    Twilio sends form-encoded data with fields like ``From``, ``Body``,
    ``MessageSid``, etc.  We validate the signature (in production),
    extract the relevant fields, and hand off to the conversation service.

    We always return a 200 so Twilio doesn't retry.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # Twilio doesn't send auth headers

    def post(self, request):
        # Validate Twilio signature
        if not TwilioService.validate_webhook_signature(request):
            logger.warning("Invalid Twilio webhook signature")
            return HttpResponse("Forbidden", status=403)

        # Extract message data from Twilio's POST
        from_number = request.POST.get("From", "") or request.data.get("From", "")
        body = request.POST.get("Body", "") or request.data.get("Body", "")
        message_sid = request.POST.get("MessageSid", "") or request.data.get("MessageSid", "")

        if not from_number or not body:
            logger.warning("Twilio webhook missing From or Body")
            return HttpResponse("OK", status=200)

        logger.info(
            "Incoming WhatsApp: from=%s, body=%s, sid=%s",
            from_number,
            body[:100],
            message_sid,
        )

        # Process the reply
        try:
            result = ConversationService.handle_incoming_reply(
                phone=from_number,
                body=body,
                message_sid=message_sid,
            )
            logger.info("Webhook result: %s", result.get("status", "unknown"))
        except Exception:
            logger.exception("Error processing incoming WhatsApp from %s", from_number)

        # Always return 200 so Twilio doesn't retry
        return HttpResponse("OK", status=200)
