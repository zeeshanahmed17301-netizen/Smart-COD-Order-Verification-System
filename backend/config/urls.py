"""
Risk-Guard Backend — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── Auth ─────────────────────────────────────────────────────────────
    path("api/auth/", include("apps.accounts.urls")),

    # ── Core Resources ──────────────────────────────────────────────────
    path("api/", include("apps.orders.urls")),
    path("api/", include("apps.customers.urls")),
    path("api/", include("apps.addresses.urls")),

    # ── Store & Integrations ────────────────────────────────────────────
    path("api/stores/", include("apps.stores.urls")),

    # ── Chatbot & Messaging ─────────────────────────────────────────────
    path("api/chatbot/", include("apps.chatbot.urls")),

    # ── Risk Engine ─────────────────────────────────────────────────────
    path("api/risk/", include("apps.risk_engine.urls")),

    # ── Analytics ───────────────────────────────────────────────────────
    path("api/analytics/", include("apps.analytics.urls")),

    # ── Account Management ──────────────────────────────────────────────
    path("api/accounts/", include("apps.accounts.profile_urls")),
]
