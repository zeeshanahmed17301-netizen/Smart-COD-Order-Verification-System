"""Analytics views — dashboard stats, trends, and heatmaps."""
from datetime import timedelta
from collections import defaultdict

from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.source_facts import build_canonical_order_facts

RTO_OUTCOME_VALUES = {
    "rto",
    "wrong_address",
    "refused",
    "not_my_order",
    "prank",
    "other",
}


def _orders_with_canonical_context(merchant):
    return Order.objects.filter(merchant=merchant).select_related(
        "customer",
        "address",
        "source_snapshot",
    )


def _canonical_facts(order):
    cached = getattr(order, "_canonical_facts_cache", None)
    if cached is None:
        cached = build_canonical_order_facts(order, getattr(order, "source_snapshot", None)) or {}
        setattr(order, "_canonical_facts_cache", cached)
    return cached


def _canonical_city(order):
    facts = _canonical_facts(order)
    addresses = facts.get("addresses") or {}
    return addresses.get("city") or "Unknown"


def _parse_days(value, default: int = 7) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        days = default
    return max(1, min(days, 90))


def _actual_rto_filter() -> Q:
    return Q(status="rto")


def _actual_rto_count(orders) -> int:
    return orders.filter(_actual_rto_filter()).distinct().count()


def _build_city_rollup(orders, limit: int = 10):
    city_stats = defaultdict(lambda: {"count": 0, "risk_total": 0.0, "fraud_total": 0.0, "rto_count": 0})

    for order in orders:
        city = _canonical_city(order)
        stats = city_stats[city]
        stats["count"] += 1
        stats["risk_total"] += float(order.risk_score or 0)
        stats["fraud_total"] += float(order.fraud_score or 0)
        if order.status == "rto":
            stats["rto_count"] += 1

    ranked = sorted(
        city_stats.items(),
        key=lambda item: (-item[1]["count"], item[0]),
    )[:limit]

    rollup = []
    for city, stats in ranked:
        count = stats["count"]
        rollup.append(
            {
                "city": city,
                "count": count,
                "order_count": count,
                "avg_risk": round((stats["risk_total"] / count), 1) if count else 0,
                "avg_fraud": round((stats["fraud_total"] / count), 1) if count else 0,
                "rto_count": stats["rto_count"],
                "rto_rate": round((stats["rto_count"] / count) * 100, 1) if count else 0,
            }
        )
    return rollup


class DashboardStatsView(APIView):
    """
    Dashboard summary stats matching frontend mockStats shape:
    { rtoPercentage, fraudScore, savings, totalOrders, pendingVerification, codOrdersToday }
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        merchant = request.user
        days = _parse_days(request.query_params.get("days"), default=7)
        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)
        all_orders = Order.objects.filter(merchant=merchant)
        period_orders = all_orders.filter(created_at__date__gte=start_date, created_at__date__lte=today)

        total_orders = period_orders.count()
        rto_orders = _actual_rto_count(period_orders)
        rto_percentage = (
            round((rto_orders / total_orders) * 100, 1) if total_orders > 0 else 0
        )

        averages = period_orders.aggregate(
            avg_fraud=Avg("fraud_score"),
            avg_risk=Avg("risk_score"),
        )
        pending = period_orders.filter(status="pending").count()
        high_risk = period_orders.filter(risk_level__in=("high", "critical")).count()
        high_risk_pending = period_orders.filter(
            status="pending",
            risk_level__in=("high", "critical"),
        ).count()
        cod_today = all_orders.filter(
            payment_method="cod", created_at__date=today
        ).count()

        # Estimated savings = value of orders the engine told you to cancel that
        # you actually stopped. The old version filtered status="rejected", a
        # status the app never writes (cancel/reject both set status="cancelled"),
        # so it was permanently 0. Attribute savings to engine-driven cancels:
        # recommended_action == "cancel_order" AND the order was actually stopped.
        saved_orders = period_orders.filter(
            status__in=("cancelled", "rejected"),
            recommended_action="cancel_order",
        )
        saved_amount = saved_orders.aggregate(total=Sum("amount"))["total"] or 0
        saved_count = saved_orders.count()

        return Response({
            "rtoPercentage": rto_percentage,
            "rtoCount": rto_orders,
            "fraudScore": round(averages["avg_fraud"] or 0, 1),
            "avgRiskScore": round(averages["avg_risk"] or 0, 1),
            "savings": float(saved_amount),
            "savingsCount": saved_count,
            "totalOrders": total_orders,
            "pendingVerification": pending,
            "highRiskOrders": high_risk,
            "highRiskPending": high_risk_pending,
            "codOrdersToday": cod_today,
            "periodDays": days,
            "periodStart": start_date.strftime("%Y-%m-%d"),
            "periodEnd": today.strftime("%Y-%m-%d"),
        })


class RTOTrendView(APIView):
    """7/30/90 day RTO trend data for charts."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        days = _parse_days(request.query_params.get("days"), default=7)
        merchant = request.user
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)

        trend_data = []
        current = start_date
        while current <= end_date:
            day_orders = Order.objects.filter(
                merchant=merchant, created_at__date=current
            )
            total = day_orders.count()
            rto = _actual_rto_count(day_orders)
            rto_pct = round((rto / total) * 100, 1) if total > 0 else 0

            trend_data.append({
                "date": current.strftime("%Y-%m-%d"),
                "name": current.strftime("%a"),
                "rto": rto_pct,
                "total_orders": total,
                "rto_count": rto,
            })
            current += timedelta(days=1)

        return Response(trend_data)


class AnalyticsOverviewView(APIView):
    """Comprehensive analytics overview."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        merchant = request.user
        orders = _orders_with_canonical_context(merchant)

        # Status breakdown
        status_breakdown = dict(
            orders.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        # Risk level breakdown
        risk_breakdown = dict(
            orders.values_list("risk_level")
            .annotate(count=Count("id"))
            .values_list("risk_level", "count")
        )

        # Top cities by order count
        top_cities = _build_city_rollup(orders, limit=10)

        # Average scores
        averages = orders.aggregate(
            avg_risk=Avg("risk_score"),
            avg_fraud=Avg("fraud_score"),
            avg_address=Avg("address_score"),
        )

        return Response({
            "status_breakdown": status_breakdown,
            "risk_breakdown": risk_breakdown,
            "top_cities": top_cities,
            "averages": {
                "risk_score": round(averages["avg_risk"] or 0, 1),
                "fraud_score": round(averages["avg_fraud"] or 0, 1),
                "address_score": round(averages["avg_address"] or 0, 1),
            },
            "total_orders": orders.count(),
        })


class RiskHeatmapView(APIView):
    """Risk heatmap data by city/area."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        merchant = request.user
        heatmap = sorted(
            _build_city_rollup(_orders_with_canonical_context(merchant), limit=20),
            key=lambda entry: (-entry["avg_risk"], -entry["order_count"], entry["city"]),
        )[:5]
        return Response(heatmap)


class FraudTrendsView(APIView):
    """Fraud score trends over time."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        days = min(days, 90)
        merchant = request.user
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        trend_data = []
        current = start_date
        while current <= end_date:
            day_stats = Order.objects.filter(
                merchant=merchant, created_at__date=current
            ).aggregate(
                avg_fraud=Avg("fraud_score"),
                avg_risk=Avg("risk_score"),
                count=Count("id"),
            )
            trend_data.append({
                "date": current.strftime("%Y-%m-%d"),
                "avg_fraud": round(day_stats["avg_fraud"] or 0, 1),
                "avg_risk": round(day_stats["avg_risk"] or 0, 1),
                "order_count": day_stats["count"],
            })
            current += timedelta(days=1)

        return Response(trend_data)
