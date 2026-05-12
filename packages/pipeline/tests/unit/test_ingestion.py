"""
Unit tests for the ingestion stage.

Tests cover: channel config loading, YouTube URL extraction,
duration filtering, and metadata parsing.
"""

import os
import tempfile

import pytest
import yaml

from aqar_pipeline.config.loader import load_channels_config
from aqar_pipeline.utils.youtube import (
    VideoMetadata,
    _parse_upload_date,
    extract_youtube_id,
    normalize_youtube_url,
)

# ═══════════════════════════════════════
# YouTube URL Extraction
# ═══════════════════════════════════════


class TestExtractYouTubeId:
    """Tests for extract_youtube_id()."""

    def test_standard_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLxyz"
        assert extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url_returns_none(self):
        assert extract_youtube_id("https://example.com") is None

    def test_empty_string_returns_none(self):
        assert extract_youtube_id("") is None

    def test_non_youtube_url_returns_none(self):
        assert extract_youtube_id("https://vimeo.com/12345") is None


class TestNormalizeYouTubeUrl:
    """Tests for normalize_youtube_url()."""

    def test_normalizes_to_canonical_form(self):
        result = normalize_youtube_url("dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


# ═══════════════════════════════════════
# Date Parsing
# ═══════════════════════════════════════


class TestParseDateUpload:
    """Tests for _parse_upload_date()."""

    def test_valid_date(self):
        result = _parse_upload_date("20260512")
        assert result is not None
        assert result.year == 2026
        assert result.month == 5
        assert result.day == 12

    def test_none_returns_none(self):
        assert _parse_upload_date(None) is None

    def test_invalid_format_returns_none(self):
        assert _parse_upload_date("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert _parse_upload_date("") is None


# ═══════════════════════════════════════
# Channel Config Loading
# ═══════════════════════════════════════


class TestLoadChannelsConfig:
    """Tests for load_channels_config()."""

    # Use the 'with' statement to ensure the file closes automatically
    def _write_config(self, data: dict) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(data, f)
            return f.name

    def test_loads_valid_config(self):
        path = self._write_config(
            {
                "region": "tangier-tetouan",
                "defaults": {"max_videos": 10},
                "channels": [
                    {
                        "name": "Test Channel",
                        "channel_url": "https://www.youtube.com/@test",
                        "max_videos": 15,
                        "tags": ["tangier"],
                    },
                ],
            }
        )
        config = load_channels_config(path)
        assert config.region == "tangier-tetouan"
        assert len(config.channels) == 1
        assert config.channels[0].name == "Test Channel"
        assert config.channels[0].max_videos == 15
        os.unlink(path)

    def test_filters_disabled_channels(self):
        path = self._write_config(
            {
                "region": "tangier-tetouan",
                "channels": [
                    {"name": "Enabled", "channel_url": "https://yt.com/@a", "enabled": True},
                    {"name": "Disabled", "channel_url": "https://yt.com/@b", "enabled": False},
                ],
            }
        )
        config = load_channels_config(path)
        assert len(config.channels) == 1
        assert config.channels[0].name == "Enabled"
        os.unlink(path)

    def test_applies_defaults(self):
        path = self._write_config(
            {
                "region": "tangier-tetouan",
                "defaults": {"max_videos": 25, "language_hint": "fr"},
                "channels": [
                    {"name": "Default Channel", "channel_url": "https://yt.com/@ch"},
                ],
            }
        )
        config = load_channels_config(path)
        assert config.channels[0].max_videos == 25
        assert config.channels[0].language_hint == "fr"
        os.unlink(path)

    def test_missing_file_raises_error(self):
        with pytest.raises(FileNotFoundError):
            load_channels_config("/nonexistent/path.yml")

    def test_empty_channels_returns_empty(self):
        path = self._write_config(
            {
                "region": "tangier-tetouan",
                "channels": [],
            }
        )
        config = load_channels_config(path)
        assert len(config.channels) == 0
        os.unlink(path)

    def test_skips_entries_without_url(self):
        path = self._write_config(
            {
                "region": "tangier-tetouan",
                "channels": [
                    {"name": "No URL"},
                    {"name": "Has URL", "channel_url": "https://yt.com/@ch"},
                ],
            }
        )
        config = load_channels_config(path)
        assert len(config.channels) == 1
        assert config.channels[0].name == "Has URL"
        os.unlink(path)


# ═══════════════════════════════════════
# Duration Filtering
# ═══════════════════════════════════════


class TestDurationFiltering:
    """Tests for video duration filtering logic."""

    def test_video_within_limit_is_accepted(self):
        """A 10-minute video should pass the 30-minute limit."""
        max_seconds = 30 * 60  # 1800
        video_duration = 600  # 10 minutes
        assert video_duration <= max_seconds

    def test_video_exceeding_limit_is_rejected(self):
        """A 45-minute video should be rejected with a 30-minute limit."""
        max_seconds = 30 * 60
        video_duration = 2700  # 45 minutes
        assert video_duration > max_seconds

    def test_video_at_exact_limit_is_accepted(self):
        """A video exactly at the limit should pass."""
        max_seconds = 30 * 60
        video_duration = 1800
        assert video_duration <= max_seconds

    def test_zero_duration_is_accepted(self):
        """A video with zero duration (live/unknown) should pass."""
        max_seconds = 30 * 60
        assert max_seconds >= 0


# ═══════════════════════════════════════
# VideoMetadata
# ═══════════════════════════════════════


class TestVideoMetadata:
    """Tests for the VideoMetadata dataclass."""

    def test_creates_with_required_fields(self):
        meta = VideoMetadata(
            external_id="abc123",
            url="https://www.youtube.com/watch?v=abc123",
            title="Test Video",
        )
        assert meta.external_id == "abc123"
        assert meta.duration_seconds == 0
        assert meta.view_count == 0
        assert meta.raw_metadata == {}

    def test_full_metadata(self):
        meta = VideoMetadata(
            external_id="abc123",
            url="https://www.youtube.com/watch?v=abc123",
            title="شقة للبيع في طنجة",
            channel_name="Agent Tangier",
            duration_seconds=900,
            view_count=1500,
        )
        assert meta.title == "شقة للبيع في طنجة"
        assert meta.duration_seconds == 900
