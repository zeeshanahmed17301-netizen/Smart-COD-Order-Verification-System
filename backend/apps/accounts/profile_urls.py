"""Profile URL configuration: profile, onboarding, password change."""
from django.urls import path

from .views import ProfileView, UserUpdateView, OnboardingView, ChangePasswordView

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="accounts-profile"),
    path("profile/update/", UserUpdateView.as_view(), name="accounts-user-update"),
    path("onboarding/", OnboardingView.as_view(), name="accounts-onboarding"),
    path("change-password/", ChangePasswordView.as_view(), name="accounts-change-password"),
]
