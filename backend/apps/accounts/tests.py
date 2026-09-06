from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MerchantProfile

User = get_user_model()


class AccountFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            username="merchant",
            first_name="Merchant",
            last_name="User",
            password="StrongPass123!",
        )
        MerchantProfile.objects.create(user=self.user)
        self.client.force_authenticate(self.user)

    def test_onboarding_accepts_machine_values_and_marks_user_onboarded(self):
        payload = {
            "store_name": "Risk Guard Store",
            "category": "fashion",
            "country": "Pakistan",
            "whatsapp_number": "+923001234567",
            "whatsapp_api_key": "token-123",
            "language": "urdu",
            "auto_send": "1min",
            "auto_cancel": "1hour",
        }

        response = self.client.post("/api/accounts/onboarding/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        profile = MerchantProfile.objects.get(user=self.user)
        self.assertTrue(self.user.is_onboarded)
        self.assertEqual(profile.auto_send, "1min")
        self.assertEqual(profile.auto_cancel, "1hour")

    def test_user_update_allows_email_change(self):
        response = self.client.put(
            "/api/accounts/profile/update/",
            {
                "first_name": "Updated",
                "last_name": "Merchant",
                "username": "merchant",
                "email": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")
