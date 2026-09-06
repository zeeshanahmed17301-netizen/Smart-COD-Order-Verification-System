"""Views for accounts: signup, profile, onboarding, password change."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MerchantProfile
from .serializers import (
    SignupSerializer,
    UserSerializer,
    MerchantProfileSerializer,
    OnboardingSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()


class SignupView(generics.CreateAPIView):
    """Register a new merchant user."""

    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""

    serializer_class = MerchantProfileSerializer

    def get_object(self) -> MerchantProfile:
        profile, _ = MerchantProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile


class UserUpdateView(generics.UpdateAPIView):
    """Update basic user fields (name, username)."""

    serializer_class = UpdateProfileSerializer

    def get_object(self) -> User:
        return self.request.user


class OnboardingView(APIView):
    """Save onboarding wizard data and mark user as onboarded."""

    def post(self, request):
        profile, _ = MerchantProfile.objects.get_or_create(
            user=request.user
        )
        serializer = OnboardingSerializer(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Mark user as onboarded
        request.user.is_onboarded = True
        request.user.save(update_fields=["is_onboarded"])

        return Response(
            MerchantProfileSerializer(profile).data,
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


# Shared generic response so neither endpoint reveals whether an email exists.
_RESET_REQUESTED_MESSAGE = (
    "If an account exists for that email, a password-reset link has been sent."
)


class PasswordResetRequestView(APIView):
    """Email a password-reset link. Always returns a generic success so the
    endpoint cannot be used to enumerate registered email addresses."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = (
                f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            )
            send_mail(
                subject="Reset your Risk-Guard password",
                message=(
                    f"Hi {user.first_name or user.username},\n\n"
                    "We received a request to reset your Risk-Guard password. "
                    "Click the link below to choose a new one:\n\n"
                    f"{reset_link}\n\n"
                    "This link expires in 1 hour. If you didn't request a reset, "
                    "you can safely ignore this email.\n\n"
                    "— Risk-Guard"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

        return Response(
            {"detail": _RESET_REQUESTED_MESSAGE},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Set a new password given a valid uid + token from the reset email."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Your password has been reset. You can now sign in."},
            status=status.HTTP_200_OK,
        )
