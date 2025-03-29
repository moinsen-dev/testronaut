"""
Configuration System for Testronaut.

This package handles loading, saving, and accessing application settings.
It uses Pydantic models for validation and structure, supports loading from
YAML/JSON files, and merges settings with environment variables.
"""

# Import models from the models module
from .models import (
    BaseSettings,
    DatabaseSettings,
    ExecutionSettings,
    LLMSettings,
    LoggingSettings,
    RegisteredModel,  # Ensure RegisteredModel is imported if needed publicly
    Settings,
)

# Import file I/O functions
from .file_io import load_config_file, save_config_file

# Import the main settings loader function and the singleton accessor
from .loader import load_settings, get_settings

# Import setup utilities (assuming these are still relevant here or used by load_settings implicitly)
# If setup functions are only used by CLI commands, they might not need to be imported here.
# Reviewing setup.py might be necessary later.
# Re-import get_config_path as it's used elsewhere
from .setup import initialize_config, update_config, get_config_path


# --- Public API ---
# Define what gets imported when using 'from testronaut.config import *'
# Also serves as documentation for the package's public interface.
__all__ = [
    # Models
    "BaseSettings",
    "LoggingSettings",
    "DatabaseSettings",
    "LLMSettings",
    "ExecutionSettings",
    "Settings",
    "RegisteredModel", # Include if it's part of the public API
    # Functions
    "load_config_file",
    "save_config_file",
    "load_settings", # Keep load_settings if direct loading is needed elsewhere
    # Singleton Accessor Function
    "get_settings",
    # Setup Utilities (if intended to be public)
    "initialize_config",
    "update_config",
    "get_config_path", # Re-add get_config_path to public API
]

# Note: The global 'settings' instance is no longer created here directly.
# Use the get_settings() function to access the singleton instance.
