"""
Configuration management for the AI software engineering team.

This module provides centralized configuration using Pydantic settings.
"""

import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # Project paths
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).parent)
    ARTIFACTS_DIR: Path = Field(default_factory=lambda: Path(__file__).parent / "artifacts")
    WORKSPACE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent / "workspace")
    PROMPTS_DIR: Path = Field(default_factory=lambda: Path(__file__).parent / "prompts")

    # LLM Configuration
    OLLAMA_HOST: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    LLM_TIMEOUT: int = Field(default=120, env="LLM_TIMEOUT")

    # Model selection by role
    MODEL_ANALYST: str = Field(default="qwen2.5:14b", env="MODEL_ANALYST")
    MODEL_ARCHITECT: str = Field(default="qwen2.5:14b", env="MODEL_ARCHITECT")
    MODEL_BACKEND: str = Field(default="deepseek-coder:6.7b", env="MODEL_BACKEND")
    MODEL_FRONTEND: str = Field(default="deepseek-coder:6.7b", env="MODEL_FRONTEND")
    MODEL_DESIGNER: str = Field(default="mistral:7b", env="MODEL_DESIGNER")
    MODEL_QA: str = Field(default="mistral:7b", env="MODEL_QA")
    MODEL_CTO: str = Field(default="qwen2.5:14b", env="MODEL_CTO")

    # Agent Configuration
    ENABLE_ALL_AGENTS: bool = Field(default=True, env="ENABLE_ALL_AGENTS")
    AGENT_TIMEOUT: int = Field(default=300, env="AGENT_TIMEOUT")

    # Event Bus Configuration
    MAX_QUEUE_SIZE: int = Field(default=1000, env="MAX_QUEUE_SIZE")

    # Dashboard Configuration
    DASHBOARD_HOST: str = Field(default="0.0.0.0", env="DASHBOARD_HOST")
    DASHBOARD_PORT: int = Field(default=8000, env="DASHBOARD_PORT")
    DASHBOARD_ENABLED: bool = Field(default=True, env="DASHBOARD_ENABLED")

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )

    # Development/Debug
    DEBUG_MODE: bool = Field(default=False, env="DEBUG")
    MOCK_LLM: bool = Field(default=False, env="MOCK_LLM")  # Use mock LLM for testing

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings instance
    """
    global _settings

    if _settings is None:
        _settings = Settings()

        # Ensure directories exist
        _settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        _settings.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    return _settings


def configure_logging(settings: Optional[Settings] = None) -> None:
    """
    Configure application logging.

    Args:
        settings: Optional settings instance
    """
    if settings is None:
        settings = get_settings()

    # Map string level to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = level_map.get(settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(
                settings.ARTIFACTS_DIR / "system.log",
                encoding='utf-8'
            )
        ]
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info(f"Logging configured at level: {settings.LOG_LEVEL}")
