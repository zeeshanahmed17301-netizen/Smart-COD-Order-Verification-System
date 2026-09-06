"""Serializers for orders — list, detail, and create."""
from rest_framework import serializers

from apps.customers.serializers import CustomerHistorySerializer
from apps.addresses.serializers import AddressVerificationSerializer
from apps.chatbot.serializers import MessageSerializer, WhatsAppInteractionSerializer
from apps.risk_engine.services import (
    build_decision_summary,
    build_score_breakdown,
    InformationQualityService,
    ScoreCalibrationService,
)
from .models import Order, OrderItem, RiskFactor
from .source_facts import build_canonical_order_facts
from .source_ip import resolve_order_ip


def _coalesce(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _build_person_name(data: dict | None) -> str | None:
    if not data:
        return None
    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    return name or None


def _build_shopify_address(data: dict | None) -> dict | None:
    if not data:
        return None

    lines = [
        data.get("address1"),
        data.get("address2"),
        data.get("city"),
        data.get("province"),
        data.get("country"),
        data.get("zip"),
    ]
    formatted = ", ".join(str(line).strip() for line in lines if line)

    return {
        "name": _build_person_name(data),
        "phone": data.get("phone"),
        "company": data.get("company"),
        "address1": data.get("address1"),
        "address2": data.get("address2"),
        "city": data.get("city"),
        "province": data.get("province"),
        "country": data.get("country"),
        "zip": data.get("zip"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "formatted": formatted or None,
    }


def _build_shopify_details(snapshot) -> dict:
    raw = snapshot.raw_order_payload or {}
    customer = raw.get("customer") or {}
    shipping_address = _build_shopify_address(raw.get("shipping_address") or {})
    billing_address = _build_shopify_address(raw.get("billing_address") or {})
    shipping_lines = raw.get("shipping_lines") or []
    note_attributes = raw.get("note_attributes") or []
    order_ip = resolve_order_ip(
        client_ip=snapshot.client_ip,
        browser_ip=snapshot.browser_ip,
        raw_order_payload=raw,
    )

    return {
        "order_identity": {
            "shopify_order_gid": _coalesce(snapshot.shopify_order_gid),
            "shopify_legacy_order_id": _coalesce(snapshot.shopify_legacy_order_id),
            "name": _coalesce(raw.get("name")),
            "order_number": _coalesce(raw.get("order_number")),
            "confirmation_number": _coalesce(raw.get("confirmation_number")),
            "app_id": _coalesce(raw.get("app_id")),
            "confirmed": raw.get("confirmed"),
            "source_name": _coalesce(snapshot.source_name, raw.get("source_name")),
            "source_identifier": _coalesce(snapshot.source_identifier, raw.get("source_identifier")),
            "registered_source_url": _coalesce(snapshot.registered_source_url),
            "created_at": _coalesce(raw.get("created_at")),
            "updated_at": _coalesce(raw.get("updated_at")),
            "processed_at": _coalesce(raw.get("processed_at")),
            "cancelled_at": _coalesce(raw.get("cancelled_at")),
            "closed_at": _coalesce(raw.get("closed_at")),
            "cancel_reason": _coalesce(raw.get("cancel_reason")),
            "tags": _coalesce(raw.get("tags")),
            "note": _coalesce(raw.get("note")),
        },
        "payment": {
            "financial_status": _coalesce(snapshot.financial_status, raw.get("financial_status")),
            "fulfillment_status": _coalesce(snapshot.fulfillment_status, raw.get("fulfillment_status")),
            "payment_gateway_names": _coalesce(raw.get("payment_gateway_names")),
            "currency": _coalesce(raw.get("currency")),
            "subtotal_price": _coalesce(raw.get("subtotal_price"), raw.get("current_subtotal_price")),
            "subtotal_price_set": _coalesce(raw.get("subtotal_price_set"), raw.get("current_subtotal_price_set")),
            "total_discounts": _coalesce(raw.get("total_discounts"), raw.get("current_total_discounts")),
            "total_discounts_set": _coalesce(raw.get("total_discounts_set"), raw.get("current_total_discounts_set")),
            "total_tax": _coalesce(raw.get("total_tax")),
            "total_tax_set": _coalesce(raw.get("total_tax_set")),
            "total_price": _coalesce(raw.get("total_price"), raw.get("current_total_price")),
            "total_price_set": _coalesce(raw.get("total_price_set"), raw.get("current_total_price_set")),
            "total_outstanding": _coalesce(raw.get("total_outstanding")),
            "total_outstanding_set": _coalesce(raw.get("total_outstanding_set")),
            "total_weight": _coalesce(raw.get("total_weight")),
            "total_shipping_price_set": _coalesce(raw.get("total_shipping_price_set"), raw.get("current_total_shipping_price_set")),
            "current_total_additional_fees_set": _coalesce(raw.get("current_total_additional_fees_set")),
            "shipping_lines": shipping_lines,
        },
        "customer": {
            "name": _coalesce(_build_person_name(customer), _build_person_name(raw.get("shipping_address") or {})),
            "email": _coalesce(raw.get("contact_email"), raw.get("email"), customer.get("email")),
            "contact_email": _coalesce(raw.get("contact_email")),
            "phone": _coalesce(customer.get("phone"), raw.get("phone"), (raw.get("shipping_address") or {}).get("phone")),
            "buyer_accepts_marketing": raw.get("buyer_accepts_marketing"),
            "customer_id": _coalesce(customer.get("id")),
            "orders_count": _coalesce(customer.get("orders_count")),
            "verified_email": customer.get("verified_email"),
            "state": _coalesce(customer.get("state")),
        },
        "addresses": {
            "billing_matches_shipping": snapshot.billing_matches_shipping,
            "shipping_address": shipping_address,
            "billing_address": billing_address,
        },
        "additional_details": {
            "note_attributes": note_attributes,
            "landing_site": _coalesce(raw.get("landing_site")),
            "landing_site_ref": _coalesce(raw.get("landing_site_ref")),
            "referring_site": _coalesce(raw.get("referring_site")),
            "order_ip": order_ip["value"],
            "order_ip_source": order_ip["source"],
            "user_agent": _coalesce((raw.get("client_details") or {}).get("user_agent"), snapshot.user_agent),
            "session_hash": _coalesce((raw.get("client_details") or {}).get("session_hash"), snapshot.session_hash),
            "customer_journey_ready": snapshot.customer_journey_ready,
            "customer_order_index": snapshot.customer_order_index,
            "days_to_conversion": snapshot.days_to_conversion,
        },
        "risk": {
            "shopify_risk_recommendation": _coalesce(snapshot.shopify_risk_recommendation),
            "shopify_risk_level": _coalesce(snapshot.shopify_risk_level),
            "shopify_risk_payload": snapshot.shopify_risk_payload,
        },
    }


def _display_order_number(order: Order) -> str:
    snapshot = getattr(order, "source_snapshot", None)
    raw = getattr(snapshot, "raw_order_payload", None) or {}
    return str(
        _coalesce(
            raw.get("name"),
            f"#{raw.get('order_number')}" if raw.get("order_number") else None,
            order.order_id,
        )
    )


class OrderItemSerializer(serializers.ModelSerializer):
    """Order line item."""

    total = serializers.FloatField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "name", "price", "qty", "total", "sku", "category"]
        read_only_fields = ["id"]


class RiskFactorSerializer(serializers.ModelSerializer):
    """Individual risk factor."""

    class Meta:
        model = RiskFactor
        fields = ["id", "name", "score", "level", "description"]
        read_only_fields = ["id"]


class OrderListSerializer(serializers.ModelSerializer):
    """Flat order list matching frontend mockOrders[] shape."""

    customer_name = serializers.SerializerMethodField()
    display_order_number = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    customer_city = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    fraud_probability = serializers.SerializerMethodField()
    fraud_confidence_interval = serializers.SerializerMethodField()
    rto_probability_percent = serializers.SerializerMethodField()
    rto_confidence_interval = serializers.SerializerMethodField()
    chat_status = serializers.SerializerMethodField()
    courier_coverage_score = serializers.SerializerMethodField()
    courier_match_confidence = serializers.SerializerMethodField()
    signals = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_id", "display_order_number", "customer_name", "customer_phone", "amount",
            "status", "risk_score", "risk_level", "created_at", "customer_city",
            "items", "chat_status", "address_score", "fraud_score",
            "fraud_probability", "fraud_confidence_interval",
            "rto_probability", "rto_probability_score", "rto_probability_percent",
            "rto_confidence_interval", "recommended_action",
            "recommended_action_label", "courier_reachable",
            "courier_coverage_score", "courier_match_confidence", "signals",
        ]

    recommended_action_label = serializers.CharField(
        source="get_recommended_action_display",
        read_only=True,
    )

    def _canonical_facts(self, obj: Order) -> dict:
        cached = getattr(obj, "_canonical_facts_cache", None)
        if cached is None:
            cached = build_canonical_order_facts(obj, getattr(obj, "source_snapshot", None)) or {}
            setattr(obj, "_canonical_facts_cache", cached)
        return cached

    @staticmethod
    def get_display_order_number(obj: Order) -> str:
        return _display_order_number(obj)

    def get_customer_name(self, obj: Order) -> str | None:
        canonical_customer = self._canonical_facts(obj).get("customer") or {}
        return canonical_customer.get("name") or obj.customer.name

    def get_customer_phone(self, obj: Order) -> str | None:
        canonical_customer = self._canonical_facts(obj).get("customer") or {}
        return canonical_customer.get("phone") or obj.customer.phone

    def get_customer_city(self, obj: Order) -> str | None:
        canonical_addresses = self._canonical_facts(obj).get("addresses") or {}
        return canonical_addresses.get("city") or obj.customer.city

    @staticmethod
    def get_courier_reachable(obj: Order) -> bool | None:
        enrichment = getattr(obj, "enrichment", None)
        if enrichment:
            return enrichment.courier_reachable
        return None

    courier_reachable = serializers.SerializerMethodField()

    @staticmethod
    def get_courier_coverage_score(obj: Order) -> float | None:
        enrichment = getattr(obj, "enrichment", None)
        if enrichment:
            return float(enrichment.courier_coverage_score)
        return None

    @staticmethod
    def get_courier_match_confidence(obj: Order) -> str:
        enrichment = getattr(obj, "enrichment", None)
        if enrichment:
            return enrichment.courier_match_confidence or ""
        return ""

    @staticmethod
    def get_signals(obj: Order) -> dict:
        """Actionable notifiers derived from enrichment so the table can flag
        orders that need attention (duplicate phone, weak address) without the
        operator opening each order."""
        enrichment = getattr(obj, "enrichment", None)
        repeat_phone = getattr(enrichment, "repeat_phone_orders_30d", 0) or 0
        repeat_address = getattr(enrichment, "repeat_address_orders_30d", 0) or 0
        serviceable = getattr(enrichment, "serviceable", None)
        verdict = (getattr(enrichment, "address_validation_verdict", "") or "").upper()

        if serviceable is False or verdict == "UNDELIVERABLE":
            address_quality = "undeliverable"
        elif verdict == "DELIVERABLE":
            address_quality = "verified"
        elif verdict == "UNCONFIRMED":
            address_quality = "unconfirmed"
        else:
            address_quality = "unknown"

        return {
            # >1 because the current order itself counts toward the window.
            "duplicate_phone": repeat_phone > 1,
            "repeat_phone_orders_30d": repeat_phone,
            "duplicate_address": repeat_address > 1,
            "repeat_address_orders_30d": repeat_address,
            "address_quality": address_quality,
            "address_serviceable": serviceable,
        }

    @staticmethod
    def get_chat_status(obj: Order) -> str:
        conversation = getattr(obj, "conversation", None)
        if conversation and conversation.status:
            return conversation.status
        return obj.chat_status

    def get_items(self, obj: Order) -> list[str]:
        return list(obj.items.values_list("name", flat=True))

    def _calibration(self, obj: Order) -> dict:
        cached = getattr(obj, "_list_calibration_cache", None)
        if cached is None:
            version = obj.score_calibration_version or ScoreCalibrationService.get_active_version()
            cached = {
                "fraud": ScoreCalibrationService.calibrate(
                    target="fraud",
                    score=obj.fraud_score,
                    version=version,
                ),
                "rto": ScoreCalibrationService.calibrate(
                    target="rto",
                    score=obj.rto_probability_score,
                    version=version,
                ),
            }
            setattr(obj, "_list_calibration_cache", cached)
        return cached

    def get_fraud_probability(self, obj: Order) -> float:
        return self._calibration(obj)["fraud"].probability

    def get_fraud_confidence_interval(self, obj: Order) -> dict:
        calibration = self._calibration(obj)["fraud"]
        return {
            "lower": calibration.confidence_low,
            "upper": calibration.confidence_high,
        }

    def get_rto_probability_percent(self, obj: Order) -> float:
        return self._calibration(obj)["rto"].probability

    def get_rto_confidence_interval(self, obj: Order) -> dict:
        calibration = self._calibration(obj)["rto"]
        return {
            "lower": calibration.confidence_low,
            "upper": calibration.confidence_high,
        }


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Full order detail matching frontend mockOrderDetail shape:
    - customer (name, phone, email, address, city, history)
    - order (amount, date, items[], paymentMethod)
    - riskAnalysis (totalScore, factors[], recommendation)
    - addressVerification
    """

    customer = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    risk_factors = RiskFactorSerializer(many=True, read_only=True)
    chat_log = serializers.SerializerMethodField()
    whatsapp_interaction = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()
    risk_analysis = serializers.SerializerMethodField()
    address_verification = serializers.SerializerMethodField()
    source_snapshot = serializers.SerializerMethodField()
    canonical_facts = serializers.SerializerMethodField()
    enrichment = serializers.SerializerMethodField()
    conversation_status = serializers.SerializerMethodField()
    score_breakdown = serializers.SerializerMethodField()
    decision_summary = serializers.SerializerMethodField()
    information_quality = serializers.SerializerMethodField()
    recommended_action_label = serializers.CharField(
        source="get_recommended_action_display",
        read_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id", "order_id", "display_order_number", "status", "amount", "payment_method",
            "created_at", "updated_at", "risk_score", "fraud_score",
            "risk_level", "address_score", "rto_probability",
            "rto_probability_score",
            "recommended_action", "recommended_action_label", "chat_status", "customer",
            "address", "items", "risk_factors", "chat_log",
            "whatsapp_interaction", "order", "risk_analysis",
            "address_verification", "source_snapshot", "canonical_facts", "enrichment",
            "conversation_status",
            "score_breakdown", "decision_summary", "information_quality",
        ]

    display_order_number = serializers.SerializerMethodField()

    @staticmethod
    def get_display_order_number(obj: Order) -> str:
        return _display_order_number(obj)

    def get_customer(self, obj: Order) -> dict:
        customer = obj.customer
        return {
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "address": obj.address.full_address if obj.address else "",
            "city": customer.city,
            "total_orders": customer.total_orders,
            "delivered_count": customer.delivered_count,
            "rto_count": customer.rto_count,
            "history": CustomerHistorySerializer(customer).data,
        }

    def get_address(self, obj: Order) -> dict | None:
        if not obj.address:
            return None
        return {
            "full_address": obj.address.full_address,
            "city": obj.address.city,
            "suggested_address": obj.address.suggested_address,
            "confidence_score": obj.address.confidence_score,
            "status": obj.address.status,
            "map_preview_url": obj.address.map_preview_url,
        }

    def get_order(self, obj: Order) -> dict:
        return {
            "amount": float(obj.amount),
            "date": obj.created_at.strftime("%Y-%m-%d %H:%M"),
            "items": OrderItemSerializer(obj.items.all(), many=True).data,
            "paymentMethod": obj.get_payment_method_display(),
        }

    def get_risk_analysis(self, obj: Order) -> dict:
        return {
            "totalScore": obj.risk_score,
            "factors": RiskFactorSerializer(
                obj.risk_factors.all(), many=True
            ).data,
            "recommendation": obj.get_recommended_action_display(),
        }

    def get_chat_log(self, obj: Order) -> list[dict]:
        conversation = getattr(obj, "conversation", None)
        if not conversation:
            return []
        return MessageSerializer(conversation.messages.all(), many=True).data

    def get_conversation_status(self, obj: Order) -> dict | None:
        conversation = getattr(obj, "conversation", None)
        if not conversation:
            return None
        return {
            "id": conversation.id,
            "status": conversation.status,
            "purpose": conversation.purpose,
            "collected_data": conversation.collected_data,
            "missing_fields": conversation.missing_fields,
            "turn_count": conversation.turn_count,
            "last_message_at": conversation.last_message_at,
            "started_at": conversation.started_at,
            "completed_at": conversation.completed_at,
        }

    def get_whatsapp_interaction(self, obj: Order) -> dict | None:
        interaction = getattr(obj, "whatsapp_interaction", None)
        if not interaction:
            return None
        return WhatsAppInteractionSerializer(interaction).data

    def get_address_verification(self, obj: Order) -> dict | None:
        if not obj.address:
            return None
        return AddressVerificationSerializer(obj.address).data

    def get_source_snapshot(self, obj: Order) -> dict | None:
        snapshot = getattr(obj, "source_snapshot", None)
        if not snapshot:
            return None
        order_ip = resolve_order_ip(
            client_ip=snapshot.client_ip,
            browser_ip=snapshot.browser_ip,
            raw_order_payload=snapshot.raw_order_payload,
        )
        return {
            "shopify_order_gid": snapshot.shopify_order_gid,
            "shopify_legacy_order_id": snapshot.shopify_legacy_order_id,
            "order_ip": order_ip["value"],
            "order_ip_source": order_ip["source"],
            "user_agent": snapshot.user_agent,
            "session_hash": snapshot.session_hash,
            "source_name": snapshot.source_name,
            "source_identifier": snapshot.source_identifier,
            "registered_source_url": snapshot.registered_source_url,
            "financial_status": snapshot.financial_status,
            "fulfillment_status": snapshot.fulfillment_status,
            "billing_matches_shipping": snapshot.billing_matches_shipping,
            "customer_journey_ready": snapshot.customer_journey_ready,
            "customer_order_index": snapshot.customer_order_index,
            "days_to_conversion": snapshot.days_to_conversion,
            "shopify_risk_recommendation": snapshot.shopify_risk_recommendation,
            "shopify_risk_level": snapshot.shopify_risk_level,
            "shopify_risk_payload": snapshot.shopify_risk_payload,
            "raw_order_payload": snapshot.raw_order_payload,
            "shopify_details": _build_shopify_details(snapshot),
            "imported_at": snapshot.imported_at,
            "updated_at": snapshot.updated_at,
        }

    def get_canonical_facts(self, obj: Order) -> dict | None:
        snapshot = getattr(obj, "source_snapshot", None)
        return build_canonical_order_facts(obj, snapshot)

    def get_enrichment(self, obj: Order) -> dict | None:
        enrichment = getattr(obj, "enrichment", None)
        if not enrichment:
            return None
        return {
            "address_provider": enrichment.address_provider,
            "address_validation_status": enrichment.address_validation_status,
            "normalized_address": enrichment.normalized_address,
            "address_confidence": enrichment.address_confidence,
            "address_precision": enrichment.address_precision,
            "geocode_precision": enrichment.geocode_precision,
            "address_validation_verdict": enrichment.address_validation_verdict,
            "address_complete": enrichment.address_complete,
            "address_has_unconfirmed_components": enrichment.address_has_unconfirmed_components,
            "address_has_inferred_components": enrichment.address_has_inferred_components,
            "address_has_replaced_components": enrichment.address_has_replaced_components,
            "validation_granularity": enrichment.validation_granularity,
            "correction_delta_count": enrichment.correction_delta_count,
            "serviceable": enrichment.serviceable,
            "serviceability_reason": enrichment.serviceability_reason,
            "ip_provider": enrichment.ip_provider,
            "ip_risk_score": enrichment.ip_risk_score,
            "ip_country": enrichment.ip_country,
            "ip_region": enrichment.ip_region,
            "ip_city": enrichment.ip_city,
            "is_anonymous": enrichment.is_anonymous,
            "is_anonymous_vpn": enrichment.is_anonymous_vpn,
            "is_public_proxy": enrichment.is_public_proxy,
            "is_residential_proxy": enrichment.is_residential_proxy,
            "is_tor_exit_node": enrichment.is_tor_exit_node,
            "is_hosting_provider": enrichment.is_hosting_provider,
            "ip_geo_matches_shipping_city": enrichment.ip_geo_matches_shipping_city,
            "ip_geo_matches_shipping_country": enrichment.ip_geo_matches_shipping_country,
            "repeat_ip_orders_7d": enrichment.repeat_ip_orders_7d,
            "repeat_ip_customers_30d": enrichment.repeat_ip_customers_30d,
            "repeat_phone_orders_30d": enrichment.repeat_phone_orders_30d,
            "repeat_address_orders_30d": enrichment.repeat_address_orders_30d,
            "source_rto_rate": enrichment.source_rto_rate,
            "area_rto_rate": enrichment.area_rto_rate,
            "customer_rto_rate": enrichment.customer_rto_rate,
            "category_rto_rate": enrichment.category_rto_rate,
            "contactability_score": enrichment.contactability_score,
            "courier_reachable": enrichment.courier_reachable,
            "courier_reachable_count": enrichment.courier_reachable_count,
            "courier_coverage_score": enrichment.courier_coverage_score,
            "courier_match_confidence": enrichment.courier_match_confidence,
            "enrichment_status": enrichment.enrichment_status,
            "failure_reason": enrichment.failure_reason,
            "enriched_at": enrichment.enriched_at,
            "created_at": enrichment.created_at,
            "updated_at": enrichment.updated_at,
        }

    def get_score_breakdown(self, obj: Order) -> dict | None:
        enrichment = getattr(obj, "enrichment", None)
        if not enrichment:
            return None
        return build_score_breakdown(order=obj, enrichment=enrichment)

    def get_information_quality(self, obj: Order) -> dict | None:
        enrichment = getattr(obj, "enrichment", None)
        if not enrichment:
            return None
        snapshot = getattr(obj, "source_snapshot", None)
        canonical_facts = build_canonical_order_facts(obj, snapshot)
        return InformationQualityService.score(obj, enrichment, snapshot, canonical_facts)

    def get_decision_summary(self, obj: Order) -> dict:
        information_quality = self.get_information_quality(obj) or {
            "coverage_label": "weak",
            "warnings": [],
        }
        return build_decision_summary(
            risk_level=obj.risk_level,
            recommended_action=obj.recommended_action,
            factors=RiskFactorSerializer(obj.risk_factors.all(), many=True).data,
            information_quality=information_quality,
            order=obj,
        )


class OrderCreateSerializer(serializers.ModelSerializer):
    """Create order with nested items."""

    items = OrderItemSerializer(many=True, required=False)

    class Meta:
        model = Order
        fields = [
            "order_id", "customer", "address", "amount",
            "payment_method", "source", "campaign", "items",
        ]

    def create(self, validated_data: dict) -> Order:
        items_data = validated_data.pop("items", [])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order
