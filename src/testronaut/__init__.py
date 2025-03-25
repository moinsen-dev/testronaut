"""
Testronaut: Automated CLI Testing Framework.

Testronaut is a tool for generating, executing, and verifying CLI tool tests
using containerized environments and AI-assisted validation.
"""

__version__ = "0.4.0"
__author__ = "Testronaut Team"

# Import key components
from testronaut.config import Settings, get_config_path, initialize_config, update_config

# Export public interface
__all__ = [
    "Settings",
    "initialize_config",
    "update_config",
    "get_config_path",
    "__version__",
    "__author__",
]
