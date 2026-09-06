"""Views for customers."""
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """CRUD for customers scoped to the authenticated merchant."""

    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["city", "is_blacklisted"]
    search_fields = ["name", "phone", "normalized_phone", "email"]
    ordering_fields = ["created_at", "total_orders", "rto_count"]

    def get_queryset(self):
        return Customer.objects.filter(merchant=self.request.user)

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user)
