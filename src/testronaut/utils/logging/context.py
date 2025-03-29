"""Logging context management utilities."""

import uuid
from datetime import datetime
from typing import Any, Dict

# Global dictionary to hold request-specific or task-specific context
_request_context: Dict[str, Any] = {}


def set_context(key: str, value: Any) -> None:
    """
    Set a key-value pair in the global logging context.

    This context will be automatically bound to loggers retrieved via `get_logger`.

    Args:
        key: The context key (e.g., "user_id", "request_id").
        value: The context value.
    """
    _request_context[key] = value


def clear_context() -> None:
    """Clear all key-value pairs from the global logging context."""
    _request_context.clear()


def get_context() -> Dict[str, Any]:
    """
    Get a copy of the current global logging context.

    Returns:
        A dictionary containing the current context.
    """
    return _request_context.copy()


class RequestContext:
    """
    A context manager for setting and clearing logging context within a `with` block.

    Automatically adds a unique `request_id` and timestamp upon entry.
    Restores the previous context upon exit.

    Example:
        with RequestContext(user_id="abc", task="processing"):
            logger.info("Starting task") # Log will include user_id, task, request_id
        logger.info("Task finished") # Log will not include the context set within the block
    """

    def __init__(self, **kwargs: Any):
        """
        Initialize the context manager with initial key-value pairs.

        Args:
            **kwargs: Context key-value pairs to set upon entering the block.
                      A 'request_id' and 'timestamp' will be added automatically
                      if not provided.
        """
        self.context_to_set = kwargs
        # Ensure standard context fields are present
        self.context_to_set.setdefault("request_id", str(uuid.uuid4()))
        self.context_to_set.setdefault("timestamp_utc", datetime.utcnow().isoformat() + "Z")
        self.previous_context: Dict[str, Any] = {}

    def __enter__(self) -> "RequestContext":
        """
        Saves the current global context and applies the new context for the block.

        Returns:
            The context manager instance itself.
        """
        self.previous_context = get_context()
        # Apply the new context provided during initialization
        for key, value in self.context_to_set.items():
            set_context(key, value)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """
        Restores the logging context that existed before entering the `with` block.

        Args:
            exc_type: Exception type if an exception occurred within the block.
            exc_val: Exception value if an exception occurred.
            exc_tb: Traceback if an exception occurred.

        Returns:
            False, indicating that exceptions should not be suppressed.
        """
        clear_context()
        # Restore the context that was present before entering the block
        for key, value in self.previous_context.items():
            set_context(key, value)
        # Returning False ensures any exception raised within the 'with' block is propagated
        return False
