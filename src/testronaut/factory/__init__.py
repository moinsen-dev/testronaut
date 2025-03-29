"""
Component Factory System.

This module provides a factory system for creating and managing component instances.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

# Type variable for the component type produced by the factory
T = TypeVar('T')


class Factory(Generic[T], ABC):
    """Base factory interface for creating components."""

    @abstractmethod
    def create(self, **kwargs) -> T:
        """
        Create a component instance.

        Args:
            **kwargs: Component-specific configuration parameters.

        Returns:
            An instance of the component.

        Raises:
            ConfigurationError: If the configuration is invalid.
        """
        pass


class FactoryRegistry:
    """Registry for component factories."""

    def __init__(self):
        """Initialize the factory registry."""
        self._factories: Dict[str, Factory] = {}

    def register(self, component_type: str, factory: Factory) -> None:
        """
        Register a factory for a component type.

        Args:
            component_type: The type of component the factory creates.
            factory: The factory instance.

        Raises:
            ValueError: If a factory for the component type is already registered.
        """
        if component_type in self._factories:
            raise ValueError(f"Factory for {component_type} already registered")
        self._factories[component_type] = factory

    def get_factory(self, component_type: str) -> Optional[Factory]:
        """
        Get a factory for a component type.

        Args:
            component_type: The type of component to get a factory for.

        Returns:
            The factory instance, or None if no factory is registered.
        """
        return self._factories.get(component_type)

    def create(self, component_type: str, **kwargs) -> Any:
        """
        Create a component instance using the registered factory.

        Args:
            component_type: The type of component to create.
            **kwargs: Component-specific configuration parameters.

        Returns:
            An instance of the component.

        Raises:
            ValueError: If no factory is registered for the component type.
            ConfigurationError: If the configuration is invalid.
        """
        factory = self.get_factory(component_type)
        if factory is None:
            raise ValueError(f"No factory registered for {component_type}")
        return factory.create(**kwargs)

    def list_registered_factories(self) -> Dict[str, Factory]:
        """
        Get a dictionary of all registered factories.

        Returns:
            A dictionary mapping component types to factory instances.
        """
        return dict(self._factories)


# Global factory registry
registry = FactoryRegistry()

# Import and register component factories
from testronaut.factory.analyzer import analyzer_factory
from testronaut.factory.executor import executor_factory
from testronaut.factory.generator import generator_factory
from testronaut.factory.llm import llm_factory, LLMManagerFactory # Import specific factory type
from testronaut.factory.verifier import verifier_factory

# --- Register Default Implementations ---
# Register the DefaultLLMManager with the llm_factory instance
try:
    from testronaut.llm.manager import DefaultLLMManager
    if isinstance(llm_factory, LLMManagerFactory):
        llm_factory.register_manager_class("default", DefaultLLMManager)
    else:
        # This case should ideally not happen if imports are correct
        print(f"Warning: llm_factory is not an instance of LLMManagerFactory ({type(llm_factory)}). Cannot register DefaultLLMManager.")
except ImportError:
    # This might happen during initial setup or if structure changes
    print("Warning: Could not import DefaultLLMManager for factory registration.")
except Exception as e:
    print(f"Warning: Error during DefaultLLMManager registration: {e}")
# --- End Registration ---


__all__ = [
    'Factory',
    'FactoryRegistry',
    'registry',
    'analyzer_factory',
    'generator_factory',
    'executor_factory',
    'verifier_factory',
    'llm_factory'
]
