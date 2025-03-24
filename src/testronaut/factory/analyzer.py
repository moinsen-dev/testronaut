"""
CLI Analyzer Factory.

This module provides a factory for creating CLI analyzer components.
"""

from typing import Dict, Type

from testronaut.analyzers.llm_enhanced_analyzer import LLMEnhancedAnalyzer
from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.factory import Factory, registry
from testronaut.interfaces import CLIAnalyzer
from testronaut.utils.errors import ConfigurationError


class CLIAnalyzerFactory(Factory[CLIAnalyzer]):
    """Factory for creating CLI analyzer components."""

    def __init__(self):
        """Initialize the CLI analyzer factory."""
        self._analyzer_classes: Dict[str, Type[CLIAnalyzer]] = {}

        # Register default analyzers
        self.register_analyzer_class("standard", StandardCLIAnalyzer)
        self.register_analyzer_class("llm_enhanced", LLMEnhancedAnalyzer)

        # Set the default analyzer
        self._default_analyzer_type = "standard"

    def register_analyzer_class(
        self, analyzer_type: str, analyzer_class: Type[CLIAnalyzer]
    ) -> None:
        """
        Register a CLI analyzer class.

        Args:
            analyzer_type: The type identifier for the analyzer.
            analyzer_class: The analyzer class to register.

        Raises:
            ValueError: If an analyzer class is already registered for the type.
        """
        if analyzer_type in self._analyzer_classes:
            raise ValueError(f"Analyzer class for {analyzer_type} already registered")
        self._analyzer_classes[analyzer_type] = analyzer_class

    def create(self, analyzer_type: str = "default", **kwargs) -> CLIAnalyzer:
        """
        Create a CLI analyzer instance.

        Args:
            analyzer_type: The type of analyzer to create.
            **kwargs: Analyzer-specific configuration parameters.

        Returns:
            An instance of the CLI analyzer.

        Raises:
            ConfigurationError: If the configuration is invalid or the analyzer type is not registered.
        """
        # Use default analyzer if 'default' is specified
        if analyzer_type == "default":
            analyzer_type = self._default_analyzer_type

        analyzer_class = self._analyzer_classes.get(analyzer_type)
        if analyzer_class is None:
            available_types = ", ".join(self._analyzer_classes.keys())
            raise ConfigurationError(
                f"No analyzer class registered for type '{analyzer_type}'",
                details={"available_types": available_types},
            )

        try:
            return analyzer_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create analyzer of type '{analyzer_type}'", details={"error": str(e)}
            ) from e

    def set_default_analyzer_type(self, analyzer_type: str) -> None:
        """
        Set the default analyzer type to use when 'default' is specified.

        Args:
            analyzer_type: The analyzer type to use as default.

        Raises:
            ValueError: If the analyzer type is not registered.
        """
        if analyzer_type not in self._analyzer_classes:
            available_types = ", ".join(self._analyzer_classes.keys())
            raise ValueError(
                f"Cannot set default analyzer type to '{analyzer_type}'. "
                f"Available types: {available_types}"
            )
        self._default_analyzer_type = analyzer_type


# Register the factory with the global registry
analyzer_factory = CLIAnalyzerFactory()
registry.register("cli_analyzer", analyzer_factory)
