"""
LLM Factory for creating role-specific LLM instances.

This module provides a factory to create properly configured LLM clients
for different agent roles, following best practices for model selection.
"""

import logging
from typing import Dict, Optional

from llm.base import BaseLLM, LLMConfig
from llm.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


# Default model mappings by role
# These are optimized for different tasks based on model capabilities
DEFAULT_MODEL_MAP: Dict[str, str] = {
    # Reasoning-heavy roles use larger, more capable models
    "analyst": "qwen2.5:14b",      # Good at understanding requirements
    "architect": "qwen2.5:14b",    # Strong at system design and reasoning

    # Code-focused roles use specialized coding models
    "backend": "deepseek-coder:6.7b",   # Optimized for code generation
    "frontend": "deepseek-coder:6.7b",  # Good at TypeScript/React

    # Creative/design roles use balanced models
    "designer": "mistral:7b",      # Good at creative tasks
    "qa": "mistral:7b",            # Good at adversarial thinking

    # Review role uses the most capable model
    "cto": "qwen2.5:14b",          # Comprehensive evaluation
}


# Default temperature settings by role
# Lower temperature = more deterministic, higher = more creative
DEFAULT_TEMPERATURE_MAP: Dict[str, float] = {
    "analyst": 0.1,    # Slightly creative for requirement exploration
    "architect": 0.0,  # Deterministic for technical decisions
    "backend": 0.0,    # Deterministic code generation
    "frontend": 0.0,   # Deterministic code generation
    "designer": 0.3,   # More creative for design
    "qa": 0.2,         # Slightly creative for finding edge cases
    "cto": 0.0,        # Deterministic review
}


class LLMFactory:
    """
    Factory for creating role-specific LLM instances.

    This factory ensures each agent gets an appropriately configured LLM
    based on its role and responsibilities.
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model_map: Optional[Dict[str, str]] = None,
        temperature_map: Optional[Dict[str, float]] = None,
        default_timeout: int = 120
    ):
        """
        Initialize the LLM factory.

        Args:
            ollama_host: Ollama server URL
            model_map: Custom model mapping by role (overrides defaults)
            temperature_map: Custom temperature mapping by role (overrides defaults)
            default_timeout: Default request timeout in seconds
        """
        self.ollama_host = ollama_host
        self.model_map = model_map or DEFAULT_MODEL_MAP.copy()
        self.temperature_map = temperature_map or DEFAULT_TEMPERATURE_MAP.copy()
        self.default_timeout = default_timeout

        logger.info(f"LLM Factory initialized with Ollama at {ollama_host}")
        logger.debug(f"Model map: {self.model_map}")

    def create_for_role(
        self,
        role: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> BaseLLM:
        """
        Create an LLM instance for a specific role.

        Args:
            role: Agent role (analyst, architect, backend, frontend, designer, qa, cto)
            temperature: Override default temperature for this role
            max_tokens: Maximum tokens to generate
            **kwargs: Additional configuration options

        Returns:
            Configured LLM instance

        Raises:
            ValueError: If role is unknown
        """
        if role not in self.model_map:
            raise ValueError(
                f"Unknown role: {role}. "
                f"Available roles: {list(self.model_map.keys())}"
            )

        model = self.model_map[role]
        temp = temperature if temperature is not None else self.temperature_map.get(role, 0.0)

        config = LLMConfig(
            model=model,
            temperature=temp,
            max_tokens=max_tokens,
            timeout=self.default_timeout,
            **kwargs
        )

        logger.info(
            f"Creating LLM for role '{role}': "
            f"model={model}, temp={temp}, timeout={self.default_timeout}"
        )

        return OllamaClient(config=config, host=self.ollama_host)

    def set_model_for_role(self, role: str, model: str) -> None:
        """
        Update the model used for a specific role.

        Args:
            role: Agent role
            model: Model identifier
        """
        logger.info(f"Setting model for role '{role}': {model}")
        self.model_map[role] = model

    def set_temperature_for_role(self, role: str, temperature: float) -> None:
        """
        Update the temperature used for a specific role.

        Args:
            role: Agent role
            temperature: Temperature value (0.0-1.0)
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")

        logger.info(f"Setting temperature for role '{role}': {temperature}")
        self.temperature_map[role] = temperature

    def get_available_roles(self) -> list[str]:
        """
        Get list of available roles.

        Returns:
            List of role names
        """
        return list(self.model_map.keys())

    async def health_check(self, role: Optional[str] = None) -> Dict[str, bool]:
        """
        Check health of LLM instances for all roles or a specific role.

        Args:
            role: Optional specific role to check, or None for all roles

        Returns:
            Dictionary mapping role to health status
        """
        roles_to_check = [role] if role else self.get_available_roles()
        results = {}

        for r in roles_to_check:
            try:
                llm = self.create_for_role(r)
                is_healthy = await llm.check_health()
                results[r] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for role '{r}': {str(e)}")
                results[r] = False

        return results


# Global factory instance (can be configured via settings)
_factory: Optional[LLMFactory] = None


def get_factory(
    ollama_host: Optional[str] = None,
    **kwargs
) -> LLMFactory:
    """
    Get or create the global LLM factory instance.

    Args:
        ollama_host: Ollama server URL (only used if factory not yet created)
        **kwargs: Additional factory configuration

    Returns:
        LLM factory instance
    """
    global _factory

    if _factory is None:
        host = ollama_host or "http://localhost:11434"
        _factory = LLMFactory(ollama_host=host, **kwargs)

    return _factory


def create_llm_for_role(role: str, **kwargs) -> BaseLLM:
    """
    Convenience function to create an LLM for a role using the global factory.

    Args:
        role: Agent role
        **kwargs: Additional configuration

    Returns:
        Configured LLM instance
    """
    factory = get_factory()
    return factory.create_for_role(role, **kwargs)
