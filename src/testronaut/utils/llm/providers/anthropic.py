"""
Anthropic LLM Provider for Claude.

This module provides an implementation of the LLM provider interface
for the Anthropic Claude API.
"""
import json
import os
from typing import Any, Dict, List, Optional

from testronaut.utils.errors import LLMServiceError
from testronaut.utils.llm import LLMProviderRegistry
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Import Anthropic library if available
try:
    import anthropic
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    logger.warning("Anthropic library not available. Install with 'pip install anthropic'")
    ANTHROPIC_AVAILABLE = False


@LLMProviderRegistry.register("anthropic")
class AnthropicProvider:
    """Anthropic Claude provider for interacting with Claude models."""

    def __init__(self):
        """Initialize the Anthropic provider."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic library not available. Install with 'pip install anthropic'"
            )

        self.client = None
        self.api_key = None
        self.model = "claude-3-haiku-20240307"  # Default to newest model

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the Anthropic provider with settings.

        Args:
            settings: Provider-specific settings.
        """
        # Get API key from settings or environment
        self.api_key = settings.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise LLMServiceError(
                "Anthropic API key not provided",
                details={
                    "solution": "Set 'api_key' in provider settings or the ANTHROPIC_API_KEY environment variable"
                }
            )

        # Get optional settings
        self.model = settings.get("model", "claude-3-haiku-20240307")

        # Initialize the client
        try:
            self.client = Anthropic(api_key=self.api_key)

            logger.info(
                "Anthropic provider initialized",
                model=self.model
            )

        except Exception as e:
            raise LLMServiceError(
                "Failed to initialize Anthropic client",
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
        Generate text from Claude based on a prompt.

        Args:
            prompt: The user prompt to send to the model.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 to 1.0).
            stop_sequences: Sequences that will stop generation.

        Returns:
            Generated text from Claude.
        """
        if not self.client:
            raise LLMServiceError(
                "Anthropic client not initialized",
                details={"solution": "Call initialize() before generating text"}
            )

        try:
            # Prepare parameters
            params: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens or 1024,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }

            # Add system prompt if provided
            if system_prompt:
                params["system"] = system_prompt

            # Add stop sequences if provided
            if stop_sequences:
                params["stop_sequences"] = stop_sequences

            # Generate completion
            logger.debug(
                "Sending request to Anthropic",
                model=self.model,
                temperature=temperature,
                max_tokens=params["max_tokens"]
            )

            response = self.client.messages.create(**params)

            # Extract the generated text
            if not response.content:
                raise LLMServiceError(
                    "Anthropic returned no content",
                    details={"response": str(response)}
                )

            # Extract the text content from the message content blocks
            generated_text = ""
            for content_block in response.content:
                if content_block.type == "text":
                    generated_text += content_block.text

            return generated_text

        except anthropic.AnthropicError as e:
            raise LLMServiceError(
                "Anthropic API error",
                details={"error": str(e), "model": self.model}
            ) from e

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate text with Anthropic",
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
        Generate structured JSON output from Claude models.

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
                "Anthropic client not initialized",
                details={"solution": "Call initialize() before generating JSON"}
            )

        try:
            # Create the system message with schema information
            base_system_prompt = system_prompt or "You are a helpful assistant that outputs JSON."

            # Add schema details to the system prompt
            formatted_schema = json.dumps(schema, indent=2)
            full_system_prompt = (
                f"{base_system_prompt}\n\n"
                f"You must respond with valid JSON that follows this schema:\n```json\n{formatted_schema}\n```\n"
                f"Do not include any explanations, only provide a valid JSON response that can be parsed by json.loads()."
            )

            # Create more specific user prompt
            json_prompt = (
                f"{prompt}\n\n"
                f"Provide your response as valid JSON only, with no other text."
            )

            # Generate the text that should contain JSON
            response_text = self.generate_text(
                prompt=json_prompt,
                system_prompt=full_system_prompt,
                temperature=temperature,
                max_tokens=4000  # Ensure we have enough tokens for complex JSON
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

        except Exception as e:
            raise LLMServiceError(
                "Failed to generate JSON with Anthropic",
                details={"error": str(e), "model": self.model}
            ) from e

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