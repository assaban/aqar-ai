"""
Aqar.ai: Ollama Provider
==========================
LLM provider for locally-hosted models via Ollama.
Primary provider using Gemma 4 and Gemma 3.

Ollama REST API: POST /api/generate or /api/chat
Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import json
import logging
import time

import httpx

from aqar_pipeline.providers.base import (
    ExtractionResult,
    LLMProvider,
    ProviderConfig,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider for local model inference.

    Supports any model available in Ollama, with Gemma 3/4 as primary.
    Uses the /api/chat endpoint for structured conversation.
    """

    def extract(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ExtractionResult:
        """Send extraction prompt to Ollama and parse the response."""
        start_time = time.time()

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(
                    f"{self.config.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            raw_text = data.get("message", {}).get("content", "")
            elapsed = round(time.time() - start_time, 2)

            # Parse JSON response
            parsed = self._parse_json_response(raw_text)
            if parsed is None:
                logger.warning(f"Failed to parse Ollama response as JSON: {raw_text[:200]}")
                return ExtractionResult(
                    properties=[],
                    raw_response=raw_text,
                    model=self.config.model,
                    provider=self.name,
                    processing_time_seconds=elapsed,
                    success=False,
                    error_message="Failed to parse JSON response",
                )

            properties = parsed.get("properties", [])
            metadata = parsed.get("metadata", {})

            # Token usage from Ollama response
            tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            logger.info(
                f"Ollama extraction complete: {len(properties)} properties, "
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
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return ExtractionResult(
                properties=[],
                model=self.config.model,
                provider=self.name,
                processing_time_seconds=elapsed,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )

        except httpx.ConnectError:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"Cannot connect to Ollama at {self.config.base_url}")
            return ExtractionResult(
                properties=[],
                model=self.config.model,
                provider=self.name,
                processing_time_seconds=elapsed,
                success=False,
                error_message=f"Cannot connect to Ollama at {self.config.base_url}",
            )

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            logger.error(f"Ollama extraction error: {e}")
            return ExtractionResult(
                properties=[],
                model=self.config.model,
                provider=self.name,
                processing_time_seconds=elapsed,
                success=False,
                error_message=str(e),
            )

    def health_check(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.config.base_url}/api/tags")
                if response.status_code != 200:
                    return False

                models = response.json().get("models", [])
                available = [m.get("name", "") for m in models]

                # Check if our model (or a variant) is available
                model_base = self.config.model.split(":")[0]
                return any(model_base in m for m in available)

        except Exception:
            return False
