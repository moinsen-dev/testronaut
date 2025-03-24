"""
Configuration System.

This module provides a configuration system for the Testronaut application.
"""

import json
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set, Type, Union

import yaml
from pydantic import BaseModel, Field, computed_field, model_validator

from testronaut.utils.errors import ConfigurationError, MissingConfigError


class BaseSettings(BaseModel):
    """Base class for all settings models."""

    _env_prefix: ClassVar[str] = "TESTRONAUT_"

    @model_validator(mode="after")
    def load_from_env_vars(self) -> "BaseSettings":
        """
        Load settings from environment variables.

        Environment variables take precedence over values in the settings object.
        Variable names should be prefixed with TESTRONAUT_ and use uppercase with
        underscores for nested attributes.

        Example:
            TESTRONAUT_DATABASE_URL -> database.url
            TESTRONAUT_LOG_LEVEL -> log_level
        """
        for key, field_info in self.model_fields.items():
            env_var = f"{self._env_prefix}{key.upper()}"
            if env_var in os.environ:
                setattr(self, key, os.environ[env_var])
        return self


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", description="The logging level")
    format: str = Field(default="structured", description="Logging format (structured or simple)")
    output_file: Optional[str] = Field(
        default=None, description="Log file path (if None, logs to console only)"
    )
    json_output: bool = Field(default=False, description="Whether to output logs in JSON format")


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field(default="sqlite:///testronaut.db", description="Database connection URL")
    echo: bool = Field(default=False, description="Whether to echo SQL statements")
    pool_size: int = Field(default=5, description="Database connection pool size")
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""

    provider: str = Field(default="openai", description="The LLM provider to use")
    model: str = Field(default="gpt-4o", description="The model to use for the LLM provider")
    temperature: float = Field(default=0.7, description="The sampling temperature for the LLM")
    max_tokens: int = Field(default=1000, description="The maximum number of tokens to generate")
    provider_settings: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "openai": {
                "api_key": None,
                "organization": None,
                "base_url": None,
                "models": {
                    "default": "gpt-4o",
                    "chat": "gpt-4o",
                    "json": "gpt-4o",
                    "embedding": "text-embedding-3-small",
                },
            },
            "anthropic": {
                "api_key": None,
                "base_url": None,
                "models": {
                    "default": "claude-3-sonnet-20240229",
                    "chat": "claude-3-sonnet-20240229",
                    "json": "claude-3-opus-20240229",
                },
            },
            "mock": {},
        },
        description="Provider-specific settings",
    )

    @model_validator(mode="after")
    def populate_api_keys_from_env(self) -> "LLMSettings":
        """Populate API keys from environment variables if not set in config."""
        # Get the current provider's settings
        provider_config = self.provider_settings.get(self.provider, {})

        # Try to set API key for the current provider from environment
        if self.provider == "openai" and not provider_config.get("api_key"):
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                if self.provider not in self.provider_settings:
                    self.provider_settings[self.provider] = {}
                self.provider_settings[self.provider]["api_key"] = api_key

        elif self.provider == "anthropic" and not provider_config.get("api_key"):
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                if self.provider not in self.provider_settings:
                    self.provider_settings[self.provider] = {}
                self.provider_settings[self.provider]["api_key"] = api_key

        # Generic TESTRONAUT_LLM_API_KEY can apply to any provider as fallback
        if not provider_config.get("api_key"):
            api_key = os.environ.get("TESTRONAUT_LLM_API_KEY")
            if api_key:
                if self.provider not in self.provider_settings:
                    self.provider_settings[self.provider] = {}
                self.provider_settings[self.provider]["api_key"] = api_key

        return self

    @property
    def current_provider_settings(self) -> Dict[str, Any]:
        """Get settings for the current provider."""
        return self.provider_settings.get(self.provider, {})

    def get_model_for_task(self, task: str = "default") -> str:
        """
        Get the configured model for a specific task.

        Args:
            task: The task type (default, chat, json, embedding)

        Returns:
            The model name to use
        """
        provider_config = self.current_provider_settings
        models = provider_config.get("models", {})

        # If the specific task model is configured, use it
        if task in models:
            return models[task]

        # Otherwise fallback to default model or the general model setting
        return models.get("default", self.model)


class ExecutionSettings(BaseSettings):
    """Test execution configuration settings."""

    timeout: int = Field(default=60, description="Default timeout for test execution in seconds")
    work_dir: Optional[str] = Field(
        default=None, description="Working directory for test execution"
    )
    use_docker: bool = Field(
        default=True, description="Whether to use Docker for test execution isolation"
    )
    docker_image: str = Field(
        default="ubuntu:latest", description="Default Docker image for test execution"
    )
    parallel_tests: int = Field(default=1, description="Number of tests to run in parallel")


class Settings(BaseSettings):
    """Main application settings."""

    app_name: str = Field(default="Testronaut", description="The application name")
    debug: bool = Field(default=False, description="Whether to run in debug mode")
    config_dir: str = Field(
        default="~/.testronaut", description="Directory for configuration files"
    )

    # Component settings
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging settings"
    )
    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings, description="Database settings"
    )
    llm: LLMSettings = Field(default_factory=LLMSettings, description="LLM settings")
    execution: ExecutionSettings = Field(
        default_factory=ExecutionSettings, description="Test execution settings"
    )

    @computed_field
    @property
    def config_path(self) -> Path:
        """Get the configuration directory path."""
        return Path(os.path.expanduser(self.config_dir))


def load_config_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a configuration file.

    Args:
        file_path: Path to the configuration file.

    Returns:
        The configuration as a dictionary.

    Raises:
        ConfigurationError: If the file cannot be loaded.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise MissingConfigError(f"Configuration file does not exist: {file_path}")

    try:
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        elif file_path.suffix == ".json":
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            raise ConfigurationError(
                f"Unsupported configuration file format: {file_path.suffix}",
                details={"supported_formats": [".yaml", ".yml", ".json"]},
            )
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load configuration file: {file_path}", details={"error": str(e)}
        ) from e


def save_config_file(config: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    Save a configuration to a file.

    Args:
        config: The configuration to save.
        file_path: Path to the configuration file.

    Raises:
        ConfigurationError: If the file cannot be saved.
    """
    file_path = Path(file_path)

    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
        elif file_path.suffix == ".json":
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2)
        else:
            raise ConfigurationError(
                f"Unsupported configuration file format: {file_path.suffix}",
                details={"supported_formats": [".yaml", ".yml", ".json"]},
            )
    except Exception as e:
        raise ConfigurationError(
            f"Failed to save configuration file: {file_path}", details={"error": str(e)}
        ) from e


def load_settings(config_file: Optional[Union[str, Path]] = None) -> Settings:
    """
    Load settings from a configuration file and environment variables.

    Args:
        config_file: Path to the configuration file. If None, the default location is used.

    Returns:
        The loaded settings.

    Raises:
        ConfigurationError: If the settings cannot be loaded.
    """
    # Start with default settings
    settings = Settings()

    # If a config file is specified, load it
    if config_file:
        config_data = load_config_file(config_file)
        settings = Settings.model_validate(config_data)
    else:
        # Look for config file in default location
        default_config = settings.config_path / "config.yaml"
        if default_config.exists():
            config_data = load_config_file(default_config)
            settings = Settings.model_validate(config_data)

    # Environment variables are handled by the model validators
    return settings


# Singleton settings instance
settings = Settings()

# Import setup utilities
from testronaut.config.setup import get_config_path, initialize_config, update_config

__all__ = [
    "BaseSettings",
    "LoggingSettings",
    "DatabaseSettings",
    "LLMSettings",
    "ExecutionSettings",
    "Settings",
    "load_config_file",
    "save_config_file",
    "load_settings",
    "settings",
    "initialize_config",
    "update_config",
    "get_config_path",
]
