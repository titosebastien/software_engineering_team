"""
Ollama LLM client implementation.

This module provides integration with Ollama for local LLM inference.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx

from llm.base import BaseLLM, LLMConfig, LLMException


logger = logging.getLogger(__name__)


class OllamaClient(BaseLLM):
    """
    Ollama LLM client for local model inference.

    This client communicates with a running Ollama instance to generate responses
    using open-source models like Qwen, DeepSeek, Mistral, etc.
    """

    def __init__(
        self,
        config: LLMConfig,
        host: str = "http://localhost:11434"
    ):
        """
        Initialize Ollama client.

        Args:
            config: LLM configuration with model name and parameters
            host: Ollama server URL
        """
        self.config = config
        self.host = host.rstrip('/')
        self.api_url = f"{self.host}/api/generate"
        self.chat_url = f"{self.host}/api/chat"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate a response from Ollama.

        Args:
            system_prompt: System-level instructions
            user_prompt: User's request
            temperature: Generation randomness (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama parameters

        Returns:
            Generated text response

        Raises:
            LLMException: If generation fails
        """
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        # Add max tokens if specified
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        # Add any extra options
        payload["options"].update(kwargs)

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                logger.debug(f"Calling Ollama with model: {self.config.model}")

                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()

                result = response.json()
                generated_text = result.get("response", "")

                logger.debug(f"Ollama response length: {len(generated_text)} chars")

                return generated_text

        except httpx.HTTPStatusError as e:
            error_msg = f"Ollama HTTP error: {e.response.status_code}"
            logger.error(error_msg)
            raise LLMException(
                error_msg,
                error_type="http_error",
                details={"status_code": e.response.status_code}
            )

        except httpx.TimeoutException:
            error_msg = f"Ollama request timeout after {self.config.timeout}s"
            logger.error(error_msg)
            raise LLMException(
                error_msg,
                error_type="timeout_error"
            )

        except httpx.RequestError as e:
            error_msg = f"Ollama connection error: {str(e)}"
            logger.error(error_msg)
            raise LLMException(
                error_msg,
                error_type="connection_error",
                details={"error": str(e)}
            )

        except Exception as e:
            error_msg = f"Unexpected Ollama error: {str(e)}"
            logger.error(error_msg)
            raise LLMException(
                error_msg,
                error_type="unknown_error",
                details={"error": str(e)}
            )

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response.

        This adds instructions to the prompt to generate valid JSON matching the schema.

        Args:
            system_prompt: System instructions
            user_prompt: User request
            schema: JSON schema for response
            temperature: Generation randomness
            **kwargs: Additional parameters

        Returns:
            Parsed JSON response

        Raises:
            LLMException: If generation fails or JSON is invalid
        """
        # Add JSON formatting instructions
        structured_prompt = f"""
{user_prompt}

IMPORTANT: You must respond with ONLY valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Do not include any explanation or text outside the JSON object.
"""

        response_text = await self.generate(
            system_prompt,
            structured_prompt,
            temperature=temperature,
            **kwargs
        )

        # Try to extract and parse JSON from response
        try:
            # Remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # Parse JSON
            result = json.loads(cleaned)

            logger.debug("Successfully parsed structured response")

            return result

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse LLM response as JSON: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Response text: {response_text}")

            raise LLMException(
                error_msg,
                error_type="json_parse_error",
                details={"response": response_text, "error": str(e)}
            )

    async def check_health(self) -> bool:
        """
        Check if Ollama server is reachable and the model is available.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.host}/api/tags")
                response.raise_for_status()

                # Check if our model is available
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                # Check if our model (or a variant) is in the list
                model_base = self.config.model.split(':')[0]
                model_available = any(model_base in name for name in model_names)

                if not model_available:
                    logger.warning(
                        f"Model {self.config.model} not found. "
                        f"Available models: {model_names}"
                    )
                    return False

                logger.info(f"Ollama health check passed. Model {self.config.model} is available.")
                return True

        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
