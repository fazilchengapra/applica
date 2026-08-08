from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "ai_service",                              # app name — distinct from user_service's "app"
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.modules.master_cv.tasks",         # register task modules explicitly
        # "app.modules.job_matching.tasks",    # add as you build more
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