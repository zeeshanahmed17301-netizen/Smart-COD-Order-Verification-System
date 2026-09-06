"""Twilio WhatsApp messaging integration.

Handles sending outbound WhatsApp messages and validating incoming
webhook signatures from Twilio.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioService:
    """Send and receive WhatsApp messages via Twilio."""

    _client = None

    @classmethod
    def is_configured(cls) -> bool:
        """Return whether the platform Twilio WhatsApp sender can send messages."""
        return all(
            [
                getattr(settings, "TWILIO_ACCOUNT_SID", "") or "",
                getattr(settings, "TWILIO_AUTH_TOKEN", "") or "",
                getattr(settings, "TWILIO_WHATSAPP_FROM", "") or "",
            ]
        )

    @classmethod
    def platform_sender_number(cls) -> str:
        """Return the platform WhatsApp sender number configured in the environment."""
        return (getattr(settings, "TWILIO_WHATSAPP_FROM", "") or "").replace("whatsapp:", "").strip()

    @classmethod
    def _get_client(cls):
        """Lazily create a Twilio REST client."""
        if cls._client is not None:
            return cls._client

        try:
            from twilio.rest import Client
        except ImportError:
            logger.error("twilio package not installed. Run: pip install twilio")
            return None

        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""

        if not account_sid or not auth_token:
            logger.warning("Twilio credentials not configured")
            return None

        cls._client = Client(account_sid, auth_token)
        return cls._client

    @classmethod
    def send_whatsapp(cls, to_phone: str, body: str) -> str | None:
        """Send a WhatsApp message via Twilio.

        Args:
            to_phone: Customer phone number (e.g. "+923001234567" or "923001234567").
            body: Message text content.

        Returns:
            Twilio message SID on success, or None on failure.
        """
        client = cls._get_client()
        if client is None:
            logger.warning("Cannot send WhatsApp: Twilio client not available")
            return None

        from_number = getattr(settings, "TWILIO_WHATSAPP_FROM", "")
        if not from_number:
            logger.error("TWILIO_WHATSAPP_FROM not configured")
            return None

        # Normalize the destination phone for WhatsApp
        to_whatsapp = cls._format_whatsapp_number(to_phone)

        try:
            message = client.messages.create(
                body=body,
                from_=from_number,
                to=to_whatsapp,
                status_callback=getattr(settings, "TWILIO_STATUS_CALLBACK_URL", None) or None,
            )
            logger.info(
                "WhatsApp sent: sid=%s, to=%s, body_len=%d",
                message.sid,
                to_whatsapp,
                len(body),
            )
            return message.sid
        except Exception:
            logger.exception("Failed to send WhatsApp message to %s", to_whatsapp)
            return None

    @classmethod
    def validate_webhook_signature(cls, request) -> bool:
        """Validate that an incoming request is genuinely from Twilio.

        In development (TWILIO_VALIDATE_SIGNATURES=False), this always returns True.
        """
        validate = getattr(settings, "TWILIO_VALIDATE_SIGNATURES", "True")
        if str(validate).lower() in ("false", "0", "no"):
            return True

        try:
            from twilio.request_validator import RequestValidator
        except ImportError:
            logger.warning("twilio package not installed, skipping signature validation")
            return True

        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        if not auth_token:
            logger.warning("TWILIO_AUTH_TOKEN not set, skipping validation")
            return True

        validator = RequestValidator(auth_token)

        # Build the URL Twilio used
        url = request.build_absolute_uri()
        # Twilio sends form data
        post_vars = request.POST.dict()
        signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")

        return validator.validate(url, post_vars, signature)

    @classmethod
    def _format_whatsapp_number(cls, phone: str) -> str:
        """Normalize a phone number for Twilio WhatsApp format."""
        phone = (phone or "").strip()

        # Remove existing whatsapp: prefix
        if phone.startswith("whatsapp:"):
            return phone

        # Ensure it starts with +
        if not phone.startswith("+"):
            # Assume Pakistani number if starts with 0
            if phone.startswith("0"):
                phone = "+92" + phone[1:]
            elif phone.startswith("92"):
                phone = "+" + phone
            else:
                phone = "+" + phone

        return f"whatsapp:{phone}"

    @classmethod
    def extract_phone_from_whatsapp(cls, whatsapp_from: str) -> str:
        """Extract a clean phone number from Twilio's whatsapp: format.

        e.g. "whatsapp:+923001234567" → "+923001234567"
        """
        return (whatsapp_from or "").replace("whatsapp:", "").strip()
