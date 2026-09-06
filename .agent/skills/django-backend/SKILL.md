---
name: Django Backend Development
description: Django REST Framework backend best practices for the Risk-Guard project — models, serializers, views, authentication, and API design
---

# Django Backend Development Skill

## Tech Stack
- **Framework**: Django 5.x + Django REST Framework (DRF)
- **Database**: PostgreSQL (recommended) or SQLite (dev)
- **Auth**: Django's built-in auth + JWT (djangorestframework-simplejwt)
- **API**: RESTful with DRF serializers, viewsets, and routers
- **Frontend**: React 19 (Vite) — separate app communicating via API

## Project Structure
```
backend/
├── manage.py
├── requirements.txt
├── config/                    # Project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py           # Shared settings
│   │   ├── development.py    # Dev overrides
│   │   └── production.py     # Prod overrides
│   ├── urls.py               # Root URL config
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/             # User auth, registration, profiles
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests.py
│   ├── orders/               # COD orders, risk scoring
│   ├── customers/            # Customer identity & behavior
│   ├── addresses/            # Address verification
│   ├── chatbot/              # WhatsApp chatbot & messaging
│   ├── analytics/            # Dashboards & reporting
│   └── stores/               # Store connections (Shopify, WooCommerce)
```

## Django Conventions

### Models
```python
from django.db import models

class Order(models.Model):
    """COD order with risk scoring fields."""
    order_id = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='orders')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    risk_score = models.FloatField(default=0.0)
    fraud_score = models.FloatField(default=0.0)
    rto_probability = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'risk_score']),
        ]

    def __str__(self):
        return f"Order {self.order_id}"
```

### Serializers
```python
from rest_framework import serializers

class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_id', 'customer', 'customer_name', 'amount',
                  'status', 'risk_score', 'fraud_score', 'rto_probability',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
```

### ViewSets
```python
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer').all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'risk_level', 'city']
    search_fields = ['order_id', 'customer__name', 'customer__phone']
    ordering_fields = ['created_at', 'risk_score', 'amount']
```

### URLs with Routers
```python
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet)

urlpatterns = router.urls
```

## Authentication (JWT)
```python
# settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
]
```

## CORS Setup (for React frontend)
```python
# settings/base.py
INSTALLED_APPS += ['corsheaders']
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', ...rest]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
]
```

## Coding Rules
1. **PEP 8** — follow Python style guide, use `black` formatter
2. **snake_case** for functions, variables, URLs; **PascalCase** for classes
3. **Type hints** on all function parameters and returns
4. **Docstrings** on all models, views, and serializers (Google style)
5. Use `select_related()` / `prefetch_related()` to avoid N+1 queries
6. Keep views thin — business logic in model methods or service layer
7. Use Django signals sparingly; prefer explicit calls
8. Always use serializer validation, never trust raw input
9. Use environment variables for secrets (never hardcode)
10. Write tests for all API endpoints

## Security Best Practices
- Enable CSRF protection (Django default)
- Use HTTPS in production
- Set `SECURE_*` headers in production settings
- Validate and sanitize all inputs via serializers
- Rate-limit auth endpoints
- Use parameterized queries (Django ORM handles this)
- Never expose stack traces in production

## API Response Format
```json
{
    "count": 150,
    "next": "http://api.example.com/orders/?page=2",
    "previous": null,
    "results": [
        {"id": 1, "order_id": "ORD-001", ...}
    ]
}
```

## Error Response Format
```json
{
    "detail": "Not found.",
    "code": "not_found"
}
```

## Key Dependencies
```
django>=5.0
djangorestframework>=3.15
djangorestframework-simplejwt
django-cors-headers
django-filter
psycopg2-binary          # PostgreSQL
python-decouple           # Environment variables
celery                    # Background tasks (optional)
redis                     # Celery broker (optional)
```

## Common Patterns

### Service Layer (for complex business logic)
```python
# apps/orders/services.py
class RiskScoringService:
    @staticmethod
    def calculate_risk(order):
        """Calculate composite risk score for an order."""
        customer_risk = CustomerRiskCalculator.score(order.customer)
        address_risk = AddressVerifier.score(order.address)
        product_risk = ProductRiskCalculator.score(order.items)
        return weighted_average(customer_risk, address_risk, product_risk)
```

### Custom Permissions
```python
from rest_framework.permissions import BasePermission

class IsStoreOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.store.owner == request.user
```

### Pagination
```python
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
```
