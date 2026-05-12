"""
Unit tests for the audio extraction stage.

Tests cover: audio path generation, WAV validation, cleanup logic,
download directory management, and yt-dlp option building.
"""

import os
import tempfile
import wave

from aqar_pipeline.utils.audio import (
    cleanup_audio_file,
    ensure_download_dir,
    get_audio_path,
    get_download_dir_stats,
    validate_wav_file,
)

# ═══════════════════════════════════════
# Audio Path Generation
# ═══════════════════════════════════════


class TestGetAudioPath:
    """Tests for get_audio_path()."""

    def test_generates_correct_path(self):
        path = get_audio_path("dQw4w9WgXcQ", "/tmp/test")
        assert path == "/tmp/test/dQw4w9WgXcQ.wav"

    def test_uses_default_download_path(self):
        path = get_audio_path("abc123")
        assert path.endswith("abc123.wav")
        assert "downloads" in path

    def test_handles_special_characters_in_id(self):
        path = get_audio_path("a-b_c123DEF", "/tmp/test")
        assert path == "/tmp/test/a-b_c123DEF.wav"


# ═══════════════════════════════════════
# Download Directory
# ═══════════════════════════════════════


class TestEnsureDownloadDir:
    """Tests for ensure_download_dir()."""

    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "audio", "downloads")
            result = ensure_download_dir(new_dir)
            assert os.path.isdir(result)
            assert result == new_dir

    def test_existing_directory_is_fine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ensure_download_dir(tmpdir)
            assert os.path.isdir(result)


# ═══════════════════════════════════════
# WAV Validation
# ═══════════════════════════════════════


def _create_test_wav(path: str, sample_rate: int = 16000, channels: int = 1, duration_s: float = 1.0):
    """Helper: create a minimal valid WAV file."""
    n_frames = int(sample_rate * duration_s)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Write silence (zero samples)
        wf.writeframes(b"\x00\x00" * n_frames * channels)


class TestValidateWavFile:
    """Tests for validate_wav_file()."""

    def test_valid_wav_file(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name, sample_rate=16000, channels=1, duration_s=2.0)
            info = validate_wav_file(f.name)

            assert info is not None
            assert info.sample_rate == 16000
            assert info.channels == 1
            assert 1.9 <= info.duration_seconds <= 2.1
            assert info.file_size_bytes > 0
            os.unlink(f.name)

    def test_stereo_wav(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            _create_test_wav(f.name, sample_rate=44100, channels=2, duration_s=1.0)
            info = validate_wav_file(f.name)

            assert info is not None
            assert info.channels == 2
            assert info.sample_rate == 44100
            os.unlink(f.name)

    def test_missing_file_returns_none(self):
        info = validate_wav_file("/nonexistent/file.wav")
        assert info is None

    def test_empty_file_returns_none(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            pass  # Empty file
        info = validate_wav_file(f.name)
        assert info is None
        os.unlink(f.name)

    def test_non_wav_file_returns_none(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, mode="w") as f:
            f.write("this is not a wav file")
        info = validate_wav_file(f.name)
        assert info is None
        os.unlink(f.name)


# ═══════════════════════════════════════
# Audio Cleanup
# ═══════════════════════════════════════


class TestCleanupAudioFile:
    """Tests for cleanup_audio_file()."""

    def test_deletes_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"test")
        assert os.path.exists(f.name)
        result = cleanup_audio_file(f.name)
        assert result is True
        assert not os.path.exists(f.name)

    def test_nonexistent_file_returns_true(self):
        result = cleanup_audio_file("/nonexistent/file.wav")
        assert result is True

    def test_handles_already_deleted(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            path = f.name
        # File already deleted by context manager
        result = cleanup_audio_file(path)
        assert result is True


# ═══════════════════════════════════════
# Download Dir Stats
# ═══════════════════════════════════════


class TestGetDownloadDirStats:
    """Tests for get_download_dir_stats()."""

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stats = get_download_dir_stats(tmpdir)
            assert stats["file_count"] == 0
            assert stats["total_size_mb"] == 0.0

    def test_directory_with_wav_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_test_wav(os.path.join(tmpdir, "test1.wav"), duration_s=1.0)
            _create_test_wav(os.path.join(tmpdir, "test2.wav"), duration_s=2.0)

            stats = get_download_dir_stats(tmpdir)
            assert stats["file_count"] == 2
            assert stats["total_size_mb"] > 0

    def test_nonexistent_directory(self):
        stats = get_download_dir_stats("/nonexistent/dir")
        assert stats["file_count"] == 0

    def test_ignores_non_wav_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_test_wav(os.path.join(tmpdir, "audio.wav"), duration_s=1.0)
            with open(os.path.join(tmpdir, "notes.txt"), "w") as f:
                f.write("not audio")

            stats = get_download_dir_stats(tmpdir)
            assert stats["file_count"] == 1  # Only the .wav
