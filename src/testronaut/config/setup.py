"""
Configuration Setup Utilities.

This module provides utilities for setting up and initializing configuration.
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Union, Dict, Any

from testronaut.config import Settings, save_config_file, settings


def initialize_config(
    config_dir: Optional[Union[str, Path]] = None,
    force: bool = False
) -> Path:
    """
    Initialize the configuration directory with default configuration files.

    Args:
        config_dir: Path to the configuration directory. If None, the default location is used.
        force: Whether to overwrite existing configuration files.

    Returns:
        The path to the created configuration directory.

    Raises:
        ConfigurationError: If the configuration cannot be initialized.
    """
    # Use default config dir if not specified
    if config_dir is None:
        config_dir = settings.config_path
    else:
        config_dir = Path(os.path.expanduser(config_dir))

    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Copy default configuration file
    default_config_path = Path(__file__).parent / 'default_config.yaml'
    target_config_path = config_dir / 'config.yaml'

    if not target_config_path.exists() or force:
        shutil.copy(default_config_path, target_config_path)

    return config_dir


def update_config(
    config_updates: Dict[str, Any],
    config_file: Optional[Union[str, Path]] = None
) -> None:
    """
    Update the configuration with the provided values.

    Args:
        config_updates: The configuration updates to apply.
        config_file: Path to the configuration file. If None, the default location is used.

    Raises:
        ConfigurationError: If the configuration cannot be updated.
    """
    # Use default config path if not specified
    if config_file is None:
        config_file = settings.config_path / 'config.yaml'
    else:
        config_file = Path(os.path.expanduser(config_file))

    # Ensure the config directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create a new one
    if config_file.exists():
        from testronaut.config import load_config_file
        existing_config = load_config_file(config_file)
    else:
        # Start with settings defaults
        existing_config = Settings().model_dump()

    # Update the configuration recursively
    def update_dict_recursive(target, source):
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionaries
                update_dict_recursive(target[key], value)
            else:
                # Update or add the value
                target[key] = value

    update_dict_recursive(existing_config, config_updates)

    # Save the updated configuration
    save_config_file(existing_config, config_file)


def get_config_path() -> Path:
    """
    Get the path to the configuration directory.

    Returns:
        The path to the configuration directory.
    """
    return settings.config_path