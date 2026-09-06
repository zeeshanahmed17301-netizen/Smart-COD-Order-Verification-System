"""Shared permission classes for Risk-Guard API."""
from rest_framework.permissions import BasePermission


class IsStoreOwner(BasePermission):
    """Allow access only if the request user owns the related store/merchant."""

    def has_object_permission(self, request, view, obj) -> bool:
        # Works for any model with a `merchant` FK pointing to the user
        if hasattr(obj, "merchant"):
            return obj.merchant == request.user
        if hasattr(obj, "store") and hasattr(obj.store, "merchant"):
            return obj.store.merchant == request.user
        return False
