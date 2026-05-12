"""
Pipeline stages: ingestion, transcription, extraction, geocoding.

Each stage is a Celery task that processes data through one step
of the pipeline. Stages are connected via task chaining.
"""

from aqar_pipeline.stages.audio_extraction import (
    cleanup_audio,
    extract_audio,
)
from aqar_pipeline.stages.extraction import (
    extract_properties,
)
from aqar_pipeline.stages.geocoding import (
    geocode_properties,
)
from aqar_pipeline.stages.ingestion import (
    discover_videos,
    ingest_video,
    retry_failed_jobs,
)
from aqar_pipeline.stages.transcription import (
    transcribe_audio,
)

__all__ = [
    "discover_videos",
    "ingest_video",
    "retry_failed_jobs",
    "extract_audio",
    "cleanup_audio",
    "transcribe_audio",
    "extract_properties",
    "geocode_properties",
]
