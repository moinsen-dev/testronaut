"""
Deprecated Command module for analyzing CLI tools.

This module is being maintained for backward compatibility but will be removed in a future version.
Please import from testronaut.cli.commands.analyze_commands instead.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The testronaut.cli.commands.analyze module is deprecated. "
    "Please use testronaut.cli.commands.analyze_commands instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import from the new module for backward compatibility
from testronaut.cli.commands.analyze_commands import app, tool

# These symbols are imported here for backward compatibility
__all__ = ["app", "tool"]
