"""Celery application configuration for the PE Investment Platform."""

from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "pe_platform",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["core.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 min hard limit
    task_soft_time_limit=300,  # 5 min soft limit
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "nightly-ingestion": {
        "task": "core.tasks.run_nightly_ingestion_task",
        "schedule": crontab(hour=3, minute=0),
    },
}
