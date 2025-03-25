"""
Test Executor Factory.

This module provides a factory for creating test executor components.
"""
from typing import Dict, Type

from testronaut.factory import Factory, registry
from testronaut.interfaces import TestExecutor
from testronaut.utils.errors import ConfigurationError


class TestExecutorFactory(Factory[TestExecutor]):
    """Factory for creating test executor components."""

    def __init__(self):
        """Initialize the test executor factory."""
        self._executor_classes: Dict[str, Type[TestExecutor]] = {}

    def register_executor_class(self, executor_type: str, executor_class: Type[TestExecutor]) -> None:
        """
        Register a test executor class.

        Args:
            executor_type: The type identifier for the executor.
            executor_class: The executor class to register.

        Raises:
            ValueError: If an executor class is already registered for the type.
        """
        if executor_type in self._executor_classes:
            raise ValueError(f"Executor class for {executor_type} already registered")
        self._executor_classes[executor_type] = executor_class

    def create(self, executor_type: str = "default", **kwargs) -> TestExecutor:
        """
        Create a test executor instance.

        Args:
            executor_type: The type of executor to create.
            **kwargs: Executor-specific configuration parameters.

        Returns:
            An instance of the test executor.

        Raises:
            ConfigurationError: If the configuration is invalid or the executor type is not registered.
        """
        executor_class = self._executor_classes.get(executor_type)
        if executor_class is None:
            available_types = ", ".join(self._executor_classes.keys())
            raise ConfigurationError(
                f"No executor class registered for type '{executor_type}'",
                details={"available_types": available_types}
            )

        try:
            return executor_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create executor of type '{executor_type}'",
                details={"error": str(e)}
            ) from e


# Register the factory with the global registry
executor_factory = TestExecutorFactory()
registry.register("test_executor", executor_factory)