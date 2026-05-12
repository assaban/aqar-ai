"""
Aqar.ai: Anthropic Provider
=============================
LLM provider for Anthropic Claude models.
Tertiary provider leveraging Claude's Arabic language strengths.
"""

from __future__ import annotations

import logging
import time

import httpx

from aqar_pipeline.providers.base import (
    ExtractionResult,
    LLMProvider,
    ProviderConfig,
)

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude LLM provider.

    Uses the Messages API with system prompt support.
    """

    def extract(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ExtractionResult:
        """Send extraction prompt to Claude and parse the response."""
        start_time = time.time()

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(
                    ANTHROPIC_API_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()

            # Extract text from content blocks
            raw_text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    raw_text += block.get("text", "")

            elapsed = round(time.time() - start_time, 2)

            # Token usage
            usage = data.get("usage", {})
            tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            # Parse JSON response
            parsed = self._parse_json_response(raw_text)
            if parsed is None:
                logger.warning(f"Failed to parse Anthropic response as JSON: {raw_text[:200]}")
                return ExtractionResult(
                    properties=[],
                    raw_response=raw_text,
                    model=self.config.model,
                    provider=self.name,
                    tokens_used=tokens_used,
                    processing_time_seconds=elapsed,
                    success=False,
                    error_message="Failed to parse JSON response",
                )

            properties = parsed.get("properties", [])
            metadata = parsed.get("metadata", {})

            logger.info(
                f"Anthropic extraction complete: {len(properties)} properties, "
                f"{tokens_used} tokens, {elapsed}s"
            )

            return ExtractionResult(
                properties=properties,
                metadata=metadata,
                raw_response=raw_text,
                model=self.config.model,
                provider=self.name,
                tokens_used=tokens_used,
                processing_time_seconds=elapsed,
                success=True,
            )

        except httpx.HTTPStatusError as e:
            elapsed = round(time.time() - start_time, 2)
            error_body = e.response.text[:300]
            logger.error(f"Anthropic HTTP error: {e.response.status_code} - {error_body}")
            return ExtractionResult(
                properties=[],
                model=self.config.model,
                provider=self.name,
                processing_time_seconds=elapsed,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {error_body}",
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"Anthropic extraction error: {e}")
            return ExtractionResult(
                properties=[],
                model=self.config.model,
                provider=self.name,
                processing_time_seconds=elapsed,
                success=False,
                error_message=str(e),
            )

    def health_check(self) -> bool:
        """Check if the Anthropic API key is configured."""
        return bool(self.config.api_key)
