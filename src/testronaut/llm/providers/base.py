"""
Base definitions for LLM providers.
"""
from typing import Protocol, runtime_checkable

@runtime_checkable
class BaseLLMProvider(Protocol):
    """Base protocol that all LLM providers should implement."""

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text based on a prompt."""
        ...

    # Add other common provider methods here if needed in the future,
    # e.g., get_embedding, if most providers support it directly.
    # For now, only generate_text is assumed as the core requirement.
