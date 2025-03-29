"""Pydantic models for Testronaut configuration."""

import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, model_validator

# Import necessary error types if they are used within models
# Assuming ConfigurationError and MissingConfigError might be needed if models raise them directly
# from testronaut.utils.errors import ConfigurationError, MissingConfigError


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

    url: str = Field(
        default="sqlite:///${config_path}/testronaut.db", description="Database connection URL"
    )
    echo: bool = Field(default=False, description="Whether to echo SQL statements")
    pool_size: int = Field(default=5, description="Database connection pool size")
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")

    def get_resolved_url(self, config_path: Optional[str] = None) -> str:
        """
        Get the database URL with variables resolved.

        Args:
            config_path: Optional config path to use instead of the placeholder

        Returns:
            Resolved database URL with actual paths
        """
        if config_path:
            # Replace the placeholder with the actual config path
            expanded_path = str(Path(os.path.expanduser(config_path)))
            return self.url.replace("${config_path}", expanded_path)

        # If no config path provided, just expand user directory
        if "~" in self.url:
            parts = self.url.split("://")
            if len(parts) > 1:
                prefix = parts[0] + "://"
                path = parts[1]
                expanded_path = os.path.expanduser(path)
                return prefix + expanded_path

        # If ${config_path} is in the URL but no config_path was provided
        if "${config_path}" in self.url:
            # Default to ~/.testronaut
            default_config_path = os.path.expanduser("~/.testronaut")
            return self.url.replace("${config_path}", default_config_path)

        return self.url


# Model for storing registered local model information
class RegisteredModel(BaseModel):
    """Represents a registered local LLM model."""
    name: str = Field(description="User-defined name for the model")
    path: str = Field(description="Absolute path to the GGUF model file")
    source: Optional[str] = Field(default=None, description="Source identifier (e.g., Hugging Face repo ID/filename)")


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""

    provider: str = Field(default="openai", description="The LLM provider to use (e.g., openai, anthropic, llama-cpp)")
    model: str = Field(default="gpt-4", description="The model to use for the LLM provider")
    temperature: float = Field(default=0.7, description="The sampling temperature for the LLM")
    max_tokens: int = Field(default=1000, description="The maximum number of tokens to generate")
    provider_settings: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "openai": {
                "api_key": None,
                "organization": None,
                "base_url": None,
                "models": {
                    "default": "gpt-4",
                    "chat": "gpt-4",
                    "json": "gpt-4",
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
            "llama-cpp": {
                "model_path": None, # Path to the *currently active* GGUF model file (set by 'config llm set')
                "n_ctx": 4096,
                "n_gpu_layers": 0,
                "verbose": False,
                # Add other relevant llama-cpp parameters here if needed
                "registered_models": [], # List[RegisteredModel] - managed by 'config llm' commands
            },
            "mock": {},
        },
        description="Provider-specific settings (e.g., API keys, model paths)",
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

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to resolve database URL with config path."""
        # Make sure the config directory exists
        config_path = os.path.expanduser(self.config_dir)
        os.makedirs(config_path, exist_ok=True)

        # Resolve the database URL using the config path
        if hasattr(self.database, "get_resolved_url"):
            resolved_url = self.database.get_resolved_url(config_path)
            self.database.url = resolved_url
