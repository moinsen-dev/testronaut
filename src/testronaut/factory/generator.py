"""
Test Generator Factory.

This module provides a factory for creating test generator components.
"""
from typing import Dict, Type

from testronaut.factory import Factory, registry
from testronaut.interfaces import TestGenerator
from testronaut.utils.errors import ConfigurationError


class TestGeneratorFactory(Factory[TestGenerator]):
    """Factory for creating test generator components."""

    def __init__(self):
        """Initialize the test generator factory."""
        self._generator_classes: Dict[str, Type[TestGenerator]] = {}

    def register_generator_class(self, generator_type: str, generator_class: Type[TestGenerator]) -> None:
        """
        Register a test generator class.

        Args:
            generator_type: The type identifier for the generator.
            generator_class: The generator class to register.

        Raises:
            ValueError: If a generator class is already registered for the type.
        """
        if generator_type in self._generator_classes:
            raise ValueError(f"Generator class for {generator_type} already registered")
        self._generator_classes[generator_type] = generator_class

    def create(self, generator_type: str = "default", **kwargs) -> TestGenerator:
        """
        Create a test generator instance.

        Args:
            generator_type: The type of generator to create.
            **kwargs: Generator-specific configuration parameters.

        Returns:
            An instance of the test generator.

        Raises:
            ConfigurationError: If the configuration is invalid or the generator type is not registered.
        """
        generator_class = self._generator_classes.get(generator_type)
        if generator_class is None:
            available_types = ", ".join(self._generator_classes.keys())
            raise ConfigurationError(
                f"No generator class registered for type '{generator_type}'",
                details={"available_types": available_types}
            )

        try:
            return generator_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create generator of type '{generator_type}'",
                details={"error": str(e)}
            ) from e


# Register the factory with the global registry
generator_factory = TestGeneratorFactory()
registry.register("test_generator", generator_factory)