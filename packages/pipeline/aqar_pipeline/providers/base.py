"""
Aqar.ai: LLM Provider Base
============================
Abstract base class for LLM providers and shared data structures.

All providers implement the same interface, enabling the Strategy Pattern
for flexible switching between Ollama, OpenAI, and Anthropic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ProviderName(str, Enum):
    """Supported LLM provider names."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ExtractionResult:
    """Result from an LLM property extraction call."""

    properties: list[dict]
    metadata: dict = field(default_factory=dict)
    raw_response: str = ""
    model: str = ""
    provider: str = ""
    prompt_version: str = ""
    tokens_used: int = 0
    processing_time_seconds: float = 0.0
    success: bool = True
    error_message: str = ""


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    name: ProviderName
    model: str
    base_url: str = ""
    api_key: str = ""
    max_tokens: int = 4096
    temperature: float = 0.1
    timeout_seconds: int = 120


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider implements `extract()` which takes a system prompt,
    user prompt, and returns an ExtractionResult with parsed properties.

    Providers handle their own:
      - API communication (REST calls)
      - Response parsing (JSON extraction)
      - Error handling and retries
      - Token counting
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name.value

    @property
    def model(self) -> str:
        return self.config.model

    @abstractmethod
    def extract(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ExtractionResult:
        """
        Send a prompt to the LLM and return extracted property data.

        Args:
            system_prompt: System/context prompt with extraction instructions.
            user_prompt: User prompt containing the transcript text.

        Returns:
            ExtractionResult with parsed properties and metadata.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the provider is available and responding.

        Returns:
            True if the provider is healthy, False otherwise.
        """
        ...

    def _parse_json_response(self, text: str) -> dict | None:
        """
        Parse a JSON response from the LLM, handling common formatting issues.

        LLMs sometimes wrap JSON in markdown code blocks or add preamble text.
        This method extracts the JSON object regardless of formatting.
        """
        import json
        import re

        # Strip markdown code blocks
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return None
