"""
Base LLM interface for agent interactions.

This module defines the abstract interface that all LLM implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseLLM(ABC):
    """
    Abstract base class for LLM implementations.

    This provides a standard interface for all LLM backends (Ollama, OpenAI, Anthropic, etc.)
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System-level instructions and context
            user_prompt: User's specific request or question
            temperature: Randomness in generation (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate (None = model default)
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response

        Raises:
            LLMException: If generation fails
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response following a schema.

        Args:
            system_prompt: System-level instructions
            user_prompt: User's request
            schema: JSON schema for the response structure
            temperature: Generation randomness
            **kwargs: Additional parameters

        Returns:
            Structured response as dictionary

        Raises:
            LLMException: If generation fails or response doesn't match schema
        """
        pass


class LLMException(Exception):
    """Exception raised for LLM-related errors."""

    def __init__(
        self,
        message: str,
        error_type: str = "generation_error",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize LLM exception.

        Args:
            message: Error message
            error_type: Type of error (generation_error, connection_error, etc.)
            details: Additional error details
        """
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class LLMConfig:
    """Configuration for LLM instances."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        **kwargs: Any
    ):
        """
        Initialize LLM configuration.

        Args:
            model: Model identifier/name
            temperature: Default temperature
            max_tokens: Default max tokens
            timeout: Request timeout in seconds
            **kwargs: Additional configuration
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra = kwargs
