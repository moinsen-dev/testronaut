"""LLM Service for interacting with different providers."""

import importlib
import json
from typing import Any, Dict, List, Optional

# Configuration and logging
# Import Settings type and the get_settings function
from testronaut.config import Settings, get_settings
from testronaut.utils.logging import get_logger

# Errors and registry
from testronaut.utils.errors import LLMServiceError
from testronaut.utils.llm.registry import LLMProviderRegistry

# Base provider protocol
from testronaut.llm.providers.base import BaseLLMProvider

# Initialize logger
logger = get_logger(__name__)


class LLMService:
    """
    Service layer for interacting with configured LLM providers.

    This class acts as a facade, providing a consistent interface for
    generating text and JSON, regardless of the underlying LLM provider
    selected in the application settings. It uses the LLMProviderRegistry
    to find and instantiate the correct provider.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the LLM service.

        Args:
            settings: Optional application settings. If None, the global settings will be loaded on first use.
        """
        # Store provided settings, but don't load global ones yet
        self._initial_settings = settings
        self._settings: Optional[Settings] = None # Internal cache for loaded settings
        self._provider: Optional[BaseLLMProvider] = None
        self.last_token_usage: Optional[Dict[str, Any]] = None

        # Defer logging until settings are loaded
        # logger.info("LLM service instance created.")


    @property
    def settings(self) -> Settings:
        """Loads and returns the settings instance, caching it."""
        if self._settings is None:
            self._settings = self._initial_settings or get_settings()
            # Now we can log initialization details
            logger.info(f"LLM service settings loaded. Provider: {self._settings.llm.provider}")
            logger.debug(f"Default model configured: {self._settings.llm.model}")
            logger.debug(f"Provider specific settings keys: {list(self._settings.llm.current_provider_settings.keys())}")
        return self._settings

    @property
    def provider(self) -> BaseLLMProvider:
        """
        Lazy-loads and returns the configured LLM provider instance.

        Retrieves the provider class from the registry, instantiates it,
        and initializes it with the relevant settings the first time it's accessed.

        Returns:
            The initialized LLM provider instance.

        Raises:
            LLMServiceError: If the provider cannot be found, instantiated, or initialized.
        """
        if self._provider is None:
            try:
                # Access settings through the property to ensure they are loaded
                provider_name = self.settings.llm.provider
                provider_settings = self.settings.llm.current_provider_settings

                # Get the provider class from the registry
                provider_cls = LLMProviderRegistry.get_provider(provider_name)

                # Create an instance
                provider_instance = provider_cls()

                # Initialize it with its specific settings
                provider_instance.initialize(provider_settings) # Use loaded settings

                self._provider = provider_instance # Cache the initialized provider

                logger.info(f"Initialized LLM provider instance: {provider_name}")

            except LLMServiceError as e:
                # Catch registry errors (provider not found)
                 logger.error(f"LLM Registry Error: {e.message}", details=getattr(e, 'details', None))
                 raise # Re-raise the specific error
            except Exception as e:
                # Catch potential errors during instantiation or initialize()
                # Ensure provider_name is accessed safely after settings load attempt
                prov_name = self.settings.llm.provider if self._settings else "unknown"
                logger.error(f"Failed to instantiate or initialize LLM provider '{prov_name}': {e}", exc_info=True)
                raise LLMServiceError(
                    f"Failed to initialize LLM provider: {prov_name}",
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
        **kwargs: Any,
    ) -> str:
        """
        Generate text using the configured LLM provider.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum number of tokens to generate. Overrides default if set.
            temperature: Sampling temperature (0.0 to 1.0). Overrides default if set.
            stop_sequences: Sequences that will stop generation.
            **kwargs: Additional provider-specific arguments.

        Returns:
            Generated text from the LLM.

        Raises:
            LLMServiceError: If the text generation fails.
        """
        try:
            # Access settings via property to ensure loaded
            current_provider_name = self.settings.llm.provider
            temp = temperature if temperature is not None else self.settings.llm.temperature
            max_tok = max_tokens if max_tokens is not None else self.settings.llm.max_tokens
            model = self.settings.llm.get_model_for_task("chat")

            logger.debug(
                "Generating text with LLM",
                provider=current_provider_name, # Use loaded provider name
                model=model,
                system_prompt_present=bool(system_prompt),
                prompt_length=len(prompt),
                temperature=temp,
                max_tokens=max_tok,
            )

            # Access provider via property to ensure initialized
            result = self.provider.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tok,
                temperature=temp,
                stop_sequences=stop_sequences,
                **kwargs,
            )

            self.last_token_usage = getattr(self.provider, "last_token_usage", None)
            if self.last_token_usage:
                logger.debug(
                    "LLM token usage recorded",
                    provider=current_provider_name, # Use loaded provider name
                    model=model,
                    usage=self.last_token_usage,
                )

            logger.debug(
                "LLM text generation successful", provider=current_provider_name, result_length=len(result)
            )
            return result

        except NotImplementedError:
             # Access settings via property to ensure loaded before getting provider name
             current_provider_name = self.settings.llm.provider
             logger.error(f"Provider '{current_provider_name}' does not support generate_text.")
             raise LLMServiceError(f"Provider '{current_provider_name}' does not support text generation.")
        except Exception as e:
            # Access settings via property to ensure loaded before getting provider name
            current_provider_name = self.settings.llm.provider
            logger.error(f"LLM text generation failed: {e}", exc_info=True)
            raise LLMServiceError(
                "Failed to generate text with LLM",
                details={
                    "provider": current_provider_name,
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
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using the configured LLM provider.

        Args:
            prompt: The user prompt designed to elicit a JSON response.
            schema: JSON schema defining the expected structure.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0). Overrides default if set.
            **kwargs: Additional provider-specific arguments.

        Returns:
            Generated structured data as a dictionary.

        Raises:
            LLMServiceError: If the JSON generation fails or is not supported.
        """
        try:
            # Access settings via property to ensure loaded
            current_provider_name = self.settings.llm.provider
            temp = temperature if temperature is not None else self.settings.llm.temperature
            model = self.settings.llm.get_model_for_task("json")

            logger.debug(
                "Generating JSON with LLM",
                provider=current_provider_name, # Use loaded provider name
                model=model,
                schema_keys=list(schema.get("properties", {}).keys()),
                system_prompt_present=bool(system_prompt),
                prompt_length=len(prompt),
                temperature=temp,
            )

            # Access provider via property to ensure initialized
            result = self.provider.generate_json(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temp,
                **kwargs,
            )

            self.last_token_usage = getattr(self.provider, "last_token_usage", None)
            if self.last_token_usage:
                 logger.debug(
                    "LLM token usage recorded",
                    provider=current_provider_name, # Use loaded provider name
                    model=model,
                    usage=self.last_token_usage,
                )

            logger.debug("LLM JSON generation successful", provider=current_provider_name)
            return result

        except NotImplementedError:
             # Access settings via property to ensure loaded before getting provider name
             current_provider_name = self.settings.llm.provider
             logger.error(f"Provider '{current_provider_name}' does not support generate_json.")
             raise LLMServiceError(f"Provider '{current_provider_name}' does not support JSON generation.")
        except Exception as e:
            # Access settings via property to ensure loaded before getting provider name
            current_provider_name = self.settings.llm.provider
            logger.error(f"LLM JSON generation failed: {e}", exc_info=True)
            raise LLMServiceError(
                "Failed to generate JSON with LLM",
                details={
                    "provider": current_provider_name,
                    "error": str(e),
                    "prompt_length": len(prompt),
                    "schema_keys": list(schema.get("properties", {}).keys()),
                },
            ) from e
