"""
Base Protocol for LLM Providers.

This module defines the standard interface that all concrete LLM provider
implementations (e.g., OpenAI, LlamaCpp) must adhere to.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class BaseLLMProvider(Protocol):
    """Protocol defining the required interface for LLM providers."""

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the LLM provider with its specific settings.

        This method is called by the LLMService or Manager after the provider
        instance is created.

        Args:
            settings: A dictionary containing provider-specific configuration
                      extracted from the main application settings (e.g., API keys,
                      model paths, specific parameters).
        """
        ...

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any, # Allow for additional provider-specific args
    ) -> str:
        """
        Generate text from the LLM based on a prompt.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt for context or instructions.
            max_tokens: Optional maximum number of tokens to generate. If None,
                        a provider-specific or globally configured default may be used.
            temperature: Sampling temperature (typically 0.0 to 1.0 or higher).
                         Controls randomness. Lower values are more deterministic.
            stop_sequences: Optional list of strings that, if generated, will
                            cause the generation process to stop.
            **kwargs: Catch-all for additional provider-specific parameters.

        Returns:
            The generated text as a string.

        Raises:
            LLMServiceError: If the generation fails due to API errors,
                             connection issues, or other provider problems.
        """
        ...

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any, # Allow for additional provider-specific args
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from the LLM based on a prompt and schema.

        Not all providers may support native JSON mode. Implementations might
        need to use specific prompting techniques or post-processing if native
        support is lacking.

        Args:
            prompt: The user prompt designed to elicit a JSON response.
            schema: A JSON schema dictionary defining the expected structure
                    of the output.
            system_prompt: Optional system prompt for context or instructions,
                           potentially emphasizing the JSON output requirement.
            temperature: Sampling temperature, often lower for structured output
                         to ensure adherence to the schema.
            **kwargs: Catch-all for additional provider-specific parameters.

        Returns:
            A dictionary representing the generated structured data, ideally
            conforming to the provided schema.

        Raises:
            LLMServiceError: If JSON generation fails, cannot be parsed, or
                             if the provider encounters an error.
            NotImplementedError: If the provider does not support JSON generation.
        """
        ...

    # --- Optional Methods (Providers can implement if applicable) ---

    # def get_embedding(self, text: str, **kwargs: Any) -> List[float]:
    #     """Generate a vector embedding for the given text."""
    #     ...

    # --- Optional Attributes (Providers might expose) ---
    # last_token_usage: Optional[Dict[str, int]] = None # Example: {'prompt_tokens': 10, 'completion_tokens': 50, 'total_tokens': 60}
