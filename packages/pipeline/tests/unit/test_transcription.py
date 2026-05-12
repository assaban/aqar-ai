"""
Unit tests for the transcription stage.

Tests cover: segment extraction, confidence calculation,
and Whisper configuration. Does NOT test actual Whisper inference
(that requires the model to be loaded).
"""


from aqar_pipeline.stages.transcription import (
    _calculate_confidence,
    _extract_segments,
)

# ═══════════════════════════════════════
# Segment Extraction
# ═══════════════════════════════════════


class TestExtractSegments:
    """Tests for _extract_segments()."""

    def test_extracts_basic_segments(self):
        result = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": " Hello world",
                    "avg_logprob": -0.3,
                    "no_speech_prob": 0.01,
                },
                {
                    "start": 2.5,
                    "end": 5.0,
                    "text": " Second segment",
                    "avg_logprob": -0.4,
                    "no_speech_prob": 0.02,
                },
            ]
        }
        segments = _extract_segments(result)

        assert len(segments) == 2
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 2.5
        assert segments[0]["text"] == "Hello world"
        assert segments[1]["text"] == "Second segment"

    def test_handles_empty_result(self):
        segments = _extract_segments({})
        assert segments == []

    def test_handles_missing_segments_key(self):
        segments = _extract_segments({"text": "some text"})
        assert segments == []

    def test_rounds_timestamps(self):
        result = {
            "segments": [
                {
                    "start": 1.23456789,
                    "end": 3.98765432,
                    "text": "test",
                    "avg_logprob": -0.5,
                    "no_speech_prob": 0.0,
                },
            ]
        }
        segments = _extract_segments(result)
        assert segments[0]["start"] == 1.23
        assert segments[0]["end"] == 3.99

    def test_strips_segment_text(self):
        result = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "  padded text  ",
                    "avg_logprob": -0.3,
                    "no_speech_prob": 0.0,
                },
            ]
        }
        segments = _extract_segments(result)
        assert segments[0]["text"] == "padded text"

    def test_handles_missing_fields_gracefully(self):
        result = {
            "segments": [
                {"text": "minimal segment"},
            ]
        }
        segments = _extract_segments(result)
        assert len(segments) == 1
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 0.0
        assert segments[0]["avg_logprob"] == 0.0


# ═══════════════════════════════════════
# Confidence Calculation
# ═══════════════════════════════════════


class TestCalculateConfidence:
    """Tests for _calculate_confidence()."""

    def test_high_confidence_segments(self):
        """Segments with high log probability should yield high confidence."""
        segments = [
            {"avg_logprob": -0.1, "no_speech_prob": 0.01},
            {"avg_logprob": -0.2, "no_speech_prob": 0.02},
        ]
        conf = _calculate_confidence(segments)
        assert conf > 0.7

    def test_low_confidence_segments(self):
        """Segments with low log probability should yield low confidence."""
        segments = [
            {"avg_logprob": -2.0, "no_speech_prob": 0.1},
            {"avg_logprob": -3.0, "no_speech_prob": 0.1},
        ]
        conf = _calculate_confidence(segments)
        assert conf < 0.3

    def test_empty_segments(self):
        assert _calculate_confidence([]) == 0.0

    def test_non_speech_penalty(self):
        """Segments with high no_speech_prob should be penalized."""
        good = [{"avg_logprob": -0.3, "no_speech_prob": 0.01}]
        noisy = [{"avg_logprob": -0.3, "no_speech_prob": 0.9}]

        good_conf = _calculate_confidence(good)
        noisy_conf = _calculate_confidence(noisy)

        assert good_conf > noisy_conf

    def test_confidence_is_bounded(self):
        """Confidence should be between 0 and 1."""
        segments = [
            {"avg_logprob": -0.001, "no_speech_prob": 0.0},  # Very high confidence
        ]
        conf = _calculate_confidence(segments)
        assert 0.0 <= conf <= 1.0

    def test_very_negative_logprob(self):
        """Extremely negative logprobs should not cause errors."""
        segments = [
            {"avg_logprob": -100.0, "no_speech_prob": 0.0},
        ]
        conf = _calculate_confidence(segments)
        assert conf == 0.0  # exp(-100) is effectively zero
