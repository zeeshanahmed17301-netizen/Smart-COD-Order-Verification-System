"""Store serializers."""
from rest_framework import serializers
from .models import StoreConnection, APIKey, Webhook


class StoreConnectionSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True
    )

    class Meta:
        model = StoreConnection
        fields = [
            "id", "platform", "platform_display", "store_url",
            "access_token", "client_id", "client_secret",
            "is_active", "last_sync_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "access_token": {"write_only": True},
            "client_id": {"write_only": True},
            "client_secret": {"write_only": True},
        }

    def validate(self, attrs):
        platform = attrs.get("platform")
        if not platform and self.instance:
            platform = self.instance.platform

        store_url = attrs.get("store_url")
        if store_url is None and self.instance:
            store_url = self.instance.store_url

        access_token = attrs.get("access_token")
        if access_token is None and self.instance:
            access_token = self.instance.access_token

        if platform == "shopify":
            if not (store_url or "").strip():
                raise serializers.ValidationError(
                    {"store_url": "Shopify store URL is required."}
                )
            if "myshopify.com" not in (store_url or "").lower():
                raise serializers.ValidationError(
                    {"store_url": "Use your *.myshopify.com store domain."}
                )

            client_id = attrs.get("client_id")
            if client_id is None and self.instance:
                client_id = self.instance.client_id
            client_secret = attrs.get("client_secret")
            if client_secret is None and self.instance:
                client_secret = self.instance.client_secret

            has_client_creds = (client_id or "").strip() and (client_secret or "").strip()
            has_legacy_token = (access_token or "").strip()

            if not has_client_creds and not has_legacy_token:
                raise serializers.ValidationError(
                    {"client_id": "Provide Client ID and Client Secret from the Shopify Dev Dashboard."}
                )

        return attrs


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            "id", "key", "label",
            "is_active", "created_at", "last_used_at",
        ]
        read_only_fields = ["id", "key", "created_at", "last_used_at"]


class APIKeyCredentialSerializer(APIKeySerializer):
    secret = serializers.CharField(read_only=True)

    class Meta(APIKeySerializer.Meta):
        fields = APIKeySerializer.Meta.fields + ["secret"]


class WebhookSerializer(serializers.ModelSerializer):
    event_display = serializers.CharField(
        source="get_event_display", read_only=True
    )

    class Meta:
        model = Webhook
        fields = [
            "id", "event", "event_display", "url", "is_active",
            "secret_key", "delivery_count", "last_delivery_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "secret_key", "delivery_count",
            "last_delivery_at", "created_at", "updated_at",
        ]
