"""Settings loading logic."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from testronaut.config.file_io import load_config_file
from testronaut.config.models import Settings
from testronaut.models.base import initialize_db
from testronaut.utils.errors import ConfigurationError


def load_settings(config_file: Optional[Union[str, Path]] = None) -> Settings:
    """
    Load settings from config file and environment variables.

    The loading process follows this order of precedence (highest first):
    1. Environment variables (prefixed with TESTRONAUT_)
    2. Values from the configuration file
    3. Default values defined in the Settings models

    Args:
        config_file: Path to config file. If None, searches default location
                     (~/.testronaut/config.yaml).

    Returns:
        The loaded and validated Settings object.

    Raises:
        ConfigurationError: If there is an error loading or validating the configuration.
    """
    # Determine the configuration file path
    if config_file is None:
        config_dir = os.path.expanduser("~/.testronaut")
        config_file_path = Path(config_dir) / "config.yaml"
    else:
        config_file_path = Path(config_file)

    # Load configuration from file if it exists
    config_dict: Dict[str, Any] = {}
    if config_file_path.exists():
        try:
            config_dict = load_config_file(config_file_path)
        except ConfigurationError as e:
            # Re-raise with more context or handle specific cases if needed
            raise ConfigurationError(
                f"Error loading configuration from {config_file_path}: {str(e)}"
            ) from e
        except Exception as e:
            # Catch unexpected errors during file loading
            raise ConfigurationError(
                f"Unexpected error loading configuration file {config_file_path}: {str(e)}"
            ) from e

    # Create Settings instance using the loaded dictionary.
    # Pydantic will handle merging with defaults and environment variables
    # via the model validators defined in BaseSettings and LLMSettings.
    try:
        settings = Settings(**config_dict)
    except Exception as e:
        # Catch Pydantic validation errors or other instantiation issues
        raise ConfigurationError(
            f"Failed to initialize settings: {str(e)}",
            details={"config_file": str(config_file_path), "loaded_config": config_dict},
        ) from e


    # Post-initialization steps (like ensuring config dir exists and resolving DB URL)
    # are handled within Settings.model_post_init

    # Initialize the database using the final resolved URL from settings
    try:
        # The URL should be resolved by model_post_init by now
        initialize_db(settings.database.url)
    except Exception as e:
        # Handle potential database initialization errors
        raise ConfigurationError(
            f"Failed to initialize database with URL {settings.database.url}: {str(e)}"
        ) from e

    return settings


# --- Singleton Access ---
_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Loads and returns the global Settings instance (singleton).

    Loads the settings on the first call and caches the instance
    for subsequent calls.

    Returns:
        The application's Settings object.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = load_settings()
    return _settings_instance
