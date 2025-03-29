"""Configuration file loading and saving utilities."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Union

import yaml

from testronaut.utils.errors import ConfigurationError, MissingConfigError


def load_config_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a configuration file.

    Args:
        file_path: Path to the configuration file.

    Returns:
        The configuration as a dictionary.

    Raises:
        ConfigurationError: If the file cannot be loaded.
        MissingConfigError: If the file does not exist.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise MissingConfigError(f"Configuration file does not exist: {file_path}")

    try:
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "r") as f:
                # Use safe_load to avoid potential security issues with arbitrary code execution
                config_data = yaml.safe_load(f)
                # Ensure safe_load returns a dict, handle None case for empty files
                return config_data if config_data is not None else {}
        elif file_path.suffix == ".json":
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            raise ConfigurationError(
                f"Unsupported configuration file format: {file_path.suffix}",
                details={"supported_formats": [".yaml", ".yml", ".json"]},
            )
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Failed to parse YAML configuration file: {file_path}", details={"error": str(e)}
        ) from e
    except json.JSONDecodeError as e:
        raise ConfigurationError(
            f"Failed to parse JSON configuration file: {file_path}", details={"error": str(e)}
        ) from e
    except Exception as e:
        # Catch other potential errors like file read issues
        raise ConfigurationError(
            f"Failed to load configuration file: {file_path}", details={"error": str(e)}
        ) from e


def save_config_file(config: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    Save a configuration to a file.

    Args:
        config: The configuration dictionary to save.
        file_path: Path to the configuration file.

    Raises:
        ConfigurationError: If the file cannot be saved.
    """
    file_path = Path(file_path)

    # Create parent directories if they don't exist
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ConfigurationError(
            f"Failed to create directory for configuration file: {file_path.parent}",
            details={"error": str(e)},
        ) from e

    try:
        if file_path.suffix in [".yaml", ".yml"]:
            with open(file_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        elif file_path.suffix == ".json":
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2)
        else:
            raise ConfigurationError(
                f"Unsupported configuration file format for saving: {file_path.suffix}",
                details={"supported_formats": [".yaml", ".yml", ".json"]},
            )
    except Exception as e:
        raise ConfigurationError(
            f"Failed to save configuration file: {file_path}", details={"error": str(e)}
        ) from e
