from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "ai_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.modules.master_cv.tasks",
        "app.modules.jobs.tasks",
        "app.modules.companies.tasks",
        "app.modules.matching.tasks",
    ],
)

celery_app.conf.update(
    task_default_queue="ai_service_queue",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
