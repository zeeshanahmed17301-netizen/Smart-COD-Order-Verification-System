"""Celery application for Risk-Guard background tasks.

Usage:
    celery -A config worker -l info
    celery -A config beat -l info
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("riskguard")

# Read config from Django settings, namespace CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every installed app
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Sanity check: celery -A config call config.celery.debug_task"""
    print(f"Request: {self.request!r}")
