"""
Aqar.ai: Job Manager
=====================
Centralized state machine for ProcessingJob lifecycle.

Handles:
  - Valid state transitions with enforcement
  - Per-stage timing instrumentation
  - Error recording with stage context
  - Stage metadata storage

Usage in Celery tasks:
    manager = JobManager(session, video_source_id)
    manager.start_stage("audio_extraction")
    # ... do work ...
    manager.complete_stage()  # auto-records timing
    manager.chain_next()      # triggers next stage
"""

from __future__ import annotations

import contextlib
import logging
import time
import traceback
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.base import ProcessingJob, ProcessingStatus

logger = logging.getLogger(__name__)

# Valid state transitions: {from_status: [allowed_to_statuses]}
VALID_TRANSITIONS: dict[ProcessingStatus, list[ProcessingStatus]] = {
    ProcessingStatus.PENDING: [
        ProcessingStatus.INGESTING,
        ProcessingStatus.FAILED,
        ProcessingStatus.SKIPPED,
    ],
    ProcessingStatus.INGESTING: [
        ProcessingStatus.TRANSCRIBING,
        ProcessingStatus.FAILED,
    ],
    ProcessingStatus.TRANSCRIBING: [
        ProcessingStatus.EXTRACTING,
        ProcessingStatus.FAILED,
    ],
    ProcessingStatus.EXTRACTING: [
        ProcessingStatus.GEOCODING,
        ProcessingStatus.FAILED,
    ],
    ProcessingStatus.GEOCODING: [
        ProcessingStatus.COMPLETED,
        ProcessingStatus.FAILED,
    ],
    ProcessingStatus.FAILED: [
        ProcessingStatus.PENDING,  # retry resets to PENDING
    ],
    ProcessingStatus.COMPLETED: [],  # terminal state
    ProcessingStatus.SKIPPED: [],  # terminal state
}

# Maps stage name to the status set when starting that stage
STAGE_STATUS_MAP: dict[str, ProcessingStatus] = {
    "ingestion": ProcessingStatus.INGESTING,
    "audio_extraction": ProcessingStatus.INGESTING,
    "transcription": ProcessingStatus.TRANSCRIBING,
    "extraction": ProcessingStatus.EXTRACTING,
    "geocoding": ProcessingStatus.GEOCODING,
}

# Maps stage name to the next status after successful completion
STAGE_COMPLETION_MAP: dict[str, ProcessingStatus] = {
    "ingestion": ProcessingStatus.INGESTING,  # stays INGESTING, audio_extraction continues
    "audio_extraction": ProcessingStatus.TRANSCRIBING,
    "transcription": ProcessingStatus.EXTRACTING,
    "extraction": ProcessingStatus.GEOCODING,
    "geocoding": ProcessingStatus.COMPLETED,
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    pass


class JobManager:
    """
    Manages the lifecycle of a ProcessingJob.

    Provides methods for starting/completing stages with automatic
    timing, recording errors, and validating state transitions.
    """

    def __init__(self, session: Session, video_source_id: str):
        """
        Initialize the job manager.

        Args:
            session: SQLAlchemy sync session.
            video_source_id: UUID string of the VideoSource record.
        """
        self.session = session
        self.video_source_id = video_source_id
        self._stage_start_time: float | None = None
        self._current_stage: str | None = None
        self._job: ProcessingJob | None = None

    @property
    def job(self) -> ProcessingJob:
        """Lazy-load and cache the ProcessingJob."""
        if self._job is None:
            self._job = self.session.execute(
                select(ProcessingJob).where(ProcessingJob.video_source_id == self.video_source_id)
            ).scalar_one_or_none()

            if self._job is None:
                raise ValueError(
                    f"No ProcessingJob found for video_source_id: {self.video_source_id}"
                )
        return self._job

    def _validate_transition(self, from_status: ProcessingStatus, to_status: ProcessingStatus):
        """Validate that a state transition is allowed."""
        allowed = VALID_TRANSITIONS.get(from_status, [])
        if to_status not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition: {from_status.value} -> {to_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

    def _set_status(self, new_status: ProcessingStatus):
        """Set the job status with transition validation."""
        self._validate_transition(self.job.status, new_status)
        self.job.status = new_status
        self.job.updated_at = datetime.now(UTC)

    def start_stage(self, stage_name: str):
        """
        Mark the beginning of a pipeline stage.

        Sets the job status to the appropriate state and starts the timer.
        If the job is already in a terminal state (COMPLETED, SKIPPED),
        this is a no-op to handle Celery re-delivery gracefully.

        Args:
            stage_name: Name of the stage (e.g. "ingestion", "audio_extraction").

        Returns:
            True if the stage was started, False if skipped (terminal state).
        """
        # Guard: skip if job is already in a terminal state
        if self.job.status in (ProcessingStatus.COMPLETED, ProcessingStatus.SKIPPED):
            logger.info(
                f"Skipping stage {stage_name}: job already {self.job.status.value} "
                f"(job={self.job.id})"
            )
            return False

        self._current_stage = stage_name
        self._stage_start_time = time.time()

        # Set status based on stage
        target_status = STAGE_STATUS_MAP.get(stage_name)
        if target_status and self.job.status != target_status:
            with contextlib.suppress(InvalidTransitionError):
                self._set_status(target_status)

        self.job.current_stage = stage_name
        if self.job.started_at is None:
            self.job.started_at = datetime.now(UTC)

        self.session.commit()

        logger.info(
            f"Stage started: {stage_name} (job={self.job.id}, status={self.job.status.value})"
        )
        return True

    def complete_stage(self, metadata: dict | None = None):
        """
        Mark the current stage as complete.

        Records elapsed time and optionally stores stage metadata.
        Transitions the job to the next status.

        Args:
            metadata: Optional dict of stage-specific metadata to store.
        """
        if self._current_stage is None:
            raise RuntimeError("No stage is currently active. Call start_stage() first.")

        # Record timing
        elapsed = 0.0
        if self._stage_start_time is not None:
            elapsed = round(time.time() - self._stage_start_time, 2)

        timings = self.job.stage_timings or {}
        timings[self._current_stage] = elapsed
        self.job.stage_timings = timings

        # Record stage metadata
        if metadata:
            stage_meta = self.job.stage_metadata or {}
            stage_meta[self._current_stage] = metadata
            self.job.stage_metadata = stage_meta

        # 2. Update the transition logic to use suppress
        next_status = STAGE_COMPLETION_MAP.get(self._current_stage)
        if next_status and self.job.status != next_status:
            with contextlib.suppress(InvalidTransitionError):
                self._set_status(next_status)

        self.session.commit()

        logger.info(
            f"Stage completed: {self._current_stage} "
            f"(elapsed={elapsed}s, job={self.job.id}, status={self.job.status.value})"
        )

        self._current_stage = None
        self._stage_start_time = None

    def fail(self, stage: str, message: str, exc: Exception | None = None):
        """
        Record a failure for the current job.

        Args:
            stage: Name of the stage that failed.
            message: Human-readable error message.
            exc: Optional exception for traceback recording.
        """
        try:
            self._set_status(ProcessingStatus.FAILED)
        except InvalidTransitionError:
            # Already failed or in a terminal state
            self.job.status = ProcessingStatus.FAILED

        self.job.error_stage = stage
        self.job.error_message = message
        self.job.current_stage = stage

        if exc:
            self.job.error_traceback = traceback.format_exc()

        # Record partial timing if stage was active
        if self._stage_start_time is not None:
            elapsed = round(time.time() - self._stage_start_time, 2)
            timings = self.job.stage_timings or {}
            timings[stage] = elapsed
            self.job.stage_timings = timings

        self.session.commit()

        logger.error(f"Stage failed: {stage} (job={self.job.id}, error={message})")

        self._current_stage = None
        self._stage_start_time = None

    def mark_completed(self):
        """Mark the entire pipeline as completed. Safe to call multiple times."""
        if self.job.status == ProcessingStatus.COMPLETED:
            return
        with contextlib.suppress(InvalidTransitionError):
            self._set_status(ProcessingStatus.COMPLETED)
        self.job.completed_at = self.job.completed_at or datetime.now(UTC)
        self.job.current_stage = None
        self.session.commit()
        logger.info(f"Pipeline completed (job={self.job.id})")

    def mark_skipped(self, reason: str):
        """Mark the job as skipped (e.g. duplicate, too long)."""
        self._set_status(ProcessingStatus.SKIPPED)
        self.job.error_message = reason
        self.job.current_stage = None
        self.session.commit()

        logger.info(f"Pipeline skipped: {reason} (job={self.job.id})")

    def get_total_elapsed(self) -> float:
        """Calculate total processing time across all stages."""
        timings = self.job.stage_timings or {}
        return round(sum(timings.values()), 2)
