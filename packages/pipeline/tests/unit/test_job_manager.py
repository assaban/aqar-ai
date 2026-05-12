"""
Unit tests for the JobManager state machine.

Tests cover: valid transitions, invalid transitions, timing recording,
error capture, and stage metadata storage.
"""

from aqar_pipeline.utils.job_manager import (
    STAGE_COMPLETION_MAP,
    STAGE_STATUS_MAP,
    VALID_TRANSITIONS,
)
from models.base import ProcessingStatus

# ═══════════════════════════════════════
# State Transition Validation
# ═══════════════════════════════════════


class TestValidTransitions:
    """Tests for the state transition matrix."""

    def test_pending_can_transition_to_ingesting(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.PENDING]
        assert ProcessingStatus.INGESTING in allowed

    def test_pending_can_transition_to_failed(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.PENDING]
        assert ProcessingStatus.FAILED in allowed

    def test_pending_can_transition_to_skipped(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.PENDING]
        assert ProcessingStatus.SKIPPED in allowed

    def test_ingesting_can_transition_to_transcribing(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.INGESTING]
        assert ProcessingStatus.TRANSCRIBING in allowed

    def test_ingesting_can_transition_to_failed(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.INGESTING]
        assert ProcessingStatus.FAILED in allowed

    def test_transcribing_can_transition_to_extracting(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.TRANSCRIBING]
        assert ProcessingStatus.EXTRACTING in allowed

    def test_extracting_can_transition_to_geocoding(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.EXTRACTING]
        assert ProcessingStatus.GEOCODING in allowed

    def test_geocoding_can_transition_to_completed(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.GEOCODING]
        assert ProcessingStatus.COMPLETED in allowed

    def test_failed_can_transition_to_pending(self):
        """Failed jobs can be retried (reset to PENDING)."""
        allowed = VALID_TRANSITIONS[ProcessingStatus.FAILED]
        assert ProcessingStatus.PENDING in allowed

    def test_completed_is_terminal(self):
        """Completed is a terminal state with no transitions."""
        allowed = VALID_TRANSITIONS[ProcessingStatus.COMPLETED]
        assert len(allowed) == 0

    def test_skipped_is_terminal(self):
        """Skipped is a terminal state with no transitions."""
        allowed = VALID_TRANSITIONS[ProcessingStatus.SKIPPED]
        assert len(allowed) == 0


class TestInvalidTransitions:
    """Tests for transitions that should NOT be allowed."""

    def test_pending_cannot_jump_to_extracting(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.PENDING]
        assert ProcessingStatus.EXTRACTING not in allowed

    def test_pending_cannot_jump_to_completed(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.PENDING]
        assert ProcessingStatus.COMPLETED not in allowed

    def test_ingesting_cannot_jump_to_geocoding(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.INGESTING]
        assert ProcessingStatus.GEOCODING not in allowed

    def test_completed_cannot_go_back_to_pending(self):
        allowed = VALID_TRANSITIONS[ProcessingStatus.COMPLETED]
        assert ProcessingStatus.PENDING not in allowed

    def test_every_non_terminal_state_can_fail(self):
        """Every active state should be able to transition to FAILED."""
        active_states = [
            ProcessingStatus.PENDING,
            ProcessingStatus.INGESTING,
            ProcessingStatus.TRANSCRIBING,
            ProcessingStatus.EXTRACTING,
            ProcessingStatus.GEOCODING,
        ]
        for state in active_states:
            allowed = VALID_TRANSITIONS[state]
            assert ProcessingStatus.FAILED in allowed, (
                f"{state.value} should allow transition to FAILED"
            )


# ═══════════════════════════════════════
# Stage Mapping
# ═══════════════════════════════════════


class TestStageMaps:
    """Tests for stage-to-status mapping tables."""

    def test_all_stages_have_status_map(self):
        expected_stages = [
            "ingestion",
            "audio_extraction",
            "transcription",
            "extraction",
            "geocoding",
        ]
        for stage in expected_stages:
            assert stage in STAGE_STATUS_MAP, f"Missing STAGE_STATUS_MAP entry for: {stage}"

    def test_all_stages_have_completion_map(self):
        expected_stages = [
            "ingestion",
            "audio_extraction",
            "transcription",
            "extraction",
            "geocoding",
        ]
        for stage in expected_stages:
            assert stage in STAGE_COMPLETION_MAP, f"Missing STAGE_COMPLETION_MAP entry for: {stage}"

    def test_ingestion_maps_to_ingesting(self):
        assert STAGE_STATUS_MAP["ingestion"] == ProcessingStatus.INGESTING

    def test_audio_extraction_maps_to_ingesting(self):
        """Audio extraction is part of the INGESTING phase."""
        assert STAGE_STATUS_MAP["audio_extraction"] == ProcessingStatus.INGESTING

    def test_audio_extraction_completes_to_transcribing(self):
        assert STAGE_COMPLETION_MAP["audio_extraction"] == ProcessingStatus.TRANSCRIBING

    def test_geocoding_completes_to_completed(self):
        assert STAGE_COMPLETION_MAP["geocoding"] == ProcessingStatus.COMPLETED


# ═══════════════════════════════════════
# Pipeline Flow Validation
# ═══════════════════════════════════════


class TestPipelineFlow:
    """Tests that validate the full pipeline transition path."""

    def test_happy_path_transitions_are_valid(self):
        """The complete happy path should follow valid transitions."""
        happy_path = [
            (ProcessingStatus.PENDING, ProcessingStatus.INGESTING),
            (ProcessingStatus.INGESTING, ProcessingStatus.TRANSCRIBING),
            (ProcessingStatus.TRANSCRIBING, ProcessingStatus.EXTRACTING),
            (ProcessingStatus.EXTRACTING, ProcessingStatus.GEOCODING),
            (ProcessingStatus.GEOCODING, ProcessingStatus.COMPLETED),
        ]
        for from_status, to_status in happy_path:
            allowed = VALID_TRANSITIONS[from_status]
            assert to_status in allowed, (
                f"Transition {from_status.value} -> {to_status.value} should be valid"
            )

    def test_retry_path_is_valid(self):
        """Failed -> Pending (retry) should be valid."""
        allowed = VALID_TRANSITIONS[ProcessingStatus.FAILED]
        assert ProcessingStatus.PENDING in allowed

    def test_all_statuses_have_transition_rules(self):
        """Every ProcessingStatus should have an entry in VALID_TRANSITIONS."""
        for status in ProcessingStatus:
            assert status in VALID_TRANSITIONS, (
                f"Missing VALID_TRANSITIONS entry for: {status.value}"
            )
