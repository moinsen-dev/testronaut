"""
Structured logging module for Testronaut.

This module provides context-aware structured logging for the Testronaut application.
"""
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure standard logging
logging.basicConfig(
    level=os.environ.get("TESTRONAUT_LOG_LEVEL", "INFO"),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=Console(stderr=True))],
)

# Create a global request context
_request_context: Dict[str, Any] = {}


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.

    Args:
        name: The logger name, typically __name__

    Returns:
        A configured structlog logger
    """
    logger = structlog.get_logger(name)

    # Add global context if present
    if _request_context:
        logger = logger.bind(**_request_context)

    return logger


def set_context(key: str, value: Any) -> None:
    """
    Set a value in the global context.

    Args:
        key: The context key
        value: The context value
    """
    _request_context[key] = value


def clear_context() -> None:
    """Clear the global context."""
    _request_context.clear()


def get_context() -> Dict[str, Any]:
    """
    Get the current global context.

    Returns:
        The current context dictionary
    """
    return _request_context.copy()


class RequestContext:
    """Context manager for request-specific logging context."""

    def __init__(self, **kwargs):
        """
        Initialize the context with key-value pairs.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs
        self.context.setdefault("request_id", str(uuid.uuid4()))
        self.context.setdefault("timestamp", datetime.utcnow().isoformat())
        self.previous_context = {}

    def __enter__(self):
        """Save the current context and set the new one."""
        self.previous_context = get_context()
        for key, value in self.context.items():
            set_context(key, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the previous context."""
        clear_context()
        for key, value in self.previous_context.items():
            set_context(key, value)
        return False  # Don't suppress exceptions


def log_to_file(filename: str, level: str = "INFO") -> None:
    """
    Add a file handler to the root logger.

    Args:
        filename: The log file path
        level: The log level for the file handler
    """
    handler = logging.FileHandler(filename)
    handler.setLevel(getattr(logging, level))
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_output: bool = False
) -> None:
    """
    Configure logging settings.

    Args:
        level: The log level
        log_file: Optional file to write logs to
        json_output: Whether to output logs as JSON
    """
    # Set log level
    logging.getLogger().setLevel(getattr(logging, level))

    # Add file handler if needed
    if log_file:
        log_to_file(log_file, level)

    # Configure structlog for JSON output if needed
    if json_output:
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )