"""
Result Verifier Factory.

This module provides a factory for creating result verifier components.
"""
from typing import Dict, Type

from testronaut.factory import Factory, registry
from testronaut.interfaces import ResultVerifier
from testronaut.utils.errors import ConfigurationError


class ResultVerifierFactory(Factory[ResultVerifier]):
    """Factory for creating result verifier components."""

    def __init__(self):
        """Initialize the result verifier factory."""
        self._verifier_classes: Dict[str, Type[ResultVerifier]] = {}

    def register_verifier_class(self, verifier_type: str, verifier_class: Type[ResultVerifier]) -> None:
        """
        Register a result verifier class.

        Args:
            verifier_type: The type identifier for the verifier.
            verifier_class: The verifier class to register.

        Raises:
            ValueError: If a verifier class is already registered for the type.
        """
        if verifier_type in self._verifier_classes:
            raise ValueError(f"Verifier class for {verifier_type} already registered")
        self._verifier_classes[verifier_type] = verifier_class

    def create(self, verifier_type: str = "default", **kwargs) -> ResultVerifier:
        """
        Create a result verifier instance.

        Args:
            verifier_type: The type of verifier to create.
            **kwargs: Verifier-specific configuration parameters.

        Returns:
            An instance of the result verifier.

        Raises:
            ConfigurationError: If the configuration is invalid or the verifier type is not registered.
        """
        verifier_class = self._verifier_classes.get(verifier_type)
        if verifier_class is None:
            available_types = ", ".join(self._verifier_classes.keys())
            raise ConfigurationError(
                f"No verifier class registered for type '{verifier_type}'",
                details={"available_types": available_types}
            )

        try:
            return verifier_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create verifier of type '{verifier_type}'",
                details={"error": str(e)}
            ) from e


# Register the factory with the global registry
verifier_factory = ResultVerifierFactory()
registry.register("result_verifier", verifier_factory)