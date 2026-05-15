"""
Aqar.ai - Celery Application Configuration
==========================================
Defines task queues, routing, and scheduling for the pipeline.

Queue Architecture:
  - ingestion:     Video discovery and audio extraction
  - transcription: Whisper speech-to-text
  - extraction:    LLM structured data extraction
  - geocoding:     Location resolution and mapping
"""

import os

from celery import Celery
from celery.schedules import crontab

# ── App Configuration ──
app = Celery("aqar_pipeline")

app.conf.update(
    # Broker & Backend
    broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task behavior
    task_track_started=True,
    worker_send_task_events=True, # <── for Flower visibility
    task_send_sent_event=True,    # <── Check event sent?
    task_acks_late=True,  # Re-queue tasks if worker crashes
    worker_prefetch_multiplier=1,  # One task at a time per worker (ML tasks are heavy)
    # Retry
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    # Result
    result_expires=86400,  # 24 hours
    # Queue routing
    task_routes={
        "aqar_pipeline.stages.ingestion.*": {"queue": "ingestion"},
        "aqar_pipeline.stages.audio_extraction.*": {"queue": "ingestion"},
        "aqar_pipeline.stages.transcription.*": {"queue": "transcription"},
        "aqar_pipeline.stages.extraction.*": {"queue": "extraction"},
        "aqar_pipeline.stages.geocoding.*": {"queue": "geocoding"},
    },
    task_default_queue="ingestion",
)

# ── Auto-discover tasks ──
app.autodiscover_tasks(
    [
        "aqar_pipeline.stages",
    ]
)

# ── Scheduled Tasks (Celery Beat) ──
app.conf.beat_schedule = {
    # Discover new videos every 6 hours
    "discover-new-videos": {
        "task": "aqar_pipeline.stages.ingestion.discover_videos",
        "schedule": crontab(minute=0, hour="*/6"),
        "kwargs": {"region": "tangier-tetouan"},
    },
    # Retry failed jobs every hour
    "retry-failed-jobs": {
        "task": "aqar_pipeline.stages.ingestion.retry_failed_jobs",
        "schedule": crontab(minute=30, hour="*"),
    },
}


# ── Health check task ──
@app.task(name="aqar_pipeline.health_check")
def health_check():
    """Simple health check task for monitoring."""
    return {"status": "ok", "service": "aqar-pipeline"}
