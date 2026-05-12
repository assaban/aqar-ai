"""
Aqar.ai: Audio Utilities
=========================
File path management, WAV validation, and cleanup for audio files.
"""

from __future__ import annotations

import logging
import os
import wave
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Default download directory (configurable via env)
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "/tmp/aqar/downloads")

# Whisper-optimal audio settings
TARGET_SAMPLE_RATE = 16000  # 16kHz
TARGET_CHANNELS = 1         # Mono


@dataclass
class AudioInfo:
    """Information about an audio file."""

    path: str
    sample_rate: int
    channels: int
    duration_seconds: float
    file_size_bytes: int


def get_audio_path(external_id: str, download_dir: str | None = None) -> str:
    """
    Generate the expected audio file path for a given video ID.

    Args:
        external_id: YouTube video ID (e.g. "dQw4w9WgXcQ").
        download_dir: Override download directory. Uses DOWNLOAD_PATH if None.

    Returns:
        Full path to the WAV file.
    """
    base_dir = download_dir or DOWNLOAD_PATH
    return os.path.join(base_dir, f"{external_id}.wav")


def ensure_download_dir(download_dir: str | None = None) -> str:
    """
    Create the download directory if it does not exist.

    Returns:
        The directory path.
    """
    base_dir = download_dir or DOWNLOAD_PATH
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def validate_wav_file(file_path: str) -> AudioInfo | None:
    """
    Validate that a file is a proper WAV and return its properties.

    Args:
        file_path: Path to the WAV file.

    Returns:
        AudioInfo if valid, None if the file is missing or corrupted.
    """
    if not os.path.exists(file_path):
        logger.warning(f"Audio file not found: {file_path}")
        return None

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        logger.warning(f"Audio file is empty: {file_path}")
        return None

    try:
        with wave.open(file_path, "rb") as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            frames = wf.getnframes()
            duration = frames / sample_rate if sample_rate > 0 else 0.0

            return AudioInfo(
                path=file_path,
                sample_rate=sample_rate,
                channels=channels,
                duration_seconds=round(duration, 2),
                file_size_bytes=file_size,
            )
    except wave.Error as e:
        logger.error(f"Invalid WAV file {file_path}: {e}")
        return None


def cleanup_audio_file(file_path: str) -> bool:
    """
    Delete an audio file after successful transcription.

    Args:
        file_path: Path to the audio file to delete.

    Returns:
        True if deleted successfully, False otherwise.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up audio file: {file_path}")
            return True
        else:
            logger.debug(f"Audio file already removed: {file_path}")
            return True
    except OSError as e:
        logger.error(f"Failed to cleanup audio file {file_path}: {e}")
        return False


def get_download_dir_stats(download_dir: str | None = None) -> dict:
    """
    Get statistics about the download directory.
    Useful for monitoring disk usage.

    Returns:
        Dict with file_count, total_size_mb.
    """
    base_dir = download_dir or DOWNLOAD_PATH

    if not os.path.exists(base_dir):
        return {"file_count": 0, "total_size_mb": 0.0}

    files = list(Path(base_dir).glob("*.wav"))
    total_size = sum(f.stat().st_size for f in files)

    return {
        "file_count": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }
