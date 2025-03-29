"""
LLM Utilities Package.

This package provides core components for interacting with Large Language Models (LLMs),
including the service facade, provider registry, and potentially other utilities
like prompt management or result processing if not refactored elsewhere.
"""

# Import key components from submodules to expose them at the package level
from .registry import LLMProviderRegistry
from .service import LLMService

# Optionally import other utilities if they belong here
# from .prompts import ...
# from .result_processor import ...

# Define the public API of this package
__all__ = [
    "LLMService",
    "LLMProviderRegistry",
    # Add other imported utilities here if needed
]
