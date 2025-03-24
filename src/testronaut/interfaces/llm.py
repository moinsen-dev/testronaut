"""
LLM Manager Interface.

This module defines the interface for interacting with Language Learning Models.
"""
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMManager(Protocol):
    """Protocol defining the interface for LLM managers."""

    def initialize(self, provider: str, **config) -> bool:
        """
        Initialize the LLM manager with a specific provider.

        Args:
            provider: The LLM provider to use (e.g., "openai", "anthropic", "local").
            **config: Provider-specific configuration parameters.

        Returns:
            True if initialization was successful, False otherwise.

        Raises:
            ConfigurationError: If the configuration is invalid.
            LLMServiceError: If the LLM service cannot be initialized.
        """
        ...

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text using the LLM.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: The sampling temperature (0.0 to 1.0).
            max_tokens: The maximum number of tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated text.

        Raises:
            LLMServiceError: If the text generation fails.
        """
        ...

    def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> Dict[str, float]:
        """
        Classify text into predefined categories.

        Args:
            text: The text to classify.
            categories: The list of categories to classify into.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A dictionary mapping categories to confidence scores.

        Raises:
            LLMServiceError: If the classification fails.
        """
        ...

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract structured data from text according to a schema.

        Args:
            text: The text to extract data from.
            schema: The schema defining the structured data.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A dictionary with extracted data according to the schema.

        Raises:
            LLMServiceError: If the extraction fails.
        """
        ...

    def analyze_help_text(
        self,
        help_text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze CLI help text to extract commands, options, and arguments.

        Args:
            help_text: The help text to analyze.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A dictionary with structured information about commands, options, and arguments.

        Raises:
            LLMServiceError: If the analysis fails.
        """
        ...

    def get_embedding(
        self,
        text: str,
        **kwargs
    ) -> List[float]:
        """
        Get vector embedding for text.

        Args:
            text: The text to get an embedding for.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A list of floating-point values representing the text embedding.

        Raises:
            LLMServiceError: If the embedding generation fails.
        """
        ...

    def compare_outputs(
        self,
        expected: str,
        actual: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Compare expected and actual outputs semantically.

        Args:
            expected: The expected output text.
            actual: The actual output text.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A dictionary with comparison results, including similarity score.

        Raises:
            LLMServiceError: If the comparison fails.
        """
        ...