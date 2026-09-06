"""Conversation orchestrator for LLM-powered address verification.

This is the core service that ties together:
- Risk engine triggers → auto-start conversations
- DeepSeek LLM → generate messages and parse replies
- Twilio → send/receive WhatsApp messages
- Address model → update verified address data
- Risk engine → re-score after address update
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .llm import DeepSeekClient
from .models import Conversation, Message, WhatsAppInteraction
from .twilio_service import TwilioService

if TYPE_CHECKING:
    from apps.orders.models import Order

logger = logging.getLogger(__name__)


class ConversationService:
    """Orchestrate WhatsApp conversations for address verification."""

    # ── Auto-trigger (called by risk engine after scoring) ───────────────

    @classmethod
    def auto_trigger_if_needed(cls, order: Order, risk_result) -> Conversation | None:
        """Auto-start address verification if criteria are met.

        Called from ``RiskScoringEngine.score_and_save()`` after scoring.
        """
        if not getattr(settings, "CHATBOT_AUTO_VERIFY_ENABLED", True):
            return None

        # Only trigger for verification-related actions OR if fraud/rto scores are >= 50
        action = getattr(risk_result, "recommended_action", "")
        fraud_score = getattr(risk_result, "fraud_score", 0.0)
        rto_score = getattr(risk_result, "rto_probability_score", 0.0)
        
        if fraud_score < 50.0 and rto_score < 50.0 and action not in ("verify_address", "call_customer"):
            return None

        # Don't trigger if a conversation has ever been created for this order
        if Conversation.objects.filter(order=order).exists():
            logger.debug(
                "Conversation already exists for order %s — skipping WhatsApp trigger",
                order.order_id,
            )
            return None

        if not TwilioService.is_configured():
            logger.debug("Platform WhatsApp sender is not configured")
            return None

        try:
            chatbot_settings = order.merchant.chatbot_settings
            if not chatbot_settings.auto_send_confirmation:
                return None
        except Exception:
            pass

        # Customer must have a phone number
        customer_phone = cls._delivery_phone(order)
        if not customer_phone:
            logger.debug("No customer phone for order %s", order.order_id)
            return None

        # All checks passed — start conversation
        return cls.start_conversation(order, purpose="address_verification")

    # ── Start conversation ───────────────────────────────────────────────

    @classmethod
    def start_conversation(
        cls,
        order: Order,
        purpose: str = "address_verification",
    ) -> Conversation | None:
        """Create a conversation, generate the first LLM message, send via Twilio."""
        customer = order.customer
        address = order.address

        # Determine what fields are missing at conversation start
        missing = cls._determine_missing_fields(address)

        # Build order context for the LLM
        order_context = cls._build_order_context(order)

        # Get merchant language preference
        language = "Roman Urdu"
        try:
            lang_setting = order.merchant.chatbot_settings.language
            language = {
                "urdu": "Roman Urdu",
                "english": "English",
                "roman_urdu": "Roman Urdu",
            }.get(lang_setting, "Roman Urdu")
        except Exception:
            pass

        message_text = ""

        template_text = cls._get_merchant_template(order, "greeting_template")
        if template_text:
            message_text = cls._render_template(template_text, order)

        if not message_text:
            # Generate the first message via LLM
            message_text = DeepSeekClient.generate_message(
                order_context=order_context,
                conversation_history=None,
                missing_fields=missing,
                language=language,
                step=1,
            )

        if not message_text:
            # LLM failed — use a simple template fallback
            message_text = cls._fallback_greeting(order, missing, language)

        # Create or return the existing conversation record (idempotent on rescore)
        conversation, created = Conversation.objects.get_or_create(
            order=order,
            defaults=dict(
                status="awaiting_reply",
                purpose=purpose,
                missing_fields=missing,
                collected_data={},
                turn_count=1,
                last_message_at=timezone.now(),
            ),
        )
        if not created:
            # Conversation already exists — skip re-sending WhatsApp
            return conversation

        # Send via Twilio
        message_sid = TwilioService.send_whatsapp(
            to_phone=cls._delivery_phone(order),
            body=message_text,
        )

        # Save the bot message
        Message.objects.create(
            conversation=conversation,
            sender="bot",
            content=message_text,
            message_sid=message_sid or "",
            llm_model=getattr(settings, "DEEPSEEK_MODEL", ""),
        )

        # Update interaction summary
        WhatsAppInteraction.objects.update_or_create(
            order=order,
            defaults={
                "last_message_sent": timezone.now(),
                "nudges_sent": 1,
            },
        )

        if message_sid:
            logger.info(
                "Started %s conversation for order %s (sid=%s), missing=%s",
                purpose,
                order.order_id,
                message_sid,
                missing,
            )
        else:
            logger.warning(
                "Conversation created for order %s but Twilio send failed",
                order.order_id,
            )
            conversation.status = "failed"
            conversation.save(update_fields=["status"])

        return conversation

    @classmethod
    def send_admin_confirmation_message(cls, order: Order) -> str | None:
        """Send the admin confirmation template via WhatsApp."""
        context = cls._build_order_context(order)
        body = (
            f"Assalam o Alaikum! Your order #{order.order_id} has been received. "
            f"Name: {context['customer_name']}. "
            f"Phone: {context['phone']}. "
            f"Address: {context['current_address']}. "
            f"Amount: {context['amount']}. Reply YES to confirm."
        )
        return cls._send_admin_message(
            order,
            body=body,
            purpose="order_confirmation",
            conversation_status="awaiting_reply",
        )

    @classmethod
    def send_admin_cancellation_message(cls, order: Order) -> str | None:
        """Send the admin cancellation template via WhatsApp."""
        body = (
            "Your order has been cancelled due to incomplete or invalid information. "
            "Please place a new order with correct details."
        )
        return cls._send_admin_message(
            order,
            body=body,
            purpose="order_confirmation",
            conversation_status="cancelled",
        )

    @classmethod
    def _send_admin_message(
        cls,
        order: Order,
        *,
        body: str,
        purpose: str,
        conversation_status: str,
    ) -> str | None:
        phone = cls._delivery_phone(order)
        if not phone:
            logger.info("Admin WhatsApp message skipped for %s: no delivery phone", order.order_id)
            return None
        if not TwilioService.is_configured():
            logger.info("Admin WhatsApp message skipped for %s: Twilio not configured", order.order_id)
            return None

        conversation, _ = Conversation.objects.get_or_create(
            order=order,
            defaults={
                "status": conversation_status,
                "purpose": purpose,
                "missing_fields": [],
                "collected_data": {},
                "turn_count": 0,
                "last_message_at": timezone.now(),
            },
        )

        conversation.status = conversation_status
        conversation.purpose = purpose
        conversation.last_message_at = timezone.now()
        if conversation_status == "cancelled":
            conversation.completed_at = timezone.now()
            conversation.save(update_fields=["status", "purpose", "last_message_at", "completed_at"])
        else:
            conversation.save(update_fields=["status", "purpose", "last_message_at"])

        message_sid = TwilioService.send_whatsapp(to_phone=phone, body=body)
        Message.objects.create(
            conversation=conversation,
            sender="bot",
            content=body,
            message_sid=message_sid or "",
        )

        interaction, _ = WhatsAppInteraction.objects.get_or_create(order=order)
        interaction.last_message_sent = timezone.now()
        interaction.nudges_sent += 1
        interaction.save(update_fields=["last_message_sent", "nudges_sent"])
        return message_sid

    # ── Handle incoming customer reply ───────────────────────────────────

    @classmethod
    def handle_incoming_reply(
        cls, phone: str, body: str, message_sid: str = ""
    ) -> dict:
        """Process an incoming WhatsApp reply from a customer.

        Called by the Twilio webhook view.
        Returns a dict with the processing result for logging.
        """
        from apps.customers.normalization import normalize_phone

        # Normalize the incoming phone
        clean_phone = TwilioService.extract_phone_from_whatsapp(phone)
        normalized = normalize_phone(clean_phone)

        # Find the active conversation for this phone
        conversation = cls._find_active_conversation(clean_phone)
        if not conversation:
            recent_completed = cls._find_recent_completed_conversation(clean_phone)
            if recent_completed:
                logger.info("Found completed conversation for phone %s. Sending ETA reply.", clean_phone)
                sid = TwilioService.send_whatsapp(phone, "Aapka order process ho chuka hai aur 3-4 din mein deliver ho jaye gaa. Shukriya!")
                return {"status": "post_order_faq", "phone": clean_phone}
            
            logger.info("No active or recent conversation for phone %s", clean_phone)
            return {"status": "no_conversation", "phone": clean_phone}

        order = conversation.order
        address = order.address

        # Save the customer's message
        user_message = Message.objects.create(
            conversation=conversation,
            sender="user",
            content=body,
            message_sid=message_sid,
        )

        # Record first reply timing
        interaction, _ = WhatsAppInteraction.objects.get_or_create(order=order)
        if not interaction.customer_response:
            interaction.customer_response = body[:200]
            if interaction.last_message_sent:
                delta = timezone.now() - interaction.last_message_sent
                minutes = int(delta.total_seconds() / 60)
                interaction.time_to_first_reply = (
                    f"{minutes}m" if minutes < 60 else f"{minutes // 60}h {minutes % 60}m"
                )
            interaction.save()

        # Update conversation tracking
        conversation.status = "processing"
        conversation.turn_count += 1
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=["status", "turn_count", "last_message_at"])

        # Get conversation history for LLM context
        history = cls._get_conversation_history(conversation)

        # Ask LLM to extract address from the reply
        current_address = address.full_address if address else ""
        parsed = DeepSeekClient.extract_address(
            customer_reply=body,
            conversation_history=history,
            current_address=current_address,
        )

        # Save parsed data on the message
        user_message.parsed_data = parsed
        user_message.llm_model = getattr(settings, "DEEPSEEK_MODEL", "")
        user_message.save(update_fields=["parsed_data", "llm_model"])

        logger.info(
            "Parsed reply for order %s: intent=%s, confidence=%.1f, extracted=%s",
            order.order_id,
            parsed.get("intent"),
            parsed.get("confidence", 0),
            {k: v for k, v in parsed.items() if k in ("city", "area", "street", "landmark") and v},
        )

        # Handle based on detected intent
        intent = parsed.get("intent", "unclear")
        confidence = cls._confidence_to_percent(parsed.get("confidence", 0.0))

        if intent == "order_cancel":
            return cls._handle_cancellation(conversation, order)

        # Merge any extracted address data
        cls._merge_collected_data(conversation, parsed)
        still_missing = cls._get_still_missing(conversation)

        # If all required fields are now present, complete without extra probing.
        if not still_missing and intent in ("address_update", "order_confirm"):
            conversation.step = 4
        
        # Step-based routing
        if conversation.step == 1:
            if intent in ("order_confirm", "address_update"):
                conversation.step = 2
            elif intent == "doesnt_know":
                conversation.step = 3
            else:
                conversation.step = 3  # fallback to probing
                
        elif conversation.step == 2:
            if intent == "address_update" and confidence >= 40:
                conversation.step = 4
            else:
                conversation.step = 3  # Start probing
                
        elif conversation.step == 3:
            if intent == "address_update" and confidence >= 40:
                conversation.step = 4
                
        conversation.missing_fields = still_missing
        conversation.save(update_fields=["missing_fields", "collected_data", "step"])

        if conversation.step == 4:
            return cls._finalize_address(conversation, order)

        # Max turn safety valve
        max_turns = getattr(settings, "CHATBOT_MAX_TURNS", 10)
        if conversation.turn_count >= max_turns:
            return cls._finalize_address(conversation, order, partial=True)

        return cls._send_followup(
            conversation, order, still_missing,
            customer_last_reply=body,
        )

    # ── Internal orchestration methods ───────────────────────────────────

    @classmethod
    def _handle_doesnt_know(
        cls, conversation: Conversation, order: Order, customer_reply: str
    ) -> dict:
        """Handle customer saying they don't know the answer.

        Instead of giving up, we rephrase the question with examples/landmarks
        to help them figure out their area.
        """
        missing = conversation.missing_fields or ["area"]

        # Track consecutive doesnt_know responses
        doesnt_know_count = conversation.collected_data.get("_doesnt_know_count", 0) + 1
        conversation.collected_data["_doesnt_know_count"] = doesnt_know_count
        conversation.save(update_fields=["collected_data"])

        if doesnt_know_count >= 3:
            # They genuinely don't know after 3 attempts — finalize with what we have
            return cls._finalize_address(conversation, order, partial=True)

        # Send a helpful follow-up that rephrases the question
        return cls._send_followup(
            conversation, order, missing,
            customer_last_reply=customer_reply,
        )

    @classmethod
    def _finalize_address(
        cls, conversation: Conversation, order: Order, partial: bool = False
    ) -> dict:
        """Apply collected data to address, re-score, and send confirmation."""
        collected = conversation.collected_data or {}

        # Strip internal tracking keys before applying
        clean_collected = {k: v for k, v in collected.items() if not k.startswith("_")}

        # Update the address model
        cls._update_address_from_collected(order, clean_collected)

        order.chat_status = "unverified" if partial else "confirmed"
        order.save(update_fields=["chat_status", "updated_at"])

        # Re-score the order with updated address and confirmation status.
        risk_result = cls._rescore_order(order)
        if (
            not partial
            and order.status == "pending"
            and risk_result
            and risk_result.recommended_action == "ship_order"
        ):
            order.status = "verified"
            order.save(update_fields=["status", "updated_at"])

        # Send confirmation message
        confirm_text = ""
        if not partial:
            template_text = cls._get_merchant_template(order, "confirmation_template")
            if template_text:
                confirm_text = cls._render_template(template_text, order)

        if not confirm_text and partial:
            confirm_text = cls._generate_response(
                conversation, order, [],
                override_prompt="The maximum follow-up limit has been reached. "
                "Thank the customer for the information they provided and let them "
                "know their order will be processed. Be brief and polite.",
            )
        elif not confirm_text:
            confirm_text = cls._generate_response(
                conversation, order, [],
                override_prompt="The address has been fully verified. "
                "Thank the customer warmly and confirm the complete delivery address. "
                "Let them know the order will be dispatched soon.",
            )

        if confirm_text:
            sid = TwilioService.send_whatsapp(cls._delivery_phone(order), confirm_text)
            Message.objects.create(
                conversation=conversation,
                sender="bot",
                content=confirm_text,
                message_sid=sid or "",
                llm_model=getattr(settings, "DEEPSEEK_MODEL", ""),
            )

        # Mark conversation complete
        conversation.status = "completed"
        conversation.completed_at = timezone.now()
        conversation.save(update_fields=["status", "completed_at", "missing_fields", "collected_data"])

        # Update interaction summary
        WhatsAppInteraction.objects.filter(order=order).update(
            address_clarification=clean_collected.get("area", "") or clean_collected.get("city", "")[:200],
        )

        status = "completed_partial" if partial else "completed"
        logger.info(
            "Address verification %s for order %s, collected=%s",
            status, order.order_id, clean_collected,
        )
        return {"status": status, "collected": clean_collected}

    @classmethod
    def _send_followup(
        cls,
        conversation: Conversation,
        order: Order,
        missing_fields: list[str],
        customer_last_reply: str = "",
    ) -> dict:
        """Generate and send a follow-up question asking for missing fields."""
        followup_text = cls._generate_response(
            conversation, order, missing_fields,
            customer_last_reply=customer_last_reply,
        )

        if not followup_text:
            followup_text = cls._fallback_followup(missing_fields)

        sid = TwilioService.send_whatsapp(cls._delivery_phone(order), followup_text)

        Message.objects.create(
            conversation=conversation,
            sender="bot",
            content=followup_text,
            message_sid=sid or "",
            llm_model=getattr(settings, "DEEPSEEK_MODEL", ""),
        )

        conversation.status = "awaiting_reply"
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=["status", "last_message_at", "missing_fields", "collected_data"])

        # Update nudge count
        WhatsAppInteraction.objects.filter(order=order).update(
            nudges_sent=conversation.turn_count,
            last_message_sent=timezone.now(),
        )

        return {"status": "followup_sent", "missing": missing_fields}

    @classmethod
    def _handle_cancellation(cls, conversation: Conversation, order: Order) -> dict:
        """Handle customer wanting to cancel the order."""
        cancel_text = cls._generate_response(
            conversation, order, [],
            override_prompt="The customer wants to cancel their order. "
            "Acknowledge politely and let them know the order has been noted for cancellation.",
        )
        if cancel_text:
            sid = TwilioService.send_whatsapp(cls._delivery_phone(order), cancel_text)
            Message.objects.create(
                conversation=conversation,
                sender="bot",
                content=cancel_text,
                message_sid=sid or "",
            )

        conversation.status = "cancelled"
        conversation.completed_at = timezone.now()
        conversation.save(update_fields=["status", "completed_at"])

        order.status = "cancelled"
        order.chat_status = "denied"
        order.recommended_action = "cancel_order"
        order.customer.cancelled_count += 1
        order.save(update_fields=["status", "chat_status", "recommended_action", "updated_at"])
        order.customer.save(update_fields=["cancelled_count", "updated_at"])

        # Log as system message
        Message.objects.create(
            conversation=conversation,
            sender="system",
            content="Customer requested order cancellation via WhatsApp.",
        )

        logger.info("Customer cancelled order %s via WhatsApp", order.order_id)
        return {"status": "cancelled"}

    @classmethod
    def _handle_confirmation(cls, conversation: Conversation, order: Order) -> dict:
        """Handle customer simply confirming the order (no address change)."""
        return cls._finalize_address(conversation, order)

    # ── Data helpers ─────────────────────────────────────────────────────

    @classmethod
    def _determine_missing_fields(cls, address) -> list[str]:
        """Check which address fields are empty/weak on the actual DB record.

        This is called ONCE at conversation start to determine the initial
        set of fields to collect. After that, we track via collected_data.
        """
        missing = []

        city = (getattr(address, "city", "") or "") if address else ""
        if not city or city.lower() in ("unknown", "n/a", ""):
            missing.append("city")

        area = (getattr(address, "district", "") or "") if address else ""
        if not area:
            missing.append("area")

        full = (getattr(address, "full_address", "") or "") if address else ""
        # If full address is very short or generic, still ask
        if len(full) < 15:
            if "street" not in missing:
                missing.append("street")

        return missing

    @classmethod
    def _get_still_missing(cls, conversation: Conversation) -> list[str]:
        """Determine which originally-missing fields are still not collected.

        This compares the conversation's original missing_fields against
        what has been explicitly collected via collected_data. A field is
        only considered resolved when the customer explicitly provided it.
        """
        original_missing = conversation.missing_fields or []
        collected = conversation.collected_data or {}

        still_missing = []
        for field in original_missing:
            collected_value = collected.get(field, "")
            if not collected_value or not str(collected_value).strip():
                still_missing.append(field)

        return still_missing

    @classmethod
    def _merge_collected_data(cls, conversation: Conversation, parsed: dict) -> None:
        """Merge newly extracted data into conversation.collected_data."""
        collected = conversation.collected_data or {}

        # Only overwrite with non-empty values
        for key in ("city", "area", "street", "house", "landmark", "postal_code", "full_address"):
            value = parsed.get(key, "")
            if value and value.strip():
                collected[key] = value.strip()

        conversation.collected_data = collected
        conversation.save(update_fields=["collected_data"])

    @classmethod
    def _update_address_from_collected(cls, order: Order, collected: dict) -> None:
        """Apply LLM-extracted address data back to the Address model."""
        address = order.address
        if not address:
            return

        changed = False

        if collected.get("city"):
            address.city = collected["city"]
            changed = True
        if collected.get("area"):
            address.district = collected["area"]
            changed = True
        if collected.get("postal_code"):
            address.postal_code = collected["postal_code"]
            changed = True
        if collected.get("full_address") and len(collected["full_address"]) > len(address.full_address or ""):
            address.full_address = collected["full_address"]
            changed = True
            address.suggested_address = collected["full_address"]

        # Build enriched full address if we have new components
        if changed and collected.get("city") and not collected.get("full_address"):
            parts = [
                collected.get("house", ""),
                collected.get("street", ""),
                collected.get("area", ""),
                collected.get("landmark", ""),
                collected.get("city", ""),
                collected.get("postal_code", ""),
            ]
            new_full = ", ".join(p for p in parts if p)
            if len(new_full) > len(address.full_address or ""):
                address.full_address = new_full
                address.suggested_address = new_full

        if changed:
            address.validation_provider = "whatsapp_llm_verification"
            address.save()
            logger.info(
                "Address updated via WhatsApp for order %s: city=%s, area=%s",
                order.order_id,
                address.city,
                address.district,
            )

    @classmethod
    def _rescore_order(cls, order: Order):
        """Re-run the risk scoring pipeline after address update."""
        try:
            from apps.risk_engine.services import RiskScoringEngine

            result = RiskScoringEngine.score_and_save(order)
            logger.info("Order %s re-scored after WhatsApp verification", order.order_id)
            return result
        except Exception:
            logger.exception("Failed to re-score order %s", order.order_id)
            return None

    @classmethod
    def _build_order_context(cls, order: Order) -> dict:
        """Build the order context dict for LLM message generation."""
        customer = order.customer
        address = order.address
        items_list = []
        for item in order.items.all()[:5]:
            items_list.append(f"{item.name} × {item.qty}")

        order_id = str(getattr(order, "order_id", "") or getattr(order, "id", "") or "")
        amount = f"Rs. {order.amount:,.0f}" if order.amount else ""
        current_address = address.full_address if address else ""

        return {
            "customer_name": customer.name if customer else "Customer",
            "phone": customer.phone if customer else "",
            "items": ", ".join(items_list) or "order",
            "amount": amount,
            "order_amount": amount,
            "order_id": order_id,
            "current_address": current_address,
            "address": current_address,
            "city": (address.city if address else "") or "",
        }

    @classmethod
    def _get_merchant_template(cls, order: Order, field: str) -> str:
        try:
            settings_obj = order.merchant.chatbot_settings
        except Exception:
            return ""

        template = getattr(settings_obj, field, "") or ""
        return template.strip()

    @classmethod
    def _render_template(cls, template: str, order: Order) -> str:
        if not template:
            return ""

        context = cls._build_order_context(order)
        rendered = template

        for key, value in context.items():
            value_str = str(value or "")
            rendered = rendered.replace(f"{{{{{key}}}}}", value_str)
            rendered = rendered.replace(f"{{{key}}}", value_str)

        return rendered.strip()

    @classmethod
    def _delivery_phone(cls, order: Order) -> str:
        """Prefer source-system customer phone over merchant-entered or address phone fields."""
        try:
            from apps.orders.source_facts import build_canonical_order_facts

            facts = build_canonical_order_facts(order, getattr(order, "source_snapshot", None)) or {}
            canonical_customer = facts.get("customer") or {}
            if canonical_customer.get("phone"):
                return canonical_customer["phone"]
        except Exception:
            logger.debug("Could not build canonical phone for order %s", order.order_id, exc_info=True)

        customer = getattr(order, "customer", None)
        return getattr(customer, "phone", "") or ""

    @staticmethod
    def _confidence_to_percent(value) -> float:
        """Normalize LLM confidence to a 0-100 scale (supports 0-1 or 0-100 inputs)."""
        try:
            confidence = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

        if confidence <= 1.0:
            confidence *= 100.0

        return round(max(0.0, min(confidence, 100.0)), 2)

    @classmethod
    def _get_conversation_history(cls, conversation: Conversation) -> list[dict]:
        """Get recent messages as a list of dicts for LLM context."""
        messages = conversation.messages.order_by("timestamp")[:10]
        return [
            {"sender": msg.sender, "content": msg.content}
            for msg in messages
        ]

    @classmethod
    def _find_active_conversation(cls, phone: str) -> Conversation | None:
        """Find an active conversation by customer phone number."""
        candidates = cls._phone_lookup_candidates(phone)
        return (
            Conversation.objects.filter(
                Q(order__customer__phone__in=candidates)
                | Q(order__source_snapshot__raw_order_payload__phone__in=candidates)
                | Q(order__source_snapshot__raw_order_payload__customer__phone__in=candidates)
                | Q(order__source_snapshot__raw_order_payload__shipping_address__phone__in=candidates),
                status__in=("active", "awaiting_reply"),
            )
            .select_related("order", "order__customer", "order__address")
            .order_by("-started_at")
            .first()
        )

    @classmethod
    def _find_recent_completed_conversation(cls, phone: str) -> Conversation | None:
        """Find a recently completed conversation to handle 'where is my parcel' FAQs."""
        candidates = cls._phone_lookup_candidates(phone)
        return (
            Conversation.objects.filter(
                Q(order__customer__phone__in=candidates)
                | Q(order__source_snapshot__raw_order_payload__phone__in=candidates)
                | Q(order__source_snapshot__raw_order_payload__customer__phone__in=candidates)
                | Q(order__source_snapshot__raw_order_payload__shipping_address__phone__in=candidates),
                status__in=("completed", "timeout"),
            )
            .order_by("-completed_at")
            .first()
        )

    @staticmethod
    def _phone_lookup_candidates(phone: str) -> list[str]:
        """Build resilient phone lookup candidates for local and E.164 formats."""
        from apps.customers.normalization import normalize_phone

        raw = (phone or "").replace("whatsapp:", "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        normalized = normalize_phone(raw)

        candidates = {raw, digits, normalized}

        if normalized and normalized.startswith("+92") and len(normalized) == 13:
            candidates.add(normalized[1:])
            candidates.add(f"0{normalized[3:]}")

        if digits.startswith("0") and len(digits) == 11:
            candidates.add(f"+92{digits[1:]}")
            candidates.add(f"92{digits[1:]}")
        elif digits.startswith("92") and len(digits) == 12:
            candidates.add(f"+{digits}")
            candidates.add(f"0{digits[2:]}")
        elif digits.startswith("3") and len(digits) == 10:
            candidates.add(f"+92{digits}")
            candidates.add(f"92{digits}")
            candidates.add(f"0{digits}")

        return [candidate for candidate in candidates if candidate]

    @classmethod
    def _generate_response(
        cls,
        conversation: Conversation,
        order: Order,
        missing_fields: list[str],
        override_prompt: str = "",
        customer_last_reply: str = "",
    ) -> str | None:
        """Generate an LLM response for the conversation."""
        order_context = cls._build_order_context(order)
        history = cls._get_conversation_history(conversation)

        language = "Roman Urdu"
        try:
            lang_setting = order.merchant.chatbot_settings.language
            language = {"urdu": "Roman Urdu", "english": "English"}.get(lang_setting, "Roman Urdu")
        except Exception:
            pass

        if override_prompt:
            # For special messages (confirmation, cancellation)
            return DeepSeekClient.chat(
                system_prompt=(
                    f"You are a friendly delivery assistant. {override_prompt} "
                    f"Write in {language}. Keep it under 200 characters. "
                    f"Customer: {order_context['customer_name']}. "
                    f"Order: {order_context['items']}."
                ),
                messages=[{"role": "user", "content": "Generate the message."}],
                temperature=0.5,
            )

        return DeepSeekClient.generate_message(
            order_context=order_context,
            conversation_history=history,
            missing_fields=missing_fields,
            language=language,
            customer_last_reply=customer_last_reply,
            step=conversation.step,
        )

    # ── Fallback templates ───────────────────────────────────────────────

    @classmethod
    def _fallback_greeting(cls, order: Order, missing: list[str], language: str) -> str:
        """Simple template greeting when LLM is unavailable."""
        name = order.customer.name if order.customer else "Customer"

        # Build items line: "Item A (x2), Item B (x1)"
        item_parts = []
        for item in order.items.all()[:3]:
            qty = getattr(item, "quantity", 1) or 1
            item_parts.append(f"{item.name} (x{qty})")
        items_text = ", ".join(item_parts) or "your items"

        amount = getattr(order, "total_price", None) or getattr(order, "amount", "")
        try:
            amount_str = f"{float(amount):,.2f}"
        except (TypeError, ValueError):
            amount_str = str(amount)

        address_text = ""
        try:
            a = order.address
            parts = [p for p in [
                getattr(a, "street_address", "") or "",
                getattr(a, "area", "") or "",
                getattr(a, "city", "") or "",
            ] if p]
            address_text = ", ".join(parts) or "Not provided"
        except Exception:
            address_text = "Not provided"

        order_ref = str(order.order_id)[-8:] if order.order_id else "N/A"

        return (
            f"📦 *Order Summary*\n\n"
            f"📦 Items: {items_text}\n"
            f"💰 Total: PKR {amount_str}\n"
            f"👤 Name: {name}\n"
            f"📍 Address: {address_text}\n"
            f"🗒️ Order: #{order_ref}\n\n"
            f"🚀 We will ship once you confirm!\n\n"
            f"Reply with:\n"
            f"✅ *1* - Confirm Order\n"
            f"📞 *2* - Cancel"
        )

    @classmethod
    def _fallback_followup(cls, missing: list[str]) -> str:
        """Simple fallback follow-up when LLM is unavailable."""
        missing_urdu = {
            "city": "sheher ka naam",
            "area": "area ya mohalla",
            "street": "gali ka naam/number",
            "postal_code": "postal code",
        }
        parts = [missing_urdu.get(f, f) for f in missing]
        return f"Shukriya! Baraaye meherbani {' aur '.join(parts)} bhi bata dein? 🙏"
