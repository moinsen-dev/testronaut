"""
Common error classes for the testronaut package.

This module defines common error classes used throughout the package.
"""

from typing import Any, Dict, Optional


class TestronautError(Exception):
    """Base class for all testronaut errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, *args, **kwargs):
        """
        Initialize the error with a message and optional details.

        Args:
            message: The error message.
            details: Additional details about the error.
            *args: Additional arguments to pass to the parent class.
            **kwargs: Additional keyword arguments to pass to the parent class.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message, *args, **kwargs)

    def __str__(self) -> str:
        """
        Return a string representation of the error.

        Returns:
            A string representation of the error.
        """
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class CLIServiceError(TestronautError):
    """Error raised when there is an issue with the CLI service."""

    pass


class CommandExecutionError(TestronautError):
    """Error raised when there is an issue executing a command."""

    pass


class AnalyzerError(TestronautError):
    """Error raised when there is an issue with an analyzer."""

    pass


class LLMServiceError(TestronautError):
    """Error raised when there is an issue with the LLM service."""

    pass


class LLMServiceJSONError(LLMServiceError):
    """Error raised when there is an issue parsing JSON from the LLM service."""

    pass


class ConfigError(TestronautError):
    """Error raised when there is an issue with the configuration."""

    pass


class ValidationError(TestronautError):
    """Error raised when there is an issue with validation."""

    pass
