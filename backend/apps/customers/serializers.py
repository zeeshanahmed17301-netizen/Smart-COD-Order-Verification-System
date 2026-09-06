"""Serializers for customers."""
from rest_framework import serializers

from .models import Customer
from .normalization import normalize_phone


class CustomerSerializer(serializers.ModelSerializer):
    """Full customer serializer with computed fields."""

    rto_rate = serializers.FloatField(read_only=True)
    delivery_success_rate = serializers.FloatField(read_only=True)

    def validate_phone(self, value: str) -> str:
        return normalize_phone(value) or value.strip()

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        phone = attrs.get("phone")
        if not phone:
            return attrs

        merchant = getattr(self.instance, "merchant", None) or self.context["request"].user
        normalized_phone = normalize_phone(phone)
        queryset = Customer.objects.filter(
            merchant=merchant,
            normalized_phone=normalized_phone,
        )
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        if normalized_phone and queryset.exists():
            raise serializers.ValidationError(
                {"phone": "A customer with this normalized phone number already exists."}
            )
        return attrs

    class Meta:
        model = Customer
        fields = [
            "id", "name", "phone", "email", "city",
            "total_orders", "delivered_count", "rto_count",
            "cancelled_count", "ghosted_count",
            "rto_rate", "delivery_success_rate",
            "is_blacklisted", "blacklist_reason",
            "multiple_names_detected", "names_used",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_orders", "delivered_count", "rto_count",
            "cancelled_count", "ghosted_count",
            "rto_rate", "delivery_success_rate",
            "created_at", "updated_at",
        ]


class CustomerHistorySerializer(serializers.ModelSerializer):
    """Lightweight history for order detail page."""

    rto_rate = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "total_orders", "delivered_count", "rto_count", "rto_rate",
        ]

    def get_rto_rate(self, obj: Customer) -> str:
        return f"{obj.rto_rate}%"
