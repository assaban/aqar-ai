"""
Aqar.ai: YouTube Utilities
==========================
Wrapper around yt-dlp for metadata extraction and video discovery.
Handles channel scanning, video info extraction, and URL normalization.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import yt_dlp

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """Structured metadata extracted from a YouTube video."""

    external_id: str
    url: str
    title: str
    description: str = ""
    channel_id: str = ""
    channel_name: str = ""
    duration_seconds: int = 0
    published_at: datetime | None = None
    thumbnail_url: str = ""
    view_count: int = 0
    raw_metadata: dict = field(default_factory=dict)


def extract_youtube_id(url: str) -> str | None:
    """
    Extract the 11-character YouTube video ID from various URL formats.

    Supports:
      - youtube.com/watch?v=ID
      - youtu.be/ID
      - youtube.com/embed/ID
      - youtube.com/shorts/ID

    Returns None if no valid ID is found.
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def normalize_youtube_url(video_id: str) -> str:
    """Return the canonical YouTube URL for a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"


def _parse_upload_date(date_str: str | None) -> datetime | None:
    """Parse yt-dlp upload_date (YYYYMMDD format) to datetime."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=UTC)
    except ValueError:
        return None


# Update _build_ydl_opts to include safety delays
# packages/aqar_pipeline/utils/youtube.py
def _build_ydl_opts(quiet: bool = True) -> dict:
    """Build yt-dlp options with rate-limit protection."""
    return {
        "quiet": quiet,
        "no_warnings": quiet,
        "extract_flat": False,
        "skip_download": True,
        "ignoreerrors": True,
        "no_color": True,
        # ── ADD THESE TO AVOID RATE LIMITING ──
        "sleep_interval": 5,  # Sleep 5s between requests
        "max_sleep_interval": 15,  # Randomize sleep up to 15s
        "sleep_interval_requests": 1,  # Sleep after every single request
    }


def fetch_channel_videos(
    channel_url: str,
    max_videos: int = 20,
) -> list[VideoMetadata]:
    """
    Fetch recent video metadata from a YouTube channel.

    Uses yt-dlp to extract video listings from the channel's videos tab.
    Does not download any video/audio content.

    Args:
        channel_url: YouTube channel URL (e.g. https://www.youtube.com/@handle)
        max_videos: Maximum number of videos to retrieve.

    Returns:
        List of VideoMetadata objects, newest first.
    """
    # Ensure we hit the /videos tab
    videos_url = channel_url.rstrip("/")
    if not videos_url.endswith("/videos"):
        videos_url += "/videos"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,  # Flat extraction for channel listings
        "skip_download": True,
        "ignoreerrors": True,
        "no_color": True,
        "playlistend": max_videos,
    }

    results = []

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(videos_url, download=False)

            if not info:
                logger.warning(f"No info returned for channel: {channel_url}")
                return []

            entries = info.get("entries", [])
            if not entries:
                logger.info(f"No videos found for channel: {channel_url}")
                return []

            for entry in entries:
                if entry is None:
                    continue

                video_id = entry.get("id", "")
                if not video_id:
                    continue

                results.append(
                    VideoMetadata(
                        external_id=video_id,
                        url=normalize_youtube_url(video_id),
                        title=entry.get("title", ""),
                        description=entry.get("description", ""),
                        channel_id=info.get("channel_id", entry.get("channel_id", "")),
                        channel_name=info.get("channel", entry.get("channel", "")),
                        duration_seconds=entry.get("duration") or 0,
                        published_at=_parse_upload_date(entry.get("upload_date")),
                        thumbnail_url=entry.get("thumbnail", ""),
                        view_count=entry.get("view_count") or 0,
                        raw_metadata={
                            k: v
                            for k, v in entry.items()
                            if k
                            in (
                                "id",
                                "title",
                                "duration",
                                "upload_date",
                                "view_count",
                                "like_count",
                                "channel_id",
                                "channel",
                                "thumbnail",
                                "categories",
                                "tags",
                                "description",
                            )
                        },
                    )
                )

    except Exception as e:
        logger.error(f"Error fetching channel {channel_url}: {e}")
        return []

    logger.info(f"Fetched {len(results)} videos from {channel_url}")
    return results


def fetch_video_metadata(video_url: str) -> VideoMetadata | None:
    """
    Fetch full metadata for a single YouTube video.

    Used when a video URL is submitted manually via the API.

    Args:
        video_url: YouTube video URL.

    Returns:
        VideoMetadata object or None if extraction fails.
    """
    opts = _build_ydl_opts()

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            if not info:
                logger.warning(f"No info returned for video: {video_url}")
                return None

            video_id = info.get("id", "")
            if not video_id:
                return None

            return VideoMetadata(
                external_id=video_id,
                url=normalize_youtube_url(video_id),
                title=info.get("title", ""),
                description=info.get("description", ""),
                channel_id=info.get("channel_id", ""),
                channel_name=info.get("channel", info.get("uploader", "")),
                duration_seconds=info.get("duration") or 0,
                published_at=_parse_upload_date(info.get("upload_date")),
                thumbnail_url=info.get("thumbnail", ""),
                view_count=info.get("view_count") or 0,
                raw_metadata={
                    k: v
                    for k, v in info.items()
                    if k
                    in (
                        "id",
                        "title",
                        "duration",
                        "upload_date",
                        "view_count",
                        "like_count",
                        "channel_id",
                        "channel",
                        "thumbnail",
                        "categories",
                        "tags",
                        "description",
                        "uploader",
                        "uploader_id",
                        "webpage_url",
                    )
                },
            )

    except Exception as e:
        logger.error(f"Error fetching video metadata for {video_url}: {e}")
        return None


def download_audio(
    video_url: str,
    output_path: str,
    sample_rate: int = 16000,
) -> bool:
    """
    Download audio from a YouTube video and convert to WAV.

    Uses yt-dlp to extract the best audio stream, then FFmpeg
    to convert to WAV format (16kHz mono) optimized for Whisper.

    Args:
        video_url: YouTube video URL.
        output_path: Full path for the output WAV file (without extension,
                     yt-dlp will add it, or with .wav which we handle).
        sample_rate: Target sample rate in Hz (default 16000 for Whisper).

    Returns:
        True if download and conversion succeeded, False otherwise.
    """
    # yt-dlp expects output template without extension for postprocessor
    # Remove .wav if present since FFmpeg postprocessor adds it
    output_template = output_path
    if output_template.endswith(".wav"):
        output_template = output_template[:-4]

    opts = {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "format": "bestaudio/best",
        "outtmpl": output_template + ".%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
        "postprocessor_args": {
            "FFmpegExtractAudio": [
                "-ar",
                str(sample_rate),
                "-ac",
                "1",  # mono
            ],
        },
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.download([video_url])

            if result != 0:
                logger.error(f"yt-dlp returned non-zero exit code: {result}")
                return False

        # Verify the output file exists
        expected_path = output_template + ".wav"
        if not os.path.exists(expected_path):
            logger.error(f"Expected output not found: {expected_path}")
            return False

        file_size = os.path.getsize(expected_path)
        logger.info(f"Audio downloaded: {expected_path} ({file_size / (1024 * 1024):.1f} MB)")
        return True

    except Exception as e:
        logger.error(f"Error downloading audio from {video_url}: {e}")
        return False


@dataclass
class SubtitleData:
    """Subtitles/captions fetched from YouTube."""

    text: str
    language: str
    source: str  # "manual" or "auto_generated"
    segments: list[dict] = field(default_factory=list)


def fetch_subtitles(
    video_url: str,
    preferred_languages: list[str] | None = None,
) -> SubtitleData | None:
    """
    Fetch subtitles/captions from a YouTube video.

    Checks for manual subtitles first, then auto-generated.
    This can be used instead of (or alongside) Whisper transcription.

    Args:
        video_url: YouTube video URL.
        preferred_languages: Language codes in order of preference.
                            Defaults to ["ar", "fr", "en"].

    Returns:
        SubtitleData if subtitles are available, None otherwise.
    """
    langs = preferred_languages or ["ar", "fr", "en"]

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": langs,
        "subtitlesformat": "json3",
        "no_color": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            if not info:
                return None

            # Check for manual subtitles first (higher quality)
            manual_subs = info.get("subtitles", {})
            auto_subs = info.get("automatic_captions", {})

            # Try manual subtitles in preferred language order
            for lang in langs:
                if lang in manual_subs and manual_subs[lang]:
                    sub_info = manual_subs[lang]
                    text, segments = _extract_subtitle_text(
                        sub_info, ydl, video_url, lang, "subtitles"
                    )
                    if text:
                        logger.info(f"Found manual subtitles ({lang}) for {video_url}")
                        return SubtitleData(
                            text=text,
                            language=lang,
                            source="manual",
                            segments=segments,
                        )

            # Fall back to auto-generated subtitles
            for lang in langs:
                if lang in auto_subs and auto_subs[lang]:
                    sub_info = auto_subs[lang]
                    text, segments = _extract_subtitle_text(
                        sub_info, ydl, video_url, lang, "automatic_captions"
                    )
                    if text:
                        logger.info(f"Found auto-generated subtitles ({lang}) for {video_url}")
                        return SubtitleData(
                            text=text,
                            language=lang,
                            source="auto_generated",
                            segments=segments,
                        )

            logger.info(f"No subtitles found for {video_url}")
            return None

    except Exception as e:
        logger.error(f"Error fetching subtitles for {video_url}: {e}")
        return None


def _extract_subtitle_text(
    sub_formats: list[dict],
    ydl: yt_dlp.YoutubeDL,
    video_url: str,
    lang: str,
    sub_type: str,
) -> tuple[str, list[dict]]:
    """
    Extract plain text and segments from subtitle format list.

    yt-dlp provides subtitle info as a list of available formats.
    We download the json3 or srv3 format and parse it.
    """

    # Find json3 format (structured with timestamps)
    json3_format = None
    for fmt in sub_formats:
        if fmt.get("ext") == "json3":
            json3_format = fmt
            break

    if json3_format and json3_format.get("url"):
        try:
            import httpx

            response = httpx.get(json3_format["url"], timeout=15)
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                segments = []
                texts = []

                for event in events:
                    segs = event.get("segs", [])
                    text = "".join(s.get("utf8", "") for s in segs).strip()
                    if text and text != "\n":
                        start_ms = event.get("tStartMs", 0)
                        dur_ms = event.get("dDurationMs", 0)
                        segments.append(
                            {
                                "start": round(start_ms / 1000, 2),
                                "end": round((start_ms + dur_ms) / 1000, 2),
                                "text": text,
                            }
                        )
                        texts.append(text)

                full_text = " ".join(texts)
                return full_text, segments
        except Exception as e:
            logger.debug(f"Failed to parse json3 subtitles: {e}")

    # Fallback: try to get any text format
    for fmt in sub_formats:
        if fmt.get("ext") in ("srv3", "vtt", "srt") and fmt.get("url"):
            try:
                import httpx

                response = httpx.get(fmt["url"], timeout=15)
                if response.status_code == 200:
                    # Basic text extraction (strip timing info)
                    raw = response.text
                    lines = [
                        line.strip()
                        for line in raw.split("\n")
                        if line.strip()
                        and not line.strip().startswith("WEBVTT")
                        and "-->" not in line
                        and not line.strip().isdigit()
                    ]
                    return " ".join(lines), []
            except Exception as e:
                logger.debug(f"Failed to fetch {fmt['ext']} subtitles: {e}")

    return "", []


def get_available_subtitle_languages(video_url: str) -> dict:
    """
    Check which subtitle languages are available for a video.

    Returns:
        Dict with "manual" and "auto_generated" keys, each containing
        a list of available language codes.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "listsubtitles": False,
        "no_color": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if not info:
                return {"manual": [], "auto_generated": []}

            manual = list(info.get("subtitles", {}).keys())
            auto = list(info.get("automatic_captions", {}).keys())

            return {"manual": manual, "auto_generated": auto}

    except Exception as e:
        logger.error(f"Error checking subtitles for {video_url}: {e}")
        return {"manual": [], "auto_generated": []}
