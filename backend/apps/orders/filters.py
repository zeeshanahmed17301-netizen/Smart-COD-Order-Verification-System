"""Filter sets for orders."""
import django_filters
from django.db.models import Q

from .models import Order


class OrderFilterSet(django_filters.FilterSet):
    """Advanced filters for order list."""

    status = django_filters.ChoiceFilter(choices=Order.STATUS_CHOICES)
    risk_level = django_filters.ChoiceFilter(choices=Order.RISK_LEVEL_CHOICES)
    city = django_filters.CharFilter(method="filter_city")
    date_from = django_filters.DateFilter(
        field_name="created_at", lookup_expr="gte"
    )
    date_to = django_filters.DateFilter(
        field_name="created_at", lookup_expr="lte"
    )
    min_amount = django_filters.NumberFilter(
        field_name="amount", lookup_expr="gte"
    )
    max_amount = django_filters.NumberFilter(
        field_name="amount", lookup_expr="lte"
    )
    chat_status = django_filters.ChoiceFilter(choices=Order.CHAT_STATUS_CHOICES)
    recommended_action = django_filters.ChoiceFilter(
        choices=Order.RECOMMENDED_ACTION_CHOICES
    )
    high_risk = django_filters.BooleanFilter(method="filter_high_risk")
    action_needed = django_filters.BooleanFilter(method="filter_action_needed")
    awaiting_reply = django_filters.BooleanFilter(method="filter_awaiting_reply")

    class Meta:
        model = Order
        fields = [
            "status", "risk_level", "city", "chat_status", "recommended_action",
            "date_from", "date_to", "min_amount", "max_amount",
            "high_risk", "action_needed", "awaiting_reply",
        ]

    def filter_high_risk(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(risk_level__in=["high", "critical"])

    def filter_action_needed(self, queryset, name, value):
        """Orders the recommender flags for human attention — everything except
        a clean 'ship_order'."""
        if not value:
            return queryset
        return queryset.exclude(recommended_action="ship_order")

    def filter_awaiting_reply(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(conversation__status="awaiting_reply")

    def filter_city(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(customer__city__icontains=value)
            | Q(address__city__icontains=value)
            | Q(source_snapshot__raw_order_payload__shipping_address__city__icontains=value)
            | Q(source_snapshot__raw_order_payload__billing_address__city__icontains=value)
        )
