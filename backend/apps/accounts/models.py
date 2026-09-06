"""User and Merchant Profile models for Risk-Guard."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with email-based authentication."""

    email = models.EmailField(unique=True, db_index=True)
    is_onboarded = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email


class MerchantProfile(models.Model):
    """Business profile created during onboarding."""

    CATEGORY_CHOICES = [
        ("fashion", "Fashion & Apparel"),
        ("electronics", "Electronics"),
        ("beauty", "Beauty & Health"),
        ("home", "Home & Living"),
        ("grocery", "Grocery"),
        ("other", "Other"),
    ]

    LANGUAGE_CHOICES = [
        ("urdu", "Urdu"),
        ("english", "English"),
        ("mixed", "Mixed"),
    ]

    AUTO_SEND_CHOICES = [
        ("immediately", "Immediately"),
        ("1min", "After 1 min"),
        ("5min", "After 5 min"),
    ]

    AUTO_CANCEL_CHOICES = [
        ("off", "Off"),
        ("30min", "30 min"),
        ("1hour", "1 hour"),
        ("2hours", "2 hours"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="merchant_profile"
    )
    store_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, blank=True
    )
    country = models.CharField(max_length=100, default="Pakistan")
    whatsapp_number = models.CharField(max_length=20, blank=True)
    whatsapp_api_key = models.CharField(max_length=500, blank=True)
    language = models.CharField(
        max_length=20, choices=LANGUAGE_CHOICES, default="urdu"
    )
    auto_send = models.CharField(
        max_length=20, choices=AUTO_SEND_CHOICES, default="immediately"
    )
    auto_cancel = models.CharField(
        max_length=20, choices=AUTO_CANCEL_CHOICES, default="off"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.store_name} ({self.user.email})"
