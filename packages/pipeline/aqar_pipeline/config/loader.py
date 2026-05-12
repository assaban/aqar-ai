"""
Aqar.ai: Channel Configuration Loader
======================================
Reads and validates the channels.yml configuration file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ChannelConfig:
    """A single YouTube channel to monitor."""

    name: str
    channel_url: str
    description: str = ""
    max_videos: int = 20
    language_hint: str = "ar"
    tags: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class DiscoveryConfig:
    """Full discovery configuration from channels.yml."""

    region: str
    channels: list[ChannelConfig]
    defaults: dict = field(default_factory=dict)


def load_channels_config(config_path: str | None = None) -> DiscoveryConfig:
    """
    Load channel configuration from YAML file.

    Args:
        config_path: Path to channels.yml. If None, uses the default
                     location relative to this package.

    Returns:
        DiscoveryConfig with all enabled channels.
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "channels.yml")

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Channel config not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw or "channels" not in raw:
        raise ValueError(f"Invalid channel config: missing 'channels' key in {path}")

    defaults = raw.get("defaults", {})
    default_max_videos = defaults.get("max_videos", 20)
    default_language = defaults.get("language_hint", "ar")
    default_enabled = defaults.get("enabled", True)

    channels = []
    for entry in raw["channels"]:
        if not entry.get("channel_url"):
            continue

        channel = ChannelConfig(
            name=entry.get("name", "Unknown"),
            channel_url=entry["channel_url"],
            description=entry.get("description", ""),
            max_videos=entry.get("max_videos", default_max_videos),
            language_hint=entry.get("language_hint", default_language),
            tags=entry.get("tags", []),
            enabled=entry.get("enabled", default_enabled),
        )
        channels.append(channel)

    # Filter to enabled channels only
    enabled_channels = [c for c in channels if c.enabled]

    return DiscoveryConfig(
        region=raw.get("region", "tangier-tetouan"),
        channels=enabled_channels,
        defaults=defaults,
    )
