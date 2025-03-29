"""
Default LLM Manager Implementation.
"""
import importlib
from typing import Any, Dict, List, Type, Optional, Protocol # Import Protocol

from testronaut.interfaces.llm import LLMManager
from testronaut.utils.errors import ConfigurationError, LLMServiceError
from testronaut.llm.providers.base import BaseLLMProvider # Import from base
from testronaut.llm.providers.llama_cpp_provider import LlamaCppProvider # Import the provider


# BaseLLMProvider protocol is now defined in .providers.base


class DefaultLLMManager(LLMManager):
    """
    Default implementation of the LLMManager interface.
    This manager coordinates interactions with different LLM providers.
    """

    def __init__(self, default_provider: str = "mock", **kwargs):
        """Initialize the DefaultLLMManager."""
        self.provider: Optional[BaseLLMProvider] = None # Use the base protocol if defined
        self.provider_name: Optional[str] = None
        self.config = kwargs
        print(f"Initializing DefaultLLMManager with default provider '{default_provider}' and config: {self.config}")
        # Attempt to initialize the default provider immediately
        try:
            # Pass only relevant config keys for the provider
            provider_config = self.config.get(default_provider, {})
            self.initialize(provider=default_provider, **provider_config)
        except ConfigurationError as e:
            print(f"Warning: Failed to initialize default provider '{default_provider}': {e}")
            # Proceed without a provider, user must call initialize explicitly or configure correctly
        except Exception as e:
            print(f"Unexpected error initializing default provider '{default_provider}': {e}")


    def initialize(self, provider: str, **config) -> bool:
        """
        Initialize the LLM manager with a specific provider.

        Args:
            provider: The LLM provider to use (e.g., "openai", "anthropic", "llama-cpp").
            **config: Provider-specific configuration parameters.

        Returns:
            True if initialization was successful.

        Raises:
            ConfigurationError: If the configuration is invalid or provider not found.
            LLMServiceError: If the provider fails to initialize.
        """
        print(f"Attempting to initialize provider: {provider} with config: {config}")
        try:
            provider_class = self._get_provider_class(provider)
            # Instantiate the provider with its specific config
            self.provider = provider_class(**config)
            self.provider_name = provider
            print(f"Successfully initialized provider: {provider}")
            return True
        except ImportError as e:
             raise ConfigurationError(
                 f"Failed to import provider '{provider}'. "
                 f"Ensure necessary dependencies are installed (e.g., pip install testronaut[{provider}]). "
                 f"Details: {e}"
             ) from e
        except Exception as e:
            # Catch potential errors during provider __init__
            raise LLMServiceError(f"Failed to initialize provider instance '{provider}': {e}") from e


    def _get_provider_class(self, provider_name: str) -> Type[BaseLLMProvider]:
        """Helper to get the class for a given provider name."""
        # TODO: Add mappings for other providers (openai, anthropic, mock)
        provider_map: Dict[str, Type[BaseLLMProvider]] = {
            "llama-cpp": LlamaCppProvider,
            # "openai": OpenAIProvider,
            # "anthropic": AnthropicProvider,
            # "mock": MockProvider,
        }
        provider_class = provider_map.get(provider_name)
        if provider_class is None:
            available = ", ".join(provider_map.keys())
            raise ConfigurationError(f"Unsupported LLM provider: '{provider_name}'. Available: {available}")
        return provider_class

    def _ensure_provider(self):
        """Ensure a provider is initialized."""
        if self.provider is None:
            raise LLMServiceError(
                "LLM provider has not been initialized. "
                "Please check configuration or call initialize()."
            )

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """Generate text using the configured LLM provider."""
        self._ensure_provider()
        assert self.provider is not None # Ensure provider is not None for type checker
        # Delegate to the loaded provider's generate_text method
        try:
            return self.provider.generate_text(prompt=prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
        except Exception as e:
            # Catch potential provider errors
            raise LLMServiceError(f"Provider '{self.provider_name}' failed during generate_text: {e}") from e

    def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> Dict[str, float]:
        """Classify text using the configured LLM provider."""
        self._ensure_provider()
        # TODO: Delegate to self.provider.classify(...) or implement using generate_text
        raise NotImplementedError("classify not yet implemented.")

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data using the configured LLM provider."""
        self._ensure_provider()
        # TODO: Delegate to self.provider.extract_structured_data(...) or implement using generate_text
        raise NotImplementedError("extract_structured_data not yet implemented.")

    def analyze_help_text(
        self,
        help_text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze CLI help text using the configured LLM provider."""
        self._ensure_provider()
        # TODO: Delegate to self.provider.analyze_help_text(...) or implement using generate_text
        raise NotImplementedError("analyze_help_text not yet implemented.")

    def get_embedding(
        self,
        text: str,
        **kwargs
    ) -> List[float]:
        """Get text embedding using the configured LLM provider."""
        self._ensure_provider()
        assert self.provider is not None # Ensure provider is not None for type checker
        # Delegate to provider if it supports get_embedding directly
        if hasattr(self.provider, 'get_embedding'):
            try:
                # Type ignore needed as BaseLLMProvider doesn't enforce get_embedding
                return self.provider.get_embedding(text=text, **kwargs) # type: ignore
            except Exception as e:
                raise LLMServiceError(f"Provider '{self.provider_name}' failed during get_embedding: {e}") from e
        else:
            # TODO: Implement embedding generation using generate_text if provider doesn't support it directly
            raise NotImplementedError(f"get_embedding not directly supported by provider '{self.provider_name}' and fallback not implemented.")


    def compare_outputs(
        self,
        expected: str,
        actual: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Compare outputs semantically using the configured LLM provider."""
        self._ensure_provider()
        # TODO: Delegate to self.provider.compare_outputs(...) or implement using generate_text
        raise NotImplementedError("compare_outputs not yet implemented.")

# Register this manager with the LLMManagerFactory
from testronaut.factory import registry # Import registry
from testronaut.factory.llm import LLMManagerFactory # Import factory

def register_llm_manager():
    """Registers the DefaultLLMManager with the global factory registry."""
    try:
        # Use get_factory instead of get
        factory = registry.get_factory("llm_manager")
        if factory is None:
             print("Error: 'llm_manager' factory not found in registry.")
             return
        if isinstance(factory, LLMManagerFactory):
            factory.register_manager_class("default", DefaultLLMManager)
            print("Registered DefaultLLMManager with the factory.")
        else:
            print(f"Error: Expected LLMManagerFactory, but found {type(factory)} in registry.")
    except KeyError:
        print("Error: 'llm_manager' not found in the factory registry.")
    except Exception as e:
        print(f"Error during LLM manager registration: {e}")

# Call the registration function when this module is imported.
# Note: This approach has potential side effects. A dedicated initialization
# function called from the application entry point is generally preferred.
register_llm_manager()
