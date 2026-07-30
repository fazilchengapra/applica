import os
import django

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings")
django.setup()

celery_app = Celery("app")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()