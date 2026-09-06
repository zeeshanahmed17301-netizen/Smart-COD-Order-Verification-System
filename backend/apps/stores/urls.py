"""URL configuration for stores."""
from rest_framework.routers import DefaultRouter
from .views import StoreConnectionViewSet, APIKeyViewSet, WebhookViewSet

router = DefaultRouter()
router.register(r"connections", StoreConnectionViewSet, basename="store-connection")
router.register(r"api-keys", APIKeyViewSet, basename="api-key")
router.register(r"webhooks", WebhookViewSet, basename="webhook")

urlpatterns = router.urls
