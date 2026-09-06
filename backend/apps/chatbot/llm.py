"""DeepSeek LLM client for conversational address verification.

Uses the OpenAI-compatible SDK pointed at DeepSeek's API endpoint.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

# ── Prompt templates ─────────────────────────────────────────────────────────

ADDRESS_EXTRACTION_SYSTEM = """\
You are an address parser for a COD (Cash-on-Delivery) delivery service in Pakistan.
Given a customer's WhatsApp reply (which may be in Urdu, English, Roman Urdu, or regional languages like Pashto/Punjabi), extract structured address components.

IMPORTANT RULES:
- Understand Roman Urdu and regional languages (e.g. Pashto, Punjabi, Sindhi)
- "sheher" means city, "gali" means street/lane, "mohalla" means neighborhood/area
- Common city aliases: ISB/isloo = Islamabad, LHR = Lahore, KHI = Karachi, RWP = Rawalpindi, MUL = Multan, PSH = Peshawar
- If the customer mentions a landmark, extract it

INTENT RULES (choose exactly one):
- "address_update": The customer provided actual address information (a city name, area, street, landmark, etc.)
- "order_confirm": They explicitly confirmed the existing address is correct ("haan", "theek hai", "yes", "correct", "sahi hai")
- "order_cancel": They want to cancel the order ("cancel kardo", "nahi chahiye")
- "doesnt_know": They said they don't know the answer to what was asked ("mujhe nhi pata", "pata nahi", "nhi pta", "I don't know", "malom nhi", "kha kha za drta waim" — meaning unclear/confused response)
- "question": They asked a question about the order or process
- "greeting": They just said hello/salam without any address info
- "unclear": None of the above — genuinely cannot determine intent

CRITICAL RULES:
- We provide "Current known address" for context. DO NOT copy data from it. ONLY extract address data the customer EXPLICITLY states in their NEW reply.
- If the customer's reply contains NO address information at all (greetings, questions, "I don't know"), ALL address fields MUST be empty strings.
- "needs_followup" = true if the customer did NOT provide the data we asked for.
- Set "confidence" to 0.0 if no address data was extracted.

ALWAYS respond with valid JSON only. No explanation, no markdown, no code blocks.
Schema:
{
  "city": "",
  "area": "",
  "street": "",
  "house": "",
  "landmark": "",
  "postal_code": "",
  "full_address": "",
  "confidence": 0.0,
  "intent": "address_update|order_confirm|order_cancel|doesnt_know|question|greeting|unclear",
  "needs_followup": true,
  "missing": []
}
"""

MESSAGE_GENERATION_SYSTEM = """\
You are a friendly delivery verification assistant for an e-commerce store in Pakistan.
A customer placed a COD (Cash on Delivery) order and you need to verify their delivery address via WhatsApp.

RULES:
- Respond naturally and conversationally to exactly what the customer just said.
- Write in the SAME language the customer used (including Pashto, Punjabi, etc.). If this is the first message, use {language}.
- Be polite, warm, and concise — this is WhatsApp, not email.
- For Urdu, write in Roman Urdu (transliterated) since most Pakistani customers use it.
- Never ask for payment info, CNIC, or other sensitive data.
- Keep messages short (under 300 characters).

CONVERSATION STEP INSTRUCTIONS:
You are currently generating a message for Step {step} of the verification flow.

Step 1 (Order Confirmation): Send ONE single structured message showing the order summary and asking the customer to confirm.
Format EXACTLY like this (use the actual order data, keep the emoji icons):

"📦 *Order Summary*

📦 Items: [Items]
💰 Total: PKR [Amount]
👤 Name: [Customer Name]
📍 Address: [Address]
🗒️ Order: #[Order ID or short reference]

🚀 We will ship once you confirm!

Reply with:
✅ *1* - Confirm Order
📞 *2* - Need Confirmation Call Before Dispatch"

Do NOT add any extra greeting or text. Output ONLY the formatted block above.

Step 2 (Landmark Request): The user has confirmed the order. Now politely ask them to share a famous landmark.
Example: "Shukriya! Delivery exactly aapke paas pohnchane ke liye — kya aap apne ghar ke paas koi famous jagah ya landmark bata sakte hain? (jaise market, masjid, school)"

Step 3 (Human-like Probing): The address or landmark given was unclear. Start a natural human-like conversation to figure out the real details. If they said "I don't know", help them.

Step 4 (Final ETA): Thank the customer and give them delivery expectations.
Example: "Shukriya [Name]! Aapka order 3-4 din mein deliver ho jayega. Apna number chalu rakhein, aapko rider ki call aa sakti hai. 😊"

WHAT THE CUSTOMER JUST SAID: {customer_last_reply}

CURRENT ORDER CONTEXT:
- Customer: {customer_name}
- Phone: {customer_phone}
- Items: {items}
- Amount: {amount}
- Current Address: {current_address}
- Missing Fields: {missing_fields}

CONVERSATION HISTORY:
{history}

Generate ONLY the message text. No JSON, no explanation.
"""


def _get_client():
    """Lazily create an OpenAI client pointed at DeepSeek."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        return None

    api_key = getattr(settings, "DEEPSEEK_API_KEY", "")
    if not api_key:
        logger.warning("DEEPSEEK_API_KEY not configured")
        return None

    return OpenAI(
        api_key=api_key,
        base_url=getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )


class DeepSeekClient:
    """Stateless DeepSeek API client for address verification conversations."""

    @classmethod
    def chat(
        cls,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> str | None:
        """Send a chat completion request. Returns the assistant's reply text."""
        client = _get_client()
        if client is None:
            return None

        model = getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
        timeout = getattr(settings, "DEEPSEEK_TIMEOUT", 15)

        all_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            response = client.chat.completions.create(
                model=model,
                messages=all_messages,
                temperature=temperature,
                max_tokens=500,
                timeout=timeout,
            )
            content = response.choices[0].message.content
            logger.debug("DeepSeek response (model=%s): %s", model, content[:200])
            return content
        except Exception:
            logger.exception("DeepSeek API call failed")
            return None

    @classmethod
    def extract_address(
        cls,
        customer_reply: str,
        conversation_history: list[dict] | None = None,
        current_address: str = "",
    ) -> dict[str, Any]:
        """Parse a free-text customer reply to extract structured address fields.

        Returns a dict with keys: city, area, street, house, landmark,
        postal_code, full_address, confidence, intent, needs_followup, missing.
        """
        messages = []

        # Include conversation context
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                role = "assistant" if msg.get("sender") == "bot" else "user"
                messages.append({"role": role, "content": msg["content"]})

        # Add context about existing address
        context = f"Current known address: {current_address}\n" if current_address else ""
        messages.append({
            "role": "user",
            "content": f"{context}Customer's reply: {customer_reply}",
        })

        raw = cls.chat(ADDRESS_EXTRACTION_SYSTEM, messages, temperature=0.1)
        if not raw:
            return cls._fallback_extraction(customer_reply)

        parsed = cls._parse_json_response(raw, customer_reply)

        # Post-processing: sanitize LLM output to prevent context leakage
        parsed = cls._sanitize_extraction(parsed, customer_reply)

        return parsed

    @classmethod
    def generate_message(
        cls,
        order_context: dict,
        conversation_history: list[dict] | None = None,
        missing_fields: list[str] | None = None,
        language: str = "Roman Urdu",
        customer_last_reply: str = "",
        step: int = 1,
    ) -> str | None:
        """Generate a natural WhatsApp message for the customer.

        Args:
            order_context: Dict with customer_name, phone, items, amount, current_address.
            conversation_history: Previous messages for context.
            missing_fields: Address fields still needed.
            language: Preferred language for the message.
            customer_last_reply: What the customer just said.
            step: Current step in the confirmation flow (1=confirm, 2=landmark, 3=probe, 4=eta).
        """
        # Build history text
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-6:]:
                sender = "Bot" if msg.get("sender") == "bot" else "Customer"
                history_text += f"{sender}: {msg['content']}\n"
        if not history_text:
            history_text = "(First message — no history yet)"

        system = MESSAGE_GENERATION_SYSTEM.format(
            language=language,
            customer_name=order_context.get("customer_name", "Customer"),
            customer_phone=order_context.get("phone", ""),
            items=order_context.get("items", ""),
            amount=order_context.get("amount", ""),
            current_address=order_context.get("current_address", "Not provided"),
            missing_fields=", ".join(missing_fields or []),
            history=history_text,
            customer_last_reply=customer_last_reply or "(First message)",
            step=step,
        )

        messages = [{"role": "user", "content": "Generate the next WhatsApp message."}]
        return cls.chat(system, messages, temperature=0.5)

    # ── Internal helpers ─────────────────────────────────────────────────

    @classmethod
    def _sanitize_extraction(cls, parsed: dict, customer_reply: str) -> dict:
        """Post-process LLM extraction to prevent context leakage and garbage data.

        The LLM sometimes copies address fields from the "Current known address"
        context even though the customer didn't mention them. This strips out
        any extracted data that the customer didn't actually say.
        """
        reply_lower = customer_reply.lower().strip()
        reply_words = set(reply_lower.split())

        # If confidence is very low or intent is non-address, clear all address fields
        non_address_intents = {"greeting", "doesnt_know", "question", "unclear"}
        if parsed.get("intent") in non_address_intents:
            for key in ("city", "area", "street", "house", "landmark", "postal_code", "full_address"):
                parsed[key] = ""
            parsed["confidence"] = 0.0
            parsed["needs_followup"] = True
            return parsed

        # For address_update: verify that extracted values have some basis in the reply
        for key in ("city", "area", "street", "house", "landmark"):
            value = (parsed.get(key) or "").strip()
            if not value:
                continue
            # Check if ANY word from the extracted value appears in the customer's reply
            value_words = set(value.lower().split())
            if not (value_words & reply_words):
                logger.warning(
                    "Sanitize: stripped '%s'='%s' — not found in reply '%s'",
                    key, value, customer_reply[:80],
                )
                parsed[key] = ""

        return parsed

    @classmethod
    def _parse_json_response(cls, raw: str, original_reply: str) -> dict[str, Any]:
        """Try to extract JSON from the LLM response, handling markdown fences."""
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            logger.warning("DeepSeek returned non-JSON: %s", text[:200])

        return cls._fallback_extraction(original_reply)

    @classmethod
    def _fallback_extraction(cls, text: str) -> dict[str, Any]:
        """Minimal keyword-based extraction when LLM fails."""
        text_lower = text.lower().strip()

        # Simple intent detection
        cancel_keywords = {"cancel", "band", "reject", "nahi chahiye", "cancel kardo"}
        doesnt_know_keywords = {"nhi", "nahi", "pta", "pata", "patta", "nhi pta", "malom", "maloom"}
        confirm_keywords = {"haan", "yes", "ji", "ok", "confirm", "theek", "thik", "sahi"}
        greeting_keywords = {"salam", "hello", "hi", "hey", "assalam", "walaikum"}

        words = set(text_lower.split())

        # Check for cancel (explicit cancel phrases)
        if "cancel" in words or "band" in words:
            intent = "order_cancel"
        # Check for "doesn't know" (nhi pta, pata nahi, etc.)
        elif ("pta" in words or "pata" in words or "patta" in words) and (
            "nhi" in words or "nahi" in words or "na" in words
        ):
            intent = "doesnt_know"
        elif words & greeting_keywords and len(words) <= 5:
            intent = "greeting"
        elif words & confirm_keywords and len(words) <= 4:
            intent = "order_confirm"
        else:
            intent = "unclear"

        return {
            "city": "",
            "area": "",
            "street": "",
            "house": "",
            "landmark": "",
            "postal_code": "",
            "full_address": "",  # Never store raw text as address
            "confidence": 0.0,
            "intent": intent,
            "needs_followup": True,
            "missing": [],
        }
