"""Admin registration for accounts models."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, MerchantProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "first_name", "is_onboarded", "is_active"]
    list_filter = ["is_onboarded", "is_active", "is_staff"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-date_joined"]


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = ["store_name", "user", "category", "country", "created_at"]
    list_filter = ["category", "country"]
    search_fields = ["store_name", "user__email"]
