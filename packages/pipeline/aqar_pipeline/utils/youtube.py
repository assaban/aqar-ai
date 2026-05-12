"""
Aqar.ai: YouTube Utilities
==========================
Wrapper around yt-dlp for metadata extraction and video discovery.
Handles channel scanning, video info extraction, and URL normalization.
"""

from __future__ import annotations

import logging
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


def _build_ydl_opts(quiet: bool = True) -> dict:
    """Build yt-dlp options for metadata extraction (no download)."""
    return {
        "quiet": quiet,
        "no_warnings": quiet,
        "extract_flat": False,
        "skip_download": True,
        "ignoreerrors": True,
        "no_color": True,
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

                results.append(VideoMetadata(
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
                        k: v for k, v in entry.items()
                        if k in ("id", "title", "duration", "upload_date", "view_count",
                                 "like_count", "channel_id", "channel", "thumbnail",
                                 "categories", "tags", "description")
                    },
                ))

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
                    k: v for k, v in info.items()
                    if k in ("id", "title", "duration", "upload_date", "view_count",
                             "like_count", "channel_id", "channel", "thumbnail",
                             "categories", "tags", "description", "uploader",
                             "uploader_id", "webpage_url")
                },
            )

    except Exception as e:
        logger.error(f"Error fetching video metadata for {video_url}: {e}")
        return None
