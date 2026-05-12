"""
Aqar.ai: LLM Provider Registry
================================
Factory for creating LLM provider instances from configuration.

Usage:
    provider = get_provider()  # uses LLM_PROVIDER env var
    provider = get_provider("openai")  # explicit override
    result = provider.extract(system_prompt, user_prompt)
"""

from __future__ import annotations

import logging
import os

from aqar_pipeline.providers.base import LLMProvider, ProviderConfig, ProviderName

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

_ENV_CONFIG = {
    ProviderName.OLLAMA: {
        "model": os.getenv("OLLAMA_MODEL", "gemma3"),
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
    },
    ProviderName.OPENAI: {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
    },
    ProviderName.ANTHROPIC: {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    },
}


def get_provider(
    provider_name: str | None = None,
    model: str | None = None,
) -> LLMProvider:
    """
    Create an LLM provider instance.

    Args:
        provider_name: Provider to use ("ollama", "openai", "anthropic").
                       Defaults to LLM_PROVIDER env var.
        model: Override the default model for this provider.

    Returns:
        Configured LLMProvider instance.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    name = provider_name or DEFAULT_PROVIDER

    try:
        provider_enum = ProviderName(name.lower())
    except ValueError as exc:
        raise ValueError(
            f"Unknown provider: '{name}'. Supported: {[p.value for p in ProviderName]}"
        ) from exc

    env_config = _ENV_CONFIG[provider_enum]
    config = ProviderConfig(
        name=provider_enum,
        model=model or env_config.get("model", ""),
        base_url=env_config.get("base_url", ""),
        api_key=env_config.get("api_key", ""),
    )

    if provider_enum == ProviderName.OLLAMA:
        from aqar_pipeline.providers.ollama_provider import OllamaProvider

        return OllamaProvider(config)

    if provider_enum == ProviderName.OPENAI:
        from aqar_pipeline.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(config)

    if provider_enum == ProviderName.ANTHROPIC:
        from aqar_pipeline.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(config)

    raise ValueError(f"Provider not implemented: {name}")


def list_providers() -> list[dict]:
    """List all available providers with their configuration status."""
    providers = []
    for provider_enum in ProviderName:
        env = _ENV_CONFIG[provider_enum]
        configured = bool(env.get("api_key") or provider_enum == ProviderName.OLLAMA)
        providers.append(
            {
                "name": provider_enum.value,
                "model": env.get("model", ""),
                "configured": configured,
                "is_default": provider_enum.value == DEFAULT_PROVIDER,
            }
        )
    return providers
