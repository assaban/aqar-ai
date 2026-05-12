"""
Aqar.ai: Whisper Model Loader
==============================
Singleton loader for the OpenAI Whisper model.

The model is loaded once on first use and cached for subsequent
transcription tasks. This avoids the overhead of loading a multi-GB
model for every Celery task.

Usage:
    model = get_whisper_model()
    result = model.transcribe(audio_path)
"""

from __future__ import annotations

import logging
import os
import time

import whisper

logger = logging.getLogger(__name__)

# Module-level cache
_model_instance: whisper.Whisper | None = None
_model_name: str | None = None

# Configuration from environment
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")


def get_whisper_model(
    model_name: str | None = None,
    device: str | None = None,
) -> whisper.Whisper:
    """
    Get or load the Whisper model (singleton).

    On first call, loads the model from disk/downloads it.
    Subsequent calls return the cached instance.

    Args:
        model_name: Whisper model size. Options: tiny, base, small, medium, large-v3.
                    Defaults to WHISPER_MODEL env var (default: "base").
        device: Device to load model on ("cpu" or "cuda").
                Defaults to WHISPER_DEVICE env var (default: "cpu").

    Returns:
        Loaded Whisper model instance.
    """
    global _model_instance, _model_name

    target_model = model_name or WHISPER_MODEL
    target_device = device or WHISPER_DEVICE

    # Return cached model if same configuration
    if _model_instance is not None and _model_name == target_model:
        return _model_instance

    logger.info(f"Loading Whisper model: {target_model} on {target_device}")
    start = time.time()

    _model_instance = whisper.load_model(target_model, device=target_device)
    _model_name = target_model

    elapsed = round(time.time() - start, 2)
    logger.info(f"Whisper model loaded in {elapsed}s: {target_model} on {target_device}")

    return _model_instance


def get_model_info() -> dict:
    """Return info about the currently loaded model."""
    return {
        "model_name": _model_name,
        "device": WHISPER_DEVICE,
        "loaded": _model_instance is not None,
    }


def unload_model() -> None:
    """Unload the cached model to free memory. Mainly for testing."""
    global _model_instance, _model_name
    _model_instance = None
    _model_name = None
    logger.info("Whisper model unloaded")
