"""
Aqar.ai: Prompt Loader
========================
Loads versioned extraction prompts from the prompts/ directory.

Prompts are Python modules with SYSTEM_PROMPT and USER_PROMPT_TEMPLATE
variables. The version is derived from the filename.
"""

from __future__ import annotations

import importlib
import logging
import os
import re

logger = logging.getLogger(__name__)

# Cache loaded prompts
_prompt_cache: dict[str, dict] = {}


def get_prompt(version: str = "v1") -> dict:
    """
    Load a versioned prompt template.

    Args:
        version: Prompt version string (e.g. "v1", "v2").

    Returns:
        Dict with "system_prompt", "user_prompt_template", and "version".
    """
    if version in _prompt_cache:
        return _prompt_cache[version]

    module_name = f"prompts.property_extraction_{version}"

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        logger.error(f"Prompt module not found: {module_name}")
        raise FileNotFoundError(f"Prompt version not found: {version}")

    system_prompt = getattr(module, "SYSTEM_PROMPT", "")
    user_template = getattr(module, "USER_PROMPT_TEMPLATE", "")

    if not system_prompt or not user_template:
        raise ValueError(
            f"Prompt module {module_name} must define SYSTEM_PROMPT and USER_PROMPT_TEMPLATE"
        )

    prompt_data = {
        "system_prompt": system_prompt.strip(),
        "user_prompt_template": user_template.strip(),
        "version": version,
    }

    _prompt_cache[version] = prompt_data
    logger.info(f"Loaded prompt version: {version}")

    return prompt_data


def render_prompt(transcript_text: str, version: str = "v1") -> tuple[str, str]:
    """
    Load and render a prompt with the transcript text.

    Args:
        transcript_text: The transcription to include in the user prompt.
        version: Prompt version to use.

    Returns:
        Tuple of (system_prompt, rendered_user_prompt).
    """
    prompt = get_prompt(version)
    user_prompt = prompt["user_prompt_template"].format(
        transcript_text=transcript_text,
    )
    return prompt["system_prompt"], user_prompt


def list_prompt_versions() -> list[str]:
    """List all available prompt versions by scanning the prompts/ directory."""
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")
    prompts_dir = os.path.normpath(prompts_dir)

    if not os.path.isdir(prompts_dir):
        return []

    versions = []
    for filename in sorted(os.listdir(prompts_dir)):
        match = re.match(r"property_extraction_(v\d+)\.py", filename)
        if match:
            versions.append(match.group(1))

    return versions
