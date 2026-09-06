"""Admin for chatbot."""
from django.contrib import admin
from .models import ChatbotSettings, Conversation, Message, WhatsAppInteraction


@admin.register(ChatbotSettings)
class ChatbotSettingsAdmin(admin.ModelAdmin):
    list_display = ["merchant", "whatsapp_number", "is_connected", "language"]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["timestamp"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "started_at", "completed_at"]
    list_filter = ["status"]
    inlines = [MessageInline]


@admin.register(WhatsAppInteraction)
class WhatsAppInteractionAdmin(admin.ModelAdmin):
    list_display = ["order", "customer_response", "time_to_first_reply", "nudges_sent"]
