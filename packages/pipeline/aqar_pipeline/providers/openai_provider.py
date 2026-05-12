"""
Aqar.ai: OpenAI Provider
==========================
LLM provider for OpenAI models (GPT-4o, GPT-4o-mini).
Secondary provider for high-accuracy extraction and benchmarking.
"""

from __future__ import annotations

import logging
import time

import httpx

from aqar_pipeline.providers.base import (
    ExtractionResult,
    LLMProvider,
)

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider.

    Uses the Chat Completions API with JSON response format.
    """

    def extract(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ExtractionResult:
        """Send extraction prompt to OpenAI and parse the response."""
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(
                    OPENAI_API_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            elapsed = round(time.time() - start_time, 2)

            # Token usage
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)

            # Parse JSON response
            parsed = self._parse_json_response(raw_text)
            if parsed is None:
                logger.warning(f"Failed to parse OpenAI response as JSON: {raw_text[:200]}")
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
                f"OpenAI extraction complete: {len(properties)} properties, "
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
            logger.error(f"OpenAI HTTP error: {e.response.status_code} - {error_body}")
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
            logger.error(f"OpenAI extraction error: {e}")
            return ExtractionResult(
                properties=[],
                model=self.config.model,
                provider=self.name,
                processing_time_seconds=elapsed,
                success=False,
                error_message=str(e),
            )

    def health_check(self) -> bool:
        """Check if the OpenAI API key is valid."""
        if not self.config.api_key:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
            }
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    "https://api.openai.com/v1/models",
                    headers=headers,
                )
                return response.status_code == 200
        except Exception:
            return False
