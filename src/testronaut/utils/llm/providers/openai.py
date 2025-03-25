"""
OpenAI LLM Provider.

This module provides an implementation of the LLM provider interface
for the OpenAI API.
"""

import json
import os
from typing import Any, Dict, List, Optional

from testronaut.utils.errors import LLMServiceError
from testronaut.utils.llm import LLMProviderRegistry
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Import OpenAI library if available
try:
    import openai
    from openai import OpenAI
    from openai.types.chat import ChatCompletion

    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI library not available. Install with 'pip install openai'")
    OPENAI_AVAILABLE = False


@LLMProviderRegistry.register("openai")
class OpenAIProvider:
    """OpenAI LLM provider for interacting with OpenAI models."""

    def __init__(self):
        """Initialize the OpenAI provider."""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available. Install with 'pip install openai'")

        self.client = None
        self.api_key = None
        self.organization = None
        self.model = "gpt-3.5-turbo"
        self.base_url = None
        self.last_token_usage = None

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the OpenAI provider with settings.

        Args:
            settings: Provider-specific settings.
        """
        # Store provider settings for later use
        self._provider_settings = settings

        # Get API key from settings or environment
        self.api_key = settings.get("api_key") or os.environ.get("OPENAI_API_KEY")

        if not self.api_key:
            raise LLMServiceError(
                "OpenAI API key not provided",
                details={
                    "solution": "Set 'api_key' in provider settings or the OPENAI_API_KEY environment variable"
                },
            )

        # Get optional settings
        self.organization = settings.get("organization") or os.environ.get("OPENAI_ORGANIZATION")

        # Get the model from settings or use default
        self.model = settings.get("model")
        if not self.model:
            models = settings.get("models", {})
            self.model = models.get("default", "gpt-3.5-turbo")

        self.base_url = settings.get("base_url")

        # Initialize the client
        try:
            client_kwargs = {"api_key": self.api_key}

            if self.organization:
                client_kwargs["organization"] = self.organization

            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            self.client = OpenAI(**client_kwargs)

            logger.info("Initialized OpenAI provider", model=self.model)

        except Exception as e:
            raise LLMServiceError(
                "Failed to initialize OpenAI client", details={"error": str(e)}
            ) from e

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text from OpenAI models based on a prompt.

        Args:
            prompt: The user prompt to send to the model.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 to 1.0).
            stop_sequences: Sequences that will stop generation.

        Returns:
            Generated text from the OpenAI model.
        """
        if not self.client:
            raise LLMServiceError(
                "OpenAI client not initialized",
                details={"solution": "Call initialize() before generating text"},
            )

        try:
            # Prepare messages
            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add user message
            messages.append({"role": "user", "content": prompt})

            # Prepare parameters
            params: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            # Add optional parameters
            if max_tokens:
                params["max_tokens"] = max_tokens

            if stop_sequences:
                params["stop"] = stop_sequences

            # Generate completion
            logger.debug(
                "Sending request to OpenAI",
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = self.client.chat.completions.create(**params)

            # Track token usage
            self.last_token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "model": self.model
            }

            logger.debug(
                f"OpenAI token usage: {self.last_token_usage['total_tokens']} tokens "
                f"({self.last_token_usage['prompt_tokens']} prompt, "
                f"{self.last_token_usage['completion_tokens']} completion)"
            )

            # Extract the generated text
            if not response.choices:
                raise LLMServiceError(
                    "OpenAI returned no choices", details={"response": str(response)}
                )

            generated_text = response.choices[0].message.content or ""

            return generated_text

        except openai.OpenAIError as e:
            raise LLMServiceError(
                "OpenAI API error", details={"error": str(e), "model": self.model}
            ) from e

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate text with OpenAI",
                details={"error": str(e), "model": self.model},
            ) from e

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from the LLM based on a prompt and schema.

        Args:
            prompt: The user prompt to send to the LLM.
            schema: JSON schema defining the expected structure.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            Generated structured data conforming to the schema.
        """
        try:
            # Get model specific information from provider settings
            # Use a model from provider settings if available
            provider_settings = getattr(self, "_provider_settings", {}) or {}
            models = provider_settings.get("models", {})
            json_model = models.get("json")

            # Override self.model specifically for this call if json model is configured
            current_model = self.model
            if json_model:
                self.model = json_model

            try:
                # First try with native JSON mode
                if self._model_supports_json_mode(self.model):
                    return self._generate_json_with_native_mode(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
                else:
                    # Fall back to instruction-based approach
                    return self._generate_json_with_instructions(
                        prompt=prompt,
                        schema=schema,
                        system_prompt=system_prompt,
                        temperature=temperature,
                    )
            finally:
                # Restore the original model
                self.model = current_model

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate JSON with OpenAI", details={"error": str(e)}
            ) from e

    def _model_supports_json_mode(self, model: str) -> bool:
        """
        Determine if a model supports native JSON mode.

        Args:
            model: The model name to check

        Returns:
            True if the model supports native JSON mode
        """
        # Models that support native JSON mode
        json_mode_models = [
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4-0125",
            "gpt-4-1106",
            "gpt-4-vision",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-0125",
        ]

        # Check if any of the supported model names are in the provided model name
        return any(supported_model in model for supported_model in json_mode_models)

    def _generate_json_with_native_mode(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate JSON using the OpenAI native JSON mode.

        Args:
            prompt: The user prompt.
            schema: The JSON schema to validate against.
            system_prompt: Optional system prompt.
            temperature: The temperature to use.

        Returns:
            The generated JSON object.
        """
        if not self.client:
            raise LLMServiceError(
                "OpenAI client not initialized",
                details={"solution": "Call initialize() before generating JSON"},
            )

        try:
            # Prepare messages
            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Default system message for JSON generation
                messages.append(
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that outputs valid JSON according to the provided schema.",
                    }
                )

            # Add user message with the schema
            schema_json = json.dumps(schema, indent=2)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n"
                        f"Return your response as a JSON object that conforms to this schema:\n"
                        f"```json\n{schema_json}\n```"
                    ),
                }
            )

            # Generate completion with JSON mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )

            # Track token usage
            self.last_token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "model": self.model
            }

            logger.debug(
                f"OpenAI token usage: {self.last_token_usage['total_tokens']} tokens "
                f"({self.last_token_usage['prompt_tokens']} prompt, "
                f"{self.last_token_usage['completion_tokens']} completion)"
            )

            # Extract the generated text
            if not response.choices:
                raise LLMServiceError(
                    "OpenAI returned no choices", details={"response": str(response)}
                )

            content = response.choices[0].message.content or ""

            # Parse the JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMServiceError(
                    "OpenAI returned invalid JSON",
                    details={"error": str(e), "content": content},
                )

    def _generate_json_with_instructions(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate JSON using instructions when native JSON mode is not available.

        Args:
            prompt: The user prompt.
            schema: The JSON schema to validate against.
            system_prompt: Optional system prompt.
            temperature: The temperature to use.

        Returns:
            The generated JSON object.
        """
        if not self.client:
            raise LLMServiceError(
                "OpenAI client not initialized",
                details={"solution": "Call initialize() before generating JSON"},
            )

        try:
            # Prepare messages
            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Default system message for JSON generation
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that outputs valid JSON according to the provided schema. "
                            "Respond ONLY with the JSON object and no additional text, explanations, or markdown formatting."
                        ),
                    }
                )

            # Add user message with the schema
            schema_json = json.dumps(schema, indent=2)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n"
                        f"Return your response as a JSON object that conforms to this schema:\n"
                        f"```json\n{schema_json}\n```\n\n"
                        f"Important: Respond ONLY with the JSON object and no other text. "
                        f"Do not include markdown formatting or code blocks in your response."
                    ),
                }
            )

            # Generate completion
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=temperature
            )

            # Track token usage
            self.last_token_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "model": self.model
            }

            logger.debug(
                f"OpenAI token usage: {self.last_token_usage['total_tokens']} tokens "
                f"({self.last_token_usage['prompt_tokens']} prompt, "
                f"{self.last_token_usage['completion_tokens']} completion)"
            )

            # Extract the generated text
            if not response.choices:
                raise LLMServiceError(
                    "OpenAI returned no choices", details={"response": str(response)}
                )

            content = response.choices[0].message.content or ""

            # Try to extract JSON from the text
            return self._extract_json_from_text(content)

    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON from text that might contain explanations or markdown.

        Args:
            text: The text potentially containing JSON.

        Returns:
            Cleaned JSON string.
        """
        # Look for JSON within code blocks
        if "```json" in text and "```" in text.split("```json", 1)[1]:
            parts = text.split("```json", 1)[1].split("```", 1)
            if parts:
                return parts[0].strip()

        if "```" in text and "```" in text.split("```", 1)[1]:
            parts = text.split("```", 1)[1].split("```", 1)
            if parts:
                return parts[0].strip()

        # Try to find JSON object using braces
        if "{" in text and "}" in text:
            start_idx = text.find("{")
            # Find the last closing brace
            last_brace_idx = text.rfind("}")
            if last_brace_idx > start_idx:
                return text[start_idx : last_brace_idx + 1]

        # If we couldn't find a better subset, just return the original text
        return text.strip()
