"""
Unit tests for the logger utility.
"""

import logging
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from testronaut.utils.logger import setup_logger


@pytest.mark.unit
class TestLogger:
    """Tests for the logger utility."""

    def test_setup_logger_default(self):
        """Test setup_logger with default parameters."""
        logger = setup_logger()

        # Check logger name and level
        assert logger.name == "testronaut"
        assert logger.level == logging.INFO

        # Check that at least one handler is present (console)
        assert len(logger.handlers) >= 1

        # Check that the handler is a StreamHandler (console)
        assert isinstance(logger.handlers[0], logging.StreamHandler)

        # Clean up by removing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_setup_logger_custom_name_level(self):
        """Test setup_logger with custom name and level."""
        logger = setup_logger(name="custom_logger", level=logging.DEBUG)

        # Check custom name and level
        assert logger.name == "custom_logger"
        assert logger.level == logging.DEBUG

        # Clean up
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_setup_logger_with_file(self):
        """Test setup_logger with log file."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            log_file = tmp.name

        try:
            # Set up logger with file
            logger = setup_logger(log_file=log_file)

            # Should have 2 handlers (console and file)
            assert len(logger.handlers) >= 2

            # At least one handler should be FileHandler
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) >= 1

            # Test logging to file
            test_message = "Test log message"
            logger.info(test_message)

            # Check if message was written to file
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert test_message in log_content

            # Clean up
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

        finally:
            # Remove temporary file
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_logger_formatter(self):
        """Test that logger has proper formatter."""
        logger = setup_logger()

        # Get formatter from first handler
        formatter = logger.handlers[0].formatter

        # Format a test record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)

        # Check that formatted string has expected parts
        assert "test" in formatted  # Logger name
        assert "INFO" in formatted  # Log level
        assert "Test message" in formatted  # Message

        # Clean up
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_multiple_setup_calls(self):
        """Test that multiple setup calls don't duplicate handlers."""
        # Set up logger twice
        logger1 = setup_logger()
        handler_count = len(logger1.handlers)

        logger2 = setup_logger()  # Same name, should return same logger

        # Handler count should remain the same
        assert len(logger2.handlers) == handler_count

        # Clean up
        for handler in logger2.handlers[:]:
            logger2.removeHandler(handler)