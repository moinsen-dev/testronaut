"""
LLM Manager Factory.

This module provides a factory for creating LLM manager components.
"""
from typing import Dict, Type

from testronaut.factory import Factory, registry
from testronaut.interfaces import LLMManager
from testronaut.utils.errors import ConfigurationError


class LLMManagerFactory(Factory[LLMManager]):
    """Factory for creating LLM manager components."""

    def __init__(self):
        """Initialize the LLM manager factory."""
        self._manager_classes: Dict[str, Type[LLMManager]] = {}

    def register_manager_class(self, manager_type: str, manager_class: Type[LLMManager]) -> None:
        """
        Register an LLM manager class.

        Args:
            manager_type: The type identifier for the manager.
            manager_class: The manager class to register.

        Raises:
            ValueError: If a manager class is already registered for the type.
        """
        if manager_type in self._manager_classes:
            raise ValueError(f"LLM manager class for {manager_type} already registered")
        self._manager_classes[manager_type] = manager_class

    def create(self, manager_type: str = "default", **kwargs) -> LLMManager:
        """
        Create an LLM manager instance.

        Args:
            manager_type: The type of manager to create.
            **kwargs: Manager-specific configuration parameters.

        Returns:
            An instance of the LLM manager.

        Raises:
            ConfigurationError: If the configuration is invalid or the manager type is not registered.
        """
        manager_class = self._manager_classes.get(manager_type)
        if manager_class is None:
            available_types = ", ".join(self._manager_classes.keys())
            raise ConfigurationError(
                f"No LLM manager class registered for type '{manager_type}'",
                details={"available_types": available_types}
            )

        try:
            return manager_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create LLM manager of type '{manager_type}'",
                details={"error": str(e)}
            ) from e


# Register the factory with the global registry
llm_factory = LLMManagerFactory()
registry.register("llm_manager", llm_factory)