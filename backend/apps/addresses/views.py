"""Views for addresses."""
from rest_framework import viewsets, permissions
from .models import Address
from .serializers import AddressSerializer


class AddressViewSet(viewsets.ModelViewSet):
    """CRUD for addresses scoped to the merchant's customers."""

    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(
            customer__merchant=self.request.user
        ).select_related("customer")
