"""
LLM Provider implementation using llama-cpp-python.
"""
from typing import Any, Dict, List

# Attempt to import Llama from llama_cpp, but handle ImportError
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None  # Set Llama to None if llama_cpp is not installed

from testronaut.utils.errors import LLMServiceError, ConfigurationError


class LlamaCppProvider:
    """
    LLM Provider implementation that uses llama-cpp-python to run local models.
    """

    def __init__(self, model_path: str, **kwargs):
        """
        Initialize the LlamaCppProvider.

        Args:
            model_path: Path to the GGUF model file.
            **kwargs: Additional parameters for llama_cpp.Llama initialization
                      (e.g., n_ctx, n_gpu_layers, verbose).
        """
        if Llama is None:
            raise ConfigurationError(
                "llama-cpp-python is not installed. "
                "Please install it to use the LlamaCppProvider: "
                "pip install testronaut[local-llm]"
            )

        self.model_path = model_path
        self.llama_kwargs = kwargs
        self.llm: "Llama" = None # Use string literal for type hint

        try:
            print(f"Loading Llama model from: {self.model_path}")
            print(f"Llama params: {self.llama_kwargs}")
            # Ensure verbose is explicitly passed if present, default to True for debugging
            verbose = self.llama_kwargs.get('verbose', True)
            self.llm = Llama(model_path=self.model_path, verbose=verbose, **self.llama_kwargs)
            print("Llama model loaded successfully.")
        except Exception as e:
            raise ConfigurationError(f"Failed to load Llama model from {self.model_path}: {e}") from e

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 512, # Default for local models might be lower
        **kwargs
    ) -> str:
        """
        Generate text using the loaded Llama model.

        Args:
            prompt: The prompt to send to the model.
            temperature: The sampling temperature.
            max_tokens: The maximum number of tokens to generate.
            **kwargs: Additional parameters for the Llama.create_completion call.

        Returns:
            The generated text.
        """
        if self.llm is None:
            raise LLMServiceError("Llama model is not loaded.")

        try:
            # Combine default and specific kwargs
            completion_kwargs = {
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            print(f"Generating completion with prompt (first 100 chars): {prompt[:100]}...")
            print(f"Completion params: {completion_kwargs}")

            response = self.llm.create_completion(
                prompt=prompt,
                **completion_kwargs
            )

            generated_text = response['choices'][0]['text']
            print(f"Generated text (first 100 chars): {generated_text[:100]}...")
            return generated_text.strip()
        except Exception as e:
            raise LLMServiceError(f"Llama model text generation failed: {e}") from e

    # --- Methods below need implementation based on llama-cpp capabilities ---
    # These might be implemented by formatting prompts for the generate_text method
    # or by using specific llama-cpp features if available.

    def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> Dict[str, float]:
        """Classify text (requires specific prompting strategy)."""
        # TODO: Implement using generate_text with a classification prompt
        raise NotImplementedError("classify not yet implemented for LlamaCppProvider.")

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured data (requires specific prompting strategy)."""
        # TODO: Implement using generate_text with a structured data extraction prompt
        raise NotImplementedError("extract_structured_data not yet implemented for LlamaCppProvider.")

    def analyze_help_text(
        self,
        help_text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze CLI help text (requires specific prompting strategy)."""
        # TODO: Implement using generate_text with a help text analysis prompt
        raise NotImplementedError("analyze_help_text not yet implemented for LlamaCppProvider.")

    def get_embedding(
        self,
        text: str,
        **kwargs
    ) -> List[float]:
        """Get text embedding (if the loaded model supports it)."""
        if self.llm is None:
            raise LLMServiceError("Llama model is not loaded.")
        if not hasattr(self.llm, 'embed'):
             raise NotImplementedError("Embedding is not supported by this Llama model or llama-cpp version.")

        try:
            print(f"Generating embedding for text (first 100 chars): {text[:100]}...")
            embedding = self.llm.embed(text)
            print(f"Embedding generated with dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            raise LLMServiceError(f"Llama model embedding generation failed: {e}") from e


    def compare_outputs(
        self,
        expected: str,
        actual: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Compare outputs semantically (requires specific prompting strategy)."""
        # TODO: Implement using generate_text with a comparison prompt
        raise NotImplementedError("compare_outputs not yet implemented for LlamaCppProvider.")
