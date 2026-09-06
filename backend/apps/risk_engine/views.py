"""Risk engine views."""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.stores.shopify_sync import refresh_shopify_order_bootstrap

from .serializers import ScoreOrderSerializer
from .services import RiskScoringEngine


class ScoreOrderView(APIView):
    """Score or re-score a specific order on demand."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ScoreOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data["order_id"]

        try:
            order = Order.objects.select_related(
                "customer", "address", "source_snapshot", "enrichment"
            ).prefetch_related("items").get(id=order_id, merchant=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            refresh_shopify_order_bootstrap(order)
        except Exception:
            pass

        result = RiskScoringEngine.score_and_save(order)
        return Response(
            {
                "order_id": order.order_id,
                "address_score": result.address_score,
                "risk_score": result.risk_score,
                "fraud_score": result.fraud_score,
                "rto_probability": result.rto_probability,
                "rto_probability_score": result.rto_probability_score,
                "risk_level": result.risk_level,
                "recommended_action": result.recommended_action,
                "factors": result.factors,
                "score_breakdown": result.score_breakdown,
                "decision_summary": result.decision_summary,
                "information_quality": result.information_quality,
            }
        )