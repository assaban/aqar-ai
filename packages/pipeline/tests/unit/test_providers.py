"""
Unit tests for LLM providers.

Tests cover: provider interface, registry factory, response parsing,
configuration, and provider listing.
"""

import json

import pytest

from aqar_pipeline.providers import get_provider, list_providers
from aqar_pipeline.providers.base import (
    ExtractionResult,
    LLMProvider,
    ProviderConfig,
    ProviderName,
)


# ═══════════════════════════════════════
# Provider Registry
# ═══════════════════════════════════════


class TestProviderRegistry:
    """Tests for the provider factory."""

    def test_get_ollama_provider(self):
        provider = get_provider("ollama")
        assert provider.name == "ollama"
        assert isinstance(provider, LLMProvider)

    def test_get_openai_provider(self):
        provider = get_provider("openai")
        assert provider.name == "openai"
        assert isinstance(provider, LLMProvider)

    def test_get_anthropic_provider(self):
        provider = get_provider("anthropic")
        assert provider.name == "anthropic"
        assert isinstance(provider, LLMProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")

    def test_case_insensitive(self):
        provider = get_provider("OLLAMA")
        assert provider.name == "ollama"

    def test_model_override(self):
        provider = get_provider("ollama", model="gemma3:27b")
        assert provider.model == "gemma3:27b"

    def test_list_providers(self):
        providers = list_providers()
        assert len(providers) == 3
        names = [p["name"] for p in providers]
        assert "ollama" in names
        assert "openai" in names
        assert "anthropic" in names


# ═══════════════════════════════════════
# ExtractionResult
# ═══════════════════════════════════════


class TestExtractionResult:
    """Tests for the ExtractionResult dataclass."""

    def test_default_values(self):
        result = ExtractionResult(properties=[])
        assert result.success is True
        assert result.tokens_used == 0
        assert result.error_message == ""

    def test_failed_result(self):
        result = ExtractionResult(
            properties=[],
            success=False,
            error_message="Connection refused",
        )
        assert result.success is False
        assert result.error_message == "Connection refused"

    def test_with_properties(self):
        result = ExtractionResult(
            properties=[
                {"property_type": "apartment", "price": 500000},
                {"property_type": "house", "price": 1200000},
            ],
            model="gemma3",
            provider="ollama",
            tokens_used=1500,
        )
        assert len(result.properties) == 2
        assert result.tokens_used == 1500


# ═══════════════════════════════════════
# JSON Response Parsing
# ═══════════════════════════════════════


class TestJsonParsing:
    """Tests for the _parse_json_response method on LLMProvider."""

    def _get_parser(self):
        """Create a concrete provider to test the base class parsing method."""
        provider = get_provider("ollama")
        return provider

    def test_parses_clean_json(self):
        parser = self._get_parser()
        result = parser._parse_json_response('{"properties": [{"price": 100}]}')
        assert result is not None
        assert result["properties"][0]["price"] == 100

    def test_parses_json_in_code_block(self):
        parser = self._get_parser()
        text = '```json\n{"properties": []}\n```'
        result = parser._parse_json_response(text)
        assert result is not None
        assert result["properties"] == []

    def test_parses_json_with_preamble(self):
        parser = self._get_parser()
        text = 'Here is the extracted data:\n{"properties": [{"type": "villa"}]}'
        result = parser._parse_json_response(text)
        assert result is not None
        assert len(result["properties"]) == 1

    def test_returns_none_for_invalid(self):
        parser = self._get_parser()
        result = parser._parse_json_response("This is not JSON at all")
        assert result is None

    def test_returns_none_for_empty(self):
        parser = self._get_parser()
        result = parser._parse_json_response("")
        assert result is None

    def test_handles_nested_json(self):
        parser = self._get_parser()
        data = {
            "properties": [
                {
                    "property_type": "apartment",
                    "confidence_scores": {"price": 0.95, "overall": 0.8},
                }
            ],
            "metadata": {"language": "ar"},
        }
        result = parser._parse_json_response(json.dumps(data))
        assert result is not None
        assert result["properties"][0]["confidence_scores"]["overall"] == 0.8


# ═══════════════════════════════════════
# Provider Configuration
# ═══════════════════════════════════════


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_defaults(self):
        config = ProviderConfig(name=ProviderName.OLLAMA, model="gemma3")
        assert config.max_tokens == 4096
        assert config.temperature == 0.1
        assert config.timeout_seconds == 120

    def test_custom_config(self):
        config = ProviderConfig(
            name=ProviderName.OPENAI,
            model="gpt-4o",
            api_key="sk-test",
            temperature=0.0,
            max_tokens=8192,
        )
        assert config.api_key == "sk-test"
        assert config.max_tokens == 8192
