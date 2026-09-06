# Import Celery app so it's available as `config.celery`
from .celery import app as celery_app

__all__ = ["celery_app"]
