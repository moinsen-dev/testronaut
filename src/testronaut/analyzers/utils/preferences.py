"""
User preferences utilities for analyzers.

This module provides functions for managing user preferences for analyzers.
"""

import json
from pathlib import Path
from typing import Any, Dict

from testronaut.config import Settings


def save_user_preferences(tool_name: str, enhanced: bool = False) -> None:
    """
    Save user preferences for a specific tool.

    Args:
        tool_name: The name of the tool.
        enhanced: Whether to use enhanced analysis.
    """
    # Use the config directory from settings
    settings = Settings()
    config_dir = Path(settings.config_dir)
    config_dir.mkdir(exist_ok=True, parents=True)
    preferences_file = config_dir / "tool_preferences.json"

    # Load existing preferences or create new
    if preferences_file.exists():
        try:
            with open(preferences_file, "r") as f:
                preferences = json.load(f)
        except json.JSONDecodeError:
            preferences = {}
    else:
        preferences = {}

    # Update preferences
    preferences[tool_name] = {"enhanced": enhanced}

    # Save preferences
    with open(preferences_file, "w") as f:
        json.dump(preferences, f)


def load_user_preferences(tool_name: str) -> Dict[str, Any]:
    """
    Load user preferences for a specific tool.

    Args:
        tool_name: The name of the tool.

    Returns:
        The preferences for the tool.
    """
    # Use the config directory from settings
    settings = Settings()
    config_dir = Path(settings.config_dir)
    preferences_file = config_dir / "tool_preferences.json"

    # Load existing preferences or create new
    if preferences_file.exists():
        try:
            with open(preferences_file, "r") as f:
                preferences = json.load(f)
                if tool_name in preferences:
                    return preferences[tool_name]
        except json.JSONDecodeError:
            pass

    return {}
