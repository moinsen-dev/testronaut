"""
LLM Service Integration Utilities.

This module provides utilities for integrating with various LLM providers.
"""

import importlib
import json
from typing import Any, Callable, Dict, List, Optional, Protocol, Type, Union

from testronaut.config import Settings
from testronaut.utils.errors import LLMServiceError
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class LLMProvider(Protocol):
    """Protocol defining the required interface for LLM providers."""

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the LLM provider with settings.

        Args:
            settings: Provider-specific settings.
        """
        ...

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text from the LLM based on a prompt.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 to 1.0).
            stop_sequences: Sequences that will stop generation.

        Returns:
            Generated text from the LLM.
        """
        ...

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from the LLM based on a prompt and schema.

        Args:
            prompt: The user prompt to send to the LLM.
            schema: JSON schema defining the expected structure.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            Generated structured data conforming to the schema.
        """
        ...


class LLMProviderRegistry:
    """Registry for LLM providers."""

    _providers: Dict[str, Type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Type[LLMProvider]], Type[LLMProvider]]:
        """
        Register an LLM provider.

        Args:
            name: Unique name for the provider.

        Returns:
            Decorator function that registers the provider.
        """

        def decorator(provider_cls: Type[LLMProvider]) -> Type[LLMProvider]:
            cls._providers[name] = provider_cls
            return provider_cls

        return decorator

    @classmethod
    def get_provider(cls, name: str) -> Type[LLMProvider]:
        """
        Get an LLM provider by name.

        Args:
            name: Name of the provider.

        Returns:
            The provider class.

        Raises:
            LLMServiceError: If the provider is not found.
        """
        if name not in cls._providers:
            raise LLMServiceError(
                f"LLM provider '{name}' not found",
                details={
                    "available_providers": list(cls._providers.keys()),
                    "requested_provider": name,
                },
            )
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all registered LLM providers.

        Returns:
            List of provider names.
        """
        return list(cls._providers.keys())


class LLMService:
    """Service for interacting with LLM providers."""

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the LLM service.

        Args:
            settings: Application settings. If None, they will be loaded.
        """
        self.settings = settings or Settings()
        self.provider_name = self.settings.llm.provider
        self.provider_settings = self.settings.llm.current_provider_settings
        self._provider: Optional[LLMProvider] = None

        # Import provider modules to register them
        try:
            # Attempt to import all provider modules
            # This will run their module-level code and register them
            importlib.import_module("testronaut.utils.llm.providers")
        except ImportError:
            logger.warning("Failed to import LLM provider modules")

        logger.info(f"LLM service initialized with provider: {self.provider_name}")
        logger.debug(f"Using model: {self.settings.llm.model}")

    @property
    def provider(self) -> LLMProvider:
        """
        Get or initialize the LLM provider.

        Returns:
            The initialized LLM provider.
        """
        if self._provider is None:
            try:
                # Get the provider class
                provider_cls = LLMProviderRegistry.get_provider(self.provider_name)

                # Create an instance
                self._provider = provider_cls()

                # Initialize it with settings
                self._provider.initialize(self.provider_settings)

                logger.info(f"Initialized LLM provider: {self.provider_name}")

            except Exception as e:
                raise LLMServiceError(
                    f"Failed to initialize LLM provider: {self.provider_name}",
                    details={"error": str(e)},
                ) from e

        return self._provider

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text from the LLM based on a prompt.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 to 1.0).
            stop_sequences: Sequences that will stop generation.

        Returns:
            Generated text from the LLM.
        """
        try:
            # Use default temperature if not specified
            if temperature is None:
                temperature = self.settings.llm.temperature

            # Use default max tokens if not specified
            if max_tokens is None:
                max_tokens = self.settings.llm.max_tokens

            model = self.settings.llm.get_model_for_task("chat")

            logger.debug(
                "Generating text with LLM",
                provider=self.provider_name,
                model=model,
                system_prompt_length=len(system_prompt) if system_prompt else 0,
                prompt_length=len(prompt),
                temperature=temperature,
            )

            result = self.provider.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop_sequences=stop_sequences,
            )

            logger.debug(
                "Generated text with LLM", provider=self.provider_name, result_length=len(result)
            )

            return result

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate text with LLM",
                details={
                    "provider": self.provider_name,
                    "error": str(e),
                    "prompt_length": len(prompt),
                },
            ) from e

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from the LLM based on a prompt and schema.

        Args:
            prompt: The user prompt to send to the LLM.
            schema: JSON schema defining the expected structure.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            Generated structured data conforming to the schema.
        """
        try:
            # Use default temperature if not specified
            if temperature is None:
                # Use a lower temperature for structured outputs
                temperature = min(0.2, self.settings.llm.temperature)

            model = self.settings.llm.get_model_for_task("json")

            logger.debug(
                "Generating JSON with LLM",
                provider=self.provider_name,
                model=model,
                system_prompt_length=len(system_prompt) if system_prompt else 0,
                prompt_length=len(prompt),
                temperature=temperature,
            )

            result = self.provider.generate_json(
                prompt=prompt, schema=schema, system_prompt=system_prompt, temperature=temperature
            )

            logger.debug(
                "Generated JSON with LLM",
                provider=self.provider_name,
                result_keys=list(result.keys()) if result else None,
            )

            return result

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate JSON with LLM",
                details={
                    "provider": self.provider_name,
                    "error": str(e),
                    "prompt_length": len(prompt),
                },
            ) from e
