"""URL configuration for chatbot."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatbotSettingsView, ConversationViewSet, MessageViewSet, TriggerWhatsAppView
from .webhooks import TwilioIncomingWebhookView

router = DefaultRouter()
router.register(r"conversations", ConversationViewSet, basename="conversation")

# Nested message router
message_list = MessageViewSet.as_view({"get": "list", "post": "create"})
message_detail = MessageViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path("settings/", ChatbotSettingsView.as_view(), name="chatbot-settings"),
    path("trigger/", TriggerWhatsAppView.as_view(), name="chatbot-trigger"),
    path("", include(router.urls)),
    path(
        "conversations/<int:conversation_pk>/messages/",
        message_list,
        name="conversation-messages",
    ),
    path(
        "conversations/<int:conversation_pk>/messages/<int:pk>/",
        message_detail,
        name="conversation-message-detail",
    ),
    # Twilio webhook
    path(
        "webhooks/twilio/incoming/",
        TwilioIncomingWebhookView.as_view(),
        name="twilio-incoming-webhook",
    ),
]
