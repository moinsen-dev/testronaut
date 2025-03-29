"""
Version comparison utilities for Testronaut.

This module provides utilities for comparing semantic versions
and determining if reanalysis is needed for CLI tools.
"""

import re
from typing import Optional, Tuple


def parse_version(version_str: str) -> Optional[Tuple[int, ...]]:
    """
    Parse a version string into its component parts.

    Args:
        version_str: Version string to parse (e.g., "1.2.3" or "v2.1.0")

    Returns:
        A tuple of version components as integers, or None if parsing fails
    """
    if not version_str:
        return None

    # Remove leading 'v' or 'V' if present
    if version_str.lower().startswith("v"):
        version_str = version_str[1:]

    # Extract version components using regex
    version_match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version_str)
    if not version_match:
        return None

    # Convert matched groups to integers, handling None values
    version_parts = []
    for i in range(1, 4):  # Match groups 1-3
        part = version_match.group(i)
        if part is not None:
            version_parts.append(int(part))
        else:
            version_parts.append(0)  # Default to 0 for missing parts

    return tuple(version_parts)


def normalize_version(version_str: str) -> str:
    """
    Normalize a version string to standard format.

    Args:
        version_str: Version string to normalize

    Returns:
        Normalized version string (e.g., "1.2.3")
    """
    version_parts = parse_version(version_str)
    if not version_parts:
        return version_str  # Return original if parsing fails

    # Format as dot-separated values
    return ".".join(str(part) for part in version_parts)


def requires_reanalysis(stored_version: str, current_version: str) -> bool:
    """
    Determine if a CLI tool requires reanalysis based on version comparison.

    Follows these rules:
    - Always reanalyze if the MAJOR version changes (e.g., 1.x.x to 2.x.x)
    - Reanalyze if the MINOR version changes (e.g., 1.1.x to 1.2.x)
    - Skip reanalysis for PATCH changes (e.g., 1.1.1 to 1.1.2)

    Args:
        stored_version: The version stored in the database
        current_version: The current version of the CLI tool

    Returns:
        True if reanalysis is required, False otherwise
    """
    if not stored_version or not current_version:
        return True  # If either version is missing, reanalyze

    stored_parts = parse_version(stored_version)
    current_parts = parse_version(current_version)

    if not stored_parts or not current_parts:
        return True  # If parsing fails for either version, reanalyze

    # Compare MAJOR version (index 0)
    if current_parts[0] != stored_parts[0]:
        return True

    # Compare MINOR version (index 1)
    if current_parts[1] != stored_parts[1]:
        return True

    # Only PATCH changed or no change at all
    return False


def get_version_components(version_str: str) -> Tuple[int, int, int]:
    """
    Get the major, minor, and patch components of a version string.

    Args:
        version_str: Version string to parse

    Returns:
        Tuple of (major, minor, patch) version components
    """
    version_parts = parse_version(version_str)
    if not version_parts:
        return (0, 0, 0)  # Default if parsing fails

    # Ensure we have exactly 3 components
    parts = list(version_parts)
    while len(parts) < 3:
        parts.append(0)

    return (parts[0], parts[1], parts[2])
