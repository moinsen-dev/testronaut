"""
Structured Logging Package for Testronaut.

Provides context-aware structured logging using structlog and Rich.

Key components:
- `get_logger`: Retrieves a logger instance bound with current context.
- `configure_logging`: Sets up logging level, format, and optional file output.
- `RequestContext`: Context manager for adding request-specific context to logs.
- `set_context`, `clear_context`, `get_context`: Functions for manual context management.
"""

import structlog
from typing import Any

# Import context management utilities
from .context import (
    RequestContext,
    clear_context,
    get_context,
    set_context,
    _request_context, # Import the internal context dict for get_logger
)

# Import setup/configuration functions
from .setup import configure_logging, add_file_handler

# --- Core Logger Retrieval ---

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance bound with global context.

    Retrieves a structlog logger and automatically binds any key-value pairs
    currently stored in the global logging context (managed by `set_context`,
    `clear_context`, or `RequestContext`).

    Args:
        name: The logger name, typically `__name__` of the calling module.

    Returns:
        A configured structlog logger instance ready for use.
    """
    # Retrieve the base logger instance
    logger = structlog.get_logger(name)

    # Bind the current global context to this logger instance
    # This ensures logs created with this instance include the context
    current_ctx = get_context() # Use the function to get a copy
    if current_ctx:
        logger = logger.bind(**current_ctx)

    return logger


# --- Public API ---
# Define what gets imported when using 'from testronaut.utils.logging import *'
__all__ = [
    "get_logger",
    "configure_logging",
    "add_file_handler",
    "RequestContext",
    "set_context",
    "clear_context",
    "get_context",
]

# Note: Initial logging configuration (like basicConfig or structlog.configure)
# is now handled within the `setup.py` module, specifically by the
# `configure_logging` function. The application should call `configure_logging`
# early in its startup process to apply desired settings. A basic default
# might be applied by setup.py if needed, but explicit configuration is preferred.
