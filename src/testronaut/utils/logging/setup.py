"""Logging setup and configuration for Testronaut."""

import logging
import os
import sys
from typing import Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

# --- Private Configuration State ---
_logging_configured = False


# --- Core Configuration Functions ---

def _setup_structlog(json_output: bool = False) -> None:
    """Configure structlog processors based on output format."""
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        # If not JSON, use a development-friendly console renderer
        # Note: This assumes RichHandler handles the final formatting for console
        processors.append(structlog.stdlib.ProcessorFormatter.wrap_for_formatter)

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _setup_stdlib_logging(level: str = "INFO") -> RichHandler:
    """Configure the standard library logging basics and add RichHandler."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Use RichHandler for nice console output
    rich_handler = RichHandler(
        rich_tracebacks=True,
        show_path=False, # Optionally hide path in RichHandler if structlog adds it
        console=Console(stderr=True) # Log to stderr
    )

    # Basic config sets up the root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s", # Let RichHandler handle formatting
        datefmt="[%X]", # RichHandler uses its own time format
        handlers=[rich_handler],
    )
    return rich_handler


def add_file_handler(filename: str, level: str = "INFO", json_output: bool = False) -> None:
    """
    Add a file handler to the root logger.

    Args:
        filename: The log file path.
        level: The log level for this file handler.
        json_output: If True, format logs as JSON for the file.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.FileHandler(filename)
    handler.setLevel(log_level)

    if json_output:
        # Use structlog's JSONRenderer for file output
        # Need a specific formatter setup for stdlib handler + structlog JSON
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            # These processors mimic the ones used in structlog.configure for JSON
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
            ]
        )
    else:
        # Simple text format for file logs if not JSON
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.info(f"Added file logging handler: {filename} (Level: {level}, JSON: {json_output})")


# --- Public Configuration Function ---

def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_output: bool = False,
    force_reconfigure: bool = False,
) -> None:
    """
    Configure logging settings for the entire application.

    This function should ideally be called once at application startup.

    Args:
        level: The minimum log level (e.g., "DEBUG", "INFO", "WARNING").
        log_file: Optional path to a file where logs should also be written.
        json_output: If True, format logs as JSON (useful for machine processing).
                     If False, use human-readable format (via RichHandler).
        force_reconfigure: If True, allows re-running configuration even if already run.
    """
    global _logging_configured
    if _logging_configured and not force_reconfigure:
        logging.warning("Logging already configured. Skipping reconfiguration.")
        return

    # 1. Configure standard logging (sets root level and adds RichHandler)
    rich_handler = _setup_stdlib_logging(level)

    # 2. Configure structlog processors based on JSON output preference
    _setup_structlog(json_output=json_output)

    # 3. If JSON output is NOT enabled, configure the RichHandler formatter
    #    to work with structlog's ProcessorFormatter.
    if not json_output:
         # Create a structlog formatter for the Rich handler
        formatter = structlog.stdlib.ProcessorFormatter(
            # These processors will be applied only to records processed by this handler
             processor=structlog.dev.ConsoleRenderer(), # Use ConsoleRenderer for pretty printing
             # foreign_pre_chain helps format logs from non-structlog loggers
             foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
             ]
        )
        rich_handler.setFormatter(formatter)
        # Ensure RichHandler level matches the root logger level initially
        rich_handler.setLevel(getattr(logging, level.upper(), logging.INFO))


    # 4. Add file handler if requested
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            add_file_handler(log_file, level, json_output)
        except OSError as e:
            logging.error(f"Failed to create directory for log file {log_file}: {e}", exc_info=True)
        except Exception as e:
             logging.error(f"Failed to add file handler for {log_file}: {e}", exc_info=True)


    _logging_configured = True
    logging.info(f"Logging configured. Level: {level}, JSON Output: {json_output}, File: {log_file or 'None'}")

# --- Initial Default Configuration ---
# Apply a basic configuration when this module is imported,
# using environment variables or defaults.
# This ensures logging works even if configure_logging isn't explicitly called early.
# However, calling configure_logging later allows overriding these defaults.

# _initial_level = os.environ.get("TESTRONAUT_LOG_LEVEL", "INFO")
# configure_logging(level=_initial_level)
# Commented out initial call: Let the application explicitly call configure_logging
# or rely on the simplified setup in __init__ if that's preferred.
# Having setup logic run automatically on import can sometimes be surprising.
