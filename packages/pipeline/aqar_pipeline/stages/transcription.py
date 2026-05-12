"""
Aqar.ai: Transcription Stage
==============================
Celery task that transcribes audio files using OpenAI Whisper.

Processes WAV audio (16kHz mono) and produces:
  - Full transcript text
  - Timestamped segments with per-segment confidence
  - Detected language and overall confidence score
  - Normalized text (Darija number words, abbreviations)

Tasks:
  - transcribe_audio: Transcribes a single audio file.
"""

from __future__ import annotations

import logging
import os

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models.base import Transcript, VideoSource

logger = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aqar:aqar_dev_password@db:5432/aqar_db",
)

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ar")


def _get_sync_session() -> Session:
    """Create a sync SQLAlchemy session for use in Celery tasks."""
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    return Session(engine)


def _extract_segments(result: dict) -> list[dict]:
    """
    Extract timestamped segments from Whisper result.

    Each segment contains: start, end, text, and average log probability
    (used as a confidence proxy).
    """
    segments = []
    for seg in result.get("segments", []):
        segments.append(
            {
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "text": seg.get("text", "").strip(),
                "avg_logprob": round(seg.get("avg_logprob", 0.0), 4),
                "no_speech_prob": round(seg.get("no_speech_prob", 0.0), 4),
            }
        )
    return segments


def _calculate_confidence(segments: list[dict]) -> float:
    """
    Calculate overall transcription confidence from segment log probabilities.

    Whisper's avg_logprob is negative (log probability). We convert to
    a 0-1 confidence scale using: confidence = exp(avg_logprob).

    Segments with high no_speech_prob are weighted down.
    """
    import math

    if not segments:
        return 0.0

    confidences = []
    for seg in segments:
        logprob = seg.get("avg_logprob", -1.0)
        no_speech = seg.get("no_speech_prob", 0.0)

        # Convert log prob to linear (0-1 range)
        segment_conf = math.exp(logprob) if logprob > -10 else 0.0

        # Penalize segments likely to be non-speech
        if no_speech > 0.5:
            segment_conf *= 0.5

        confidences.append(segment_conf)

    return round(sum(confidences) / len(confidences), 4) if confidences else 0.0


@shared_task(
    name="aqar_pipeline.stages.transcription.transcribe_audio",
    queue="transcription",
    bind=True,
    max_retries=2,
    default_retry_delay=180,
)
def transcribe_audio(self, video_source_id: str, audio_path: str):
    """
    Transcribe an audio file using OpenAI Whisper.

    This task is triggered after audio extraction completes. It loads
    the Whisper model (cached singleton), transcribes the audio, stores
    the result in the Transcript table, and triggers audio cleanup.

    Args:
        video_source_id: UUID string of the VideoSource record.
        audio_path: Path to the WAV file to transcribe.

    Returns:
        Dict with transcription results and metadata.
    """
    import time

    from aqar_pipeline.stages.audio_extraction import cleanup_audio
    from aqar_pipeline.utils.job_manager import JobManager
    from aqar_pipeline.utils.text_normalizer import normalize_transcript
    from aqar_pipeline.utils.whisper_loader import get_whisper_model

    logger.info(f"Starting transcription for video: {video_source_id}")

    # Verify audio file exists
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return {"status": "error", "message": f"Audio file not found: {audio_path}"}

    session = _get_sync_session()

    try:
        # Load video source
        video = session.execute(
            select(VideoSource).where(VideoSource.id == video_source_id)
        ).scalar_one_or_none()

        if not video:
            logger.error(f"VideoSource not found: {video_source_id}")
            return {"status": "error", "message": "Video not found"}

        # Check if transcript already exists (idempotency)
        existing_transcript = session.execute(
            select(Transcript).where(Transcript.video_source_id == video.id)
        ).scalar_one_or_none()

        if existing_transcript:
            logger.info(f"Transcript already exists for video: {video_source_id}")
            return {
                "status": "completed",
                "cached": True,
                "transcript_id": str(existing_transcript.id),
            }

        # Initialize JobManager
        manager = JobManager(session, video_source_id)
        manager.start_stage("transcription")

        # Load Whisper model (cached singleton)
        model = get_whisper_model()

        # Transcribe
        logger.info(f"Transcribing with Whisper ({WHISPER_MODEL}): {audio_path}")
        start_time = time.time()

        result = model.transcribe(
            audio_path,
            language=WHISPER_LANGUAGE,
            task="transcribe",
            verbose=False,
        )

        transcription_time = round(time.time() - start_time, 2)
        logger.info(f"Transcription completed in {transcription_time}s")

        # Extract data from result
        full_text = result.get("text", "").strip()
        detected_language = result.get("language", WHISPER_LANGUAGE)
        segments = _extract_segments(result)
        confidence = _calculate_confidence(segments)

        # Normalize Darija text
        normalized_text = normalize_transcript(full_text)

        # Create Transcript record
        transcript = Transcript(
            video_source_id=video.id,
            full_text=normalized_text,
            language=detected_language,
            confidence=confidence,
            segments=segments,
            whisper_model=WHISPER_MODEL,
            processing_time_seconds=transcription_time,
        )
        session.add(transcript)
        session.flush()

        # Complete the stage
        manager.complete_stage(
            metadata={
                "model": WHISPER_MODEL,
                "language_detected": detected_language,
                "confidence": confidence,
                "segments_count": len(segments),
                "text_length": len(normalized_text),
                "processing_time_seconds": transcription_time,
            }
        )

        logger.info(
            f"Transcript saved: {len(normalized_text)} chars, "
            f"{len(segments)} segments, "
            f"confidence={confidence}, "
            f"language={detected_language}"
        )

        # Cleanup audio file (no longer needed)
        cleanup_audio.delay(video.external_id)

        # Chain to LLM extraction
        from aqar_pipeline.stages.extraction import extract_properties

        extract_properties.delay(video_source_id)

        return {
            "status": "completed",
            "video_source_id": video_source_id,
            "transcript_id": str(transcript.id),
            "language": detected_language,
            "confidence": confidence,
            "text_length": len(normalized_text),
            "segments_count": len(segments),
            "processing_time_seconds": transcription_time,
            "model": WHISPER_MODEL,
        }

    except self.MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for transcription: {video_source_id}")
        try:
            manager = JobManager(session, video_source_id)
            manager.fail(
                stage="transcription",
                message="Max retries exceeded for transcription",
            )
        except Exception:
            pass
        return {"status": "failed", "message": "Max retries exceeded"}

    except Exception as e:
        session.rollback()
        logger.error(f"Transcription error for {video_source_id}: {e}")
        try:
            manager = JobManager(session, video_source_id)
            manager.fail(stage="transcription", message=str(e), exc=e)
        except Exception:
            pass
        raise self.retry(exc=e) from e

    finally:
        session.close()
