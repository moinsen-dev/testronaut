"""
OpenAI LLM Provider.

This module provides an implementation of the LLM provider interface
for the OpenAI API.
"""
import os
import json
from typing import Dict, List, Any, Optional, Union, cast

from testronaut.utils.errors import LLMServiceError
from testronaut.utils.logging import get_logger
from testronaut.utils.llm import LLMProviderRegistry

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
            raise ImportError(
                "OpenAI library not available. Install with 'pip install openai'"
            )

        self.client = None
        self.api_key = None
        self.organization = None
        self.model = "gpt-3.5-turbo"
        self.base_url = None

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the OpenAI provider with settings.

        Args:
            settings: Provider-specific settings.
        """
        # Get API key from settings or environment
        self.api_key = settings.get("api_key") or os.environ.get("OPENAI_API_KEY")

        if not self.api_key:
            raise LLMServiceError(
                "OpenAI API key not provided",
                details={
                    "solution": "Set 'api_key' in provider settings or the OPENAI_API_KEY environment variable"
                }
            )

        # Get optional settings
        self.organization = settings.get("organization") or os.environ.get("OPENAI_ORGANIZATION")
        self.model = settings.get("model", "gpt-3.5-turbo")
        self.base_url = settings.get("base_url")

        # Initialize the client
        try:
            client_kwargs = {"api_key": self.api_key}

            if self.organization:
                client_kwargs["organization"] = self.organization

            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            self.client = OpenAI(**client_kwargs)

            logger.info(
                "OpenAI provider initialized",
                model=self.model,
                has_organization=bool(self.organization),
                has_base_url=bool(self.base_url)
            )

        except Exception as e:
            raise LLMServiceError(
                "Failed to initialize OpenAI client",
                details={"error": str(e)}
            ) from e

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None
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
                details={"solution": "Call initialize() before generating text"}
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
                max_tokens=max_tokens
            )

            response = self.client.chat.completions.create(**params)

            # Extract the generated text
            if not response.choices:
                raise LLMServiceError(
                    "OpenAI returned no choices",
                    details={"response": str(response)}
                )

            generated_text = response.choices[0].message.content or ""

            return generated_text

        except openai.OpenAIError as e:
            raise LLMServiceError(
                "OpenAI API error",
                details={"error": str(e), "model": self.model}
            ) from e

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate text with OpenAI",
                details={"error": str(e), "model": self.model}
            ) from e

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from OpenAI models.

        Args:
            prompt: The user prompt to send to the model.
            schema: JSON schema defining the expected structure.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            Generated structured data conforming to the schema.
        """
        if not self.client:
            raise LLMServiceError(
                "OpenAI client not initialized",
                details={"solution": "Call initialize() before generating JSON"}
            )

        try:
            # Check if we can use OpenAI's native JSON mode
            # This is available for newer models like GPT-4 Turbo
            can_use_json_mode = any(model in self.model for model in [
                "gpt-4-turbo", "gpt-4-0125", "gpt-4-1106", "gpt-4-vision"
            ])

            if can_use_json_mode:
                # Use OpenAI's native JSON mode
                return self._generate_json_with_native_mode(prompt, schema, system_prompt, temperature)
            else:
                # Use system prompt instructions for JSON formatting
                return self._generate_json_with_instructions(prompt, schema, system_prompt, temperature)

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate JSON with OpenAI",
                details={"error": str(e), "model": self.model}
            ) from e

    def _generate_json_with_native_mode(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate structured JSON using OpenAI's native JSON mode.

        Args:
            prompt: The user prompt.
            schema: JSON schema.
            system_prompt: System prompt.
            temperature: Temperature setting.

        Returns:
            Generated JSON object.
        """
        # Create the system message with schema information
        base_system_prompt = system_prompt or "You are a helpful assistant that outputs JSON."

        # Add schema details to the system prompt
        formatted_schema = json.dumps(schema, indent=2)
        full_system_prompt = (
            f"{base_system_prompt}\n\n"
            f"You must respond with valid JSON that follows this schema:\n```json\n{formatted_schema}\n```\n"
            f"Do not include any explanations, only provide a valid JSON response."
        )

        # Prepare messages
        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": prompt}
        ]

        # Make the API call with response_format=json
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        # Extract and parse the JSON response
        content = response.choices[0].message.content
        if not content:
            raise LLMServiceError(
                "OpenAI returned empty content",
                details={"model": self.model}
            )

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMServiceError(
                "Failed to parse JSON response from OpenAI",
                details={"error": str(e), "content": content}
            ) from e

    def _generate_json_with_instructions(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate structured JSON using system prompt instructions.

        Args:
            prompt: The user prompt.
            schema: JSON schema.
            system_prompt: System prompt.
            temperature: Temperature setting.

        Returns:
            Generated JSON object.
        """
        # Create the system message with schema information
        base_system_prompt = system_prompt or "You are a helpful assistant that outputs JSON."

        # Add schema details to the system prompt
        formatted_schema = json.dumps(schema, indent=2)
        full_system_prompt = (
            f"{base_system_prompt}\n\n"
            f"You must respond with valid JSON that follows this schema:\n```json\n{formatted_schema}\n```\n"
            f"Do not include any explanations, only provide a valid JSON response that can be parsed by json.loads()."
        )

        # Generate the text that should contain JSON
        response_text = self.generate_text(
            prompt=prompt,
            system_prompt=full_system_prompt,
            temperature=temperature
        )

        # Clean the response to extract just the JSON part
        cleaned_response = self._extract_json_from_text(response_text)

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            # Log the error and response for debugging
            logger.error(
                "Failed to parse JSON response",
                error=str(e),
                response=response_text,
                cleaned_response=cleaned_response
            )

            # Make a second attempt with more explicit instructions
            retry_system_prompt = (
                "You must respond with ONLY valid JSON. No markdown formatting, no explanations, "
                "no code blocks. Just the raw, parseable JSON object. Your entire response should "
                "be valid JSON that can be parsed with json.loads()."
            )

            retry_prompt = (
                f"Generate JSON that matches this schema: {formatted_schema}\n\n"
                f"For this request: {prompt}\n\n"
                f"Respond with ONLY the JSON object, nothing else."
            )

            retry_response = self.generate_text(
                prompt=retry_prompt,
                system_prompt=retry_system_prompt,
                temperature=min(temperature, 0.1)  # Lower temperature for more deterministic output
            )

            # Clean up and retry parsing
            cleaned_retry = self._extract_json_from_text(retry_response)

            try:
                return json.loads(cleaned_retry)
            except json.JSONDecodeError as e2:
                raise LLMServiceError(
                    "Failed to parse JSON response after retry",
                    details={
                        "error": str(e2),
                        "original_response": response_text,
                        "retry_response": retry_response,
                        "cleaned_retry": cleaned_retry
                    }
                ) from e2

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
                return text[start_idx:last_brace_idx + 1]

        # If we couldn't find a better subset, just return the original text
        return text.strip()