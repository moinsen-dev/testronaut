"""
Analyzer package.

This package provides components for analyzing CLI tools.
"""

# Import core functionality
from testronaut.analyzers.core import (
    Spinner,
    analyze_tool,
    get_analyzer,
    save_analysis_data,
    validate_cli_tool_data,
)

# Import analyzer implementations
from testronaut.analyzers.llm_enhanced_analyzer import LLMEnhancedAnalyzer
from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer

# Import utility functions
from testronaut.analyzers.utils import (
    display_token_usage,
    load_user_preferences,
    save_user_preferences,
)

__all__ = [
    # Analyzer implementations
    "StandardCLIAnalyzer",
    "LLMEnhancedAnalyzer",
    # Core functionality
    "analyze_tool",
    "get_analyzer",
    "save_analysis_data",
    "validate_cli_tool_data",
    "Spinner",
    # Utility functions
    "display_token_usage",
    "save_user_preferences",
    "load_user_preferences",
]
