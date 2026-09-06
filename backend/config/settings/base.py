"""
Risk-Guard Backend — Base Settings
Shared configuration across all environments.
"""
import os
from pathlib import Path
from datetime import timedelta

# ─── Load .env file ──────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-rg-dev-key-change-in-production-!@#$%^&*()",
)

DEBUG = False

ALLOWED_HOSTS: list[str] = []

# ─── Application Definition ─────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.customers",
    "apps.addresses",
    "apps.orders",
    "apps.telemetry",
    "apps.stores",
    "apps.chatbot",
    "apps.risk_engine",
    "apps.ml_models",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ──────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Auth ────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalization ───────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True

# ─── Static Files ───────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ─── Default PK ─────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Django REST Framework ──────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "utils.pagination.StandardPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
    },
    "EXCEPTION_HANDLER": "utils.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ─── Simple JWT ─────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# ─── Email ───────────────────────────────────────────────────────────────────
# Defaults to the console backend so password-reset emails print to the runserver
# terminal in development. Set EMAIL_BACKEND to the SMTP backend in production.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Risk-Guard <no-reply@riskguard.pk>"
)

# Base URL of the frontend, used to build links inside emails (password reset).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# How long a password-reset link stays valid (seconds). Default 1 hour.
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", str(60 * 60)))

# ─── Twilio / WhatsApp ───────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")
TWILIO_STATUS_CALLBACK_URL = os.environ.get("TWILIO_STATUS_CALLBACK_URL", "")
TWILIO_VALIDATE_SIGNATURES = os.environ.get("TWILIO_VALIDATE_SIGNATURES", "True")

# External IP intelligence
# ipapi is free (no key required, 1000 req/day), ipqualityscore needs an API key
# ipapicom uses ip-api.com: free, 45 req/min, no key required
IP_INTELLIGENCE_PROVIDER = os.environ.get(
    "IP_INTELLIGENCE_PROVIDER",
    "ipapicom",
)
IPQUALITYSCORE_API_KEY = os.environ.get("IPQUALITYSCORE_API_KEY", "")
IP_INTELLIGENCE_TIMEOUT_SECONDS = float(
    os.environ.get("IP_INTELLIGENCE_TIMEOUT_SECONDS", "4")
)

# ─── DeepSeek LLM ────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_TIMEOUT = float(os.environ.get("DEEPSEEK_TIMEOUT", "15"))

# Address intelligence runs on internal heuristics plus courier coverage.
# Set ADDRESS_VALIDATION_PROVIDER=opencage and provide OPENCAGE_API_KEY to
# geocode + validate delivery addresses against OpenCage (free tier: 2,500/day).
# "internal_heuristic" keeps everything offline (completeness-based scoring only).
ADDRESS_VALIDATION_PROVIDER = os.environ.get(
    "ADDRESS_VALIDATION_PROVIDER",
    "internal_heuristic",
)
OPENCAGE_API_KEY = os.environ.get("OPENCAGE_API_KEY", "")
ADDRESS_VALIDATION_TIMEOUT_SECONDS = float(
    os.environ.get("ADDRESS_VALIDATION_TIMEOUT_SECONDS", "5")
)
# Skip re-validating an address that was validated by the same provider within
# this many days (keeps the free-tier quota for genuinely new addresses).
ADDRESS_VALIDATION_FRESHNESS_DAYS = int(
    os.environ.get("ADDRESS_VALIDATION_FRESHNESS_DAYS", "30")
)

# ─── Chatbot ─────────────────────────────────────────────────────────────────
CHATBOT_AUTO_VERIFY_ENABLED = (
    os.environ.get("CHATBOT_AUTO_VERIFY_ENABLED", "True").lower() == "true"
)
CHATBOT_MAX_TURNS = int(os.environ.get("CHATBOT_MAX_TURNS", "10"))
CHATBOT_CONVERSATION_TIMEOUT_HOURS = int(
    os.environ.get("CHATBOT_CONVERSATION_TIMEOUT_HOURS", "24")
)
CHATBOT_NO_REPLY_TIMEOUT_HOURS = int(
    os.environ.get("CHATBOT_NO_REPLY_TIMEOUT_HOURS", "5")
)

# ─── Celery ──────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max per task

CELERY_BEAT_SCHEDULE = {
    "check-chat-timeouts": {
        "task": "apps.chatbot.tasks.check_chat_timeouts",
        "schedule": 60 * 30,  # Every 30 minutes
    },
}
