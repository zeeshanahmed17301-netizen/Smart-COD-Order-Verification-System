"""Admin registration for addresses."""
from django.contrib import admin
from .models import Address, CourierBranch


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["full_address", "city", "confidence_score", "status", "is_high_risk_area"]
    list_filter = ["status", "city", "is_high_risk_area"]
    search_fields = ["full_address", "city"]


@admin.register(CourierBranch)
class CourierBranchAdmin(admin.ModelAdmin):
    list_display = ["brand", "branch_name", "city_normalized", "city_raw", "is_active"]
    list_filter = ["brand", "is_active"]
    search_fields = ["branch_name", "address", "city_normalized", "city_raw"]
    list_editable = ["is_active"]

