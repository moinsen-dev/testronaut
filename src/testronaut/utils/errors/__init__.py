"""
Error handling module for Testronaut.

This module defines the exception hierarchy and error handling utilities
for the Testronaut application.
"""

import inspect
import json
import traceback
from typing import Any, Dict, Optional, Type


class TestronautError(Exception):
    """Base exception for all Testronaut-specific errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the error.

        Args:
            message: The error message
            details: Additional error details as a dictionary
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(TestronautError):
    """Error related to configuration issues."""

    pass


class MissingConfigError(ConfigurationError):
    """Error for missing configuration items."""

    pass


class InvalidConfigError(ConfigurationError):
    """Error for invalid configuration values."""

    pass


class ValidationError(TestronautError):
    """Error for data validation failures."""

    pass


class InvalidInputError(ValidationError):
    """Error for invalid user input."""

    pass


class SchemaValidationError(ValidationError):
    """Error for schema validation failures."""

    pass


class ExecutionError(TestronautError):
    """Error during test execution."""

    pass


class CommandExecutionError(ExecutionError):
    """Error during command execution."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the error.

        Args:
            message: The error message
            command: The command that failed
            exit_code: The command's exit code
            stdout: The command's standard output
            stderr: The command's standard error
            details: Additional error details
        """
        if details is None:
            details = {}

        if command is not None:
            details["command"] = command
        if exit_code is not None:
            details["exit_code"] = exit_code
        if stdout is not None:
            details["stdout"] = stdout
        if stderr is not None:
            details["stderr"] = stderr

        super().__init__(message, details)


class DockerError(ExecutionError):
    """Error related to Docker operations."""

    pass


class TimeoutError(ExecutionError):
    """Error for execution timeouts."""

    pass


class VerificationError(TestronautError):
    """Error during result verification."""

    pass


class ResultMismatchError(VerificationError):
    """Error for mismatched test results."""

    def __init__(self, message: str, expected: Any, actual: Any, comparison: Optional[str] = None):
        """
        Initialize the error.

        Args:
            message: The error message
            expected: The expected value
            actual: The actual value
            comparison: Optional comparison details
        """
        details = {"expected": expected, "actual": actual, "comparison": comparison}
        super().__init__(message, details)


class SemanticComparisonError(VerificationError):
    """Error during semantic comparison of results."""

    pass


class ConnectivityError(TestronautError):
    """Error related to external connectivity."""

    pass


class DatabaseError(ConnectivityError):
    """Error for database operations."""

    pass


class LLMServiceError(ConnectivityError):
    """Error when communicating with LLM services."""

    pass


class FileSystemError(ConnectivityError):
    """Error during file system operations."""

    pass


# Error handler registry
_ERROR_HANDLERS: Dict[Type[TestronautError], callable] = {}


def register_error_handler(error_class: Type[TestronautError], handler: callable):
    """
    Register a handler for a specific error type.

    Args:
        error_class: The error class to handle
        handler: The handler function
    """
    _ERROR_HANDLERS[error_class] = handler


def handle_error(error: TestronautError) -> Any:
    """
    Handle an error using registered handlers.

    Args:
        error: The error to handle

    Returns:
        The result of the handler, if any
    """
    # Find the most specific handler
    for error_class, handler in _ERROR_HANDLERS.items():
        if isinstance(error, error_class):
            return handler(error)

    # No specific handler found, re-raise the error
    raise error


def format_error(error: TestronautError) -> str:
    """
    Format an error for display.

    Args:
        error: The error to format

    Returns:
        Formatted error message
    """
    message = f"Error: {error.message}"

    if error.details:
        message += "\nDetails:"
        for key, value in error.details.items():
            message += f"\n  {key}: {value}"

    return message
