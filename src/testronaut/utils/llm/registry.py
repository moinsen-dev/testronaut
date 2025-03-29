"""Registry for LLM Providers."""

from typing import Callable, Dict, List, Type

# Import the base protocol for type hinting
from testronaut.llm.providers.base import BaseLLMProvider
from testronaut.utils.errors import LLMServiceError


class LLMProviderRegistry:
    """
    A registry for discovering and accessing available LLM provider implementations.

    Uses a class-level dictionary to store registered providers, mapping a
    unique string name to the provider class. Providers can be registered
    using the `@LLMProviderRegistry.register()` decorator.
    """

    _providers: Dict[str, Type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Type[BaseLLMProvider]], Type[BaseLLMProvider]]:
        """
        Class method decorator to register an LLM provider class.

        Example:
            @LLMProviderRegistry.register("my_provider")
            class MyCustomProvider(BaseLLMProvider):
                # ... implementation ...

        Args:
            name: The unique identifier string for the provider (e.g., "openai", "llama-cpp").

        Returns:
            A decorator function that takes the provider class and registers it.
        """

        def decorator(provider_cls: Type[BaseLLMProvider]) -> Type[BaseLLMProvider]:
            if not issubclass(provider_cls, BaseLLMProvider):
                raise TypeError(
                    f"Provider class {provider_cls.__name__} must implement the BaseLLMProvider protocol."
                )
            if name in cls._providers:
                # Optionally, add a warning or raise an error if a provider name is overwritten
                print(f"Warning: Overwriting registered LLM provider '{name}'") # Consider using logger
            cls._providers[name] = provider_cls
            # print(f"Registered LLM provider: {name} -> {provider_cls.__name__}") # Debugging
            return provider_cls

        return decorator

    @classmethod
    def get_provider(cls, name: str) -> Type[BaseLLMProvider]:
        """
        Retrieve a registered LLM provider class by its name.

        Args:
            name: The unique identifier string of the provider.

        Returns:
            The registered provider class (not an instance).

        Raises:
            LLMServiceError: If no provider with the given name is found.
        """
        provider_cls = cls._providers.get(name)
        if provider_cls is None:
            # Automatically try to load provider modules if not found initially
            cls._discover_providers()
            provider_cls = cls._providers.get(name) # Try again after discovery

        if provider_cls is None:
             raise LLMServiceError(
                f"LLM provider '{name}' not found or failed to load.",
                details={
                    "available_providers": list(cls._providers.keys()),
                    "requested_provider": name,
                },
            )
        return provider_cls

    @classmethod
    def list_providers(cls) -> List[str]:
        """
        Get a list of names of all registered LLM providers.

        Returns:
            A list of strings, where each string is a registered provider name.
        """
        # Ensure providers are discovered before listing
        cls._discover_providers()
        return sorted(list(cls._providers.keys()))

    @classmethod
    def _discover_providers(cls) -> None:
        """
        Attempt to discover providers by importing modules in the providers package.
        This ensures registration decorators run.
        """
        import importlib
        import pkgutil
        import importlib.util # Import the util module

        # Define the target package name
        package_name = "testronaut.llm.providers"

        try:
            # Find the specification for the package
            spec = importlib.util.find_spec(package_name)
            if spec is None or spec.submodule_search_locations is None:
                # Handle case where package or its location cannot be found
                print(f"Warning: Could not find package specification or locations for {package_name}")
                return # Exit discovery if spec is not found

            # Get the path(s) from the spec's submodule search locations
            package_path = spec.submodule_search_locations

            # Iterate through modules found in the package path
            for _, module_name, _ in pkgutil.iter_modules(package_path, package_name + "."):
                 # print(f"Attempting to import provider module: {module_name}") # Debugging
                 importlib.import_module(module_name)
        except Exception as e:
            # Log or print a warning if discovery fails for some reason
            print(f"Warning: Failed during LLM provider discovery: {e}") # Consider using logger

# Ensure discovery runs at least once when the registry module is imported
LLMProviderRegistry._discover_providers()
