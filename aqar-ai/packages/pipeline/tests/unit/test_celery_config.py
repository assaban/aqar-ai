"""
Unit tests for Celery app configuration.
"""

from packages.pipeline.aqar_pipeline.celery_app import app


def test_celery_app_exists():
    """Celery app should be configured."""
    assert app is not None
    assert app.main == "aqar_pipeline"


def test_celery_queues_configured():
    """All four pipeline queues should be routed."""
    routes = app.conf.task_routes
    assert "aqar_pipeline.stages.ingestion.*" in routes
    assert "aqar_pipeline.stages.transcription.*" in routes
    assert "aqar_pipeline.stages.extraction.*" in routes
    assert "aqar_pipeline.stages.geocoding.*" in routes


def test_celery_beat_schedule():
    """Scheduled tasks should be defined."""
    schedule = app.conf.beat_schedule
    assert "discover-new-videos" in schedule
    assert "retry-failed-jobs" in schedule


def test_health_check_task():
    """Health check task should return ok."""
    from packages.pipeline.aqar_pipeline.celery_app import health_check

    result = health_check()
    assert result["status"] == "ok"
