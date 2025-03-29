"""
Mock LLM Provider for testing and default initialization.
"""
from typing import Any, Dict, List

from testronaut.llm.providers.base import BaseLLMProvider
from testronaut.utils.errors import LLMServiceError


class MockProvider(BaseLLMProvider):
    """
    A mock LLM provider that returns predefined responses.
    Useful for testing or when no real provider is configured.
    """

    def __init__(self, **kwargs):
        """Initialize the MockProvider."""
        print("Initialized MockProvider.")
        # Mock provider might not need specific config, but accept kwargs
        self.config = kwargs

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 50,
        **kwargs
    ) -> str:
        """Return a mock text response."""
        print(f"MockProvider received prompt (first 50 chars): {prompt[:50]}...")
        return f"[Mock Response] Received prompt: '{prompt[:30]}...'. Test successful!"

    # Add mock implementations or raise NotImplementedError for other methods
    # defined in BaseLLMProvider or expected by LLMManager if needed.
    # For now, only generate_text is strictly required by the BaseLLMProvider protocol.

    # Example for other methods if they were in BaseLLMProvider:
    # def get_embedding(self, text: str, **kwargs) -> List[float]:
    #     print(f"MockProvider received text for embedding: {text[:50]}...")
    #     # Return a fixed-size list of zeros or random numbers
    #     return [0.0] * 128 # Example dimension
