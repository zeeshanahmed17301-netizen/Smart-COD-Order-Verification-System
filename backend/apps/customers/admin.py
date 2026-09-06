"""Admin registration for customers."""
from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "city", "total_orders", "rto_count", "is_blacklisted"]
    list_filter = ["city", "is_blacklisted"]
    search_fields = ["name", "phone", "email"]
    readonly_fields = ["total_orders", "delivered_count", "rto_count", "cancelled_count"]
