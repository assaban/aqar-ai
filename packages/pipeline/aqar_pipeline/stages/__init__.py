"""
Pipeline stages: ingestion, transcription, extraction, geocoding.

Each stage is a Celery task that processes data through one step
of the pipeline. Stages are connected via task chaining.
"""

from aqar_pipeline.stages.audio_extraction import (
    cleanup_audio,
    extract_audio,
)
from aqar_pipeline.stages.ingestion import (
    discover_videos,
    ingest_video,
    retry_failed_jobs,
)

__all__ = [
    "discover_videos",
    "ingest_video",
    "retry_failed_jobs",
    "extract_audio",
    "cleanup_audio",
]
