"""Risk engine serializers."""

from rest_framework import serializers


class ScoreOrderSerializer(serializers.Serializer):
    """Input for on-demand order scoring."""

    order_id = serializers.IntegerField()