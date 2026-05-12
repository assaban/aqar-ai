"""
Pipeline stages: ingestion, transcription, extraction, geocoding.

Each stage is a Celery task that processes data through one step
of the pipeline. Stages are connected via task chaining.
"""

from aqar_pipeline.stages.ingestion import (
    discover_videos,
    ingest_video,
    retry_failed_jobs,
)
from aqar_pipeline.stages.audio_extraction import (
    extract_audio,
    cleanup_audio,
)

__all__ = [
    "discover_videos",
    "ingest_video",
    "retry_failed_jobs",
    "extract_audio",
    "cleanup_audio",
]
