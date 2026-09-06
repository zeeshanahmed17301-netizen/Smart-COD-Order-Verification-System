"""Serializers for addresses."""
from rest_framework import serializers
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    """Full address serializer."""

    class Meta:
        model = Address
        fields = [
            "id", "customer", "full_address", "city", "province", "postal_code",
            "suggested_address", "confidence_score", "status",
            "latitude", "longitude", "map_preview_url",
            "area_rto_rate", "is_high_risk_area",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AddressVerificationSerializer(serializers.ModelSerializer):
    """Address verification data for order detail page."""

    entered_address = serializers.CharField(source="full_address")

    class Meta:
        model = Address
        fields = [
            "entered_address", "suggested_address",
            "confidence_score", "status", "map_preview_url",
        ]
