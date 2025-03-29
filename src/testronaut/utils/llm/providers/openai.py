"""
OpenAI provider for the LLM service.

This module implements the OpenAI provider for the LLM service.
"""

import json
from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

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
    """OpenAI provider for the LLM service."""

    def __init__(self) -> None:
        """Initialize the OpenAI provider."""
        self.api_key: Optional[str] = None
        self.model: str = "gpt-4"
        self.temperature: float = 0.7
        self.max_tokens: Optional[int] = None
        self.default_system_prompt: Optional[str] = None
        self.client: Optional[OpenAI] = None
        self.last_token_usage: Optional[Dict[str, Any]] = None

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the OpenAI provider with settings.

        Args:
            settings: Provider-specific settings.
        """
        self.api_key = settings.get("api_key")
        self.model = settings.get("models", {}).get("default", "gpt-4")
        self.temperature = settings.get("temperature", 0.7)
        self.max_tokens = settings.get("max_tokens")
        self.default_system_prompt = settings.get("default_system_prompt")

        try:
            # Check if OpenAI is available
            if not OPENAI_AVAILABLE:
                logger.error("OpenAI library not available. Install with 'pip install openai'")
                return

            # Add more logging for client initialization
            logger.info(f"Initializing OpenAI client with model: {self.model}")

            # Explicitly log API key presence (not the actual key)
            if self.api_key:
                logger.info("Using provided API key")
            else:
                logger.info("No API key provided, will use OPENAI_API_KEY environment variable")

            # Initialize client
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
            raise LLMServiceError(f"Failed to initialize OpenAI client: {e}")

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate the cost of a request based on token usage.

        Args:
            model: The model used for the request
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Pricing as of May 2023 - update as needed
        pricing = {
            "gpt-4": {
                "input": 30.0 / 1_000_000,  # $30 per 1M tokens
                "output": 60.0 / 1_000_000,  # $60 per 1M tokens
            },
            "gpt-4-turbo": {
                "input": 10.0 / 1_000_000,  # $10 per 1M tokens
                "output": 30.0 / 1_000_000,  # $30 per 1M tokens
            },
            "gpt-3.5-turbo": {
                "input": 0.5 / 1_000_000,  # $0.50 per 1M tokens
                "output": 1.5 / 1_000_000,  # $1.50 per 1M tokens
            },
        }

        # Get pricing data for the model, defaulting to gpt-4 if not found
        model_pricing = pricing.get(model, pricing["gpt-4"])

        # Calculate cost
        input_cost = input_tokens * model_pricing["input"]
        output_cost = output_tokens * model_pricing["output"]

        return input_cost + output_cost

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text from a prompt using OpenAI.

        Args:
            prompt: Prompt to generate text from.
            system_prompt: System prompt to use. If not provided, default_system_prompt is used.
            max_tokens: Maximum number of tokens to generate.
            temperature: Temperature to use.
            stop_sequences: Sequences that will stop generation.

        Returns:
            Generated text.

        Raises:
            LLMServiceError: If there was an error generating text.
        """
        if self.client is None:
            raise LLMServiceError("OpenAI client not initialized")

        # Build messages
        messages: List[ChatCompletionMessageParam] = []

        # Add system prompt if provided
        _system_prompt = system_prompt or self.default_system_prompt
        if _system_prompt:
            messages.append({"role": "system", "content": _system_prompt})

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        # Get parameters
        _temperature = temperature or self.temperature
        _max_tokens = max_tokens or self.max_tokens
        _model = self.model

        # Generate text
        try:
            logger.debug(f"Generating text with OpenAI using model {_model}")
            response = self.client.chat.completions.create(
                model=_model,
                messages=messages,
                temperature=_temperature,
                max_tokens=_max_tokens if _max_tokens is not None else None,
                stop=stop_sequences,
            )

            # Track token usage
            if hasattr(response, "usage") and response.usage is not None:
                usage = response.usage
                model_name = _model

                self.last_token_usage = {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "model": model_name,
                    "estimated_cost": self._calculate_cost(
                        model_name, usage.prompt_tokens, usage.completion_tokens
                    ),
                }

                logger.debug(
                    f"Token usage - Prompt: {usage.prompt_tokens}, "
                    f"Completion: {usage.completion_tokens}, "
                    f"Total: {usage.total_tokens}"
                )
            else:
                self.last_token_usage = None

            if not response.choices:
                logger.error("No choices returned from OpenAI")
                raise LLMServiceError("No choices returned from OpenAI")

            return response.choices[0].message.content or ""
        except openai.OpenAIError as e:
            logger.error(f"Error generating text with OpenAI: {e}")
            raise LLMServiceError(f"Error generating text with OpenAI: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating text with OpenAI: {e}")
            raise LLMServiceError(f"Unexpected error generating text with OpenAI: {e}")

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generate JSON from a prompt using OpenAI.

        Args:
            prompt: Prompt to generate JSON from.
            schema: JSON schema to use for generation.
            system_prompt: System prompt to use. If not provided, default_system_prompt is used.
            temperature: Temperature to use.

        Returns:
            Generated JSON.

        Raises:
            LLMServiceError: If there was an error generating JSON.
        """
        if self.client is None:
            raise LLMServiceError("OpenAI client not initialized")

        # Build messages
        messages: List[ChatCompletionMessageParam] = []

        # Build system prompt
        _system_prompt = system_prompt or self.default_system_prompt or ""
        json_instruction = (
            "You are a helpful assistant that responds with JSON.\n"
            "Your response will be parsed by a machine, so it's crucial that you only provide a valid JSON object.\n"
            "Do not include explanations, notes, or anything that is not the JSON response.\n"
        )

        # Add schema information
        schema_instruction = "The JSON should follow this schema:\n"
        schema_instruction += json.dumps(schema, indent=2)

        # Combine system prompts
        combined_system_prompt = (
            f"{json_instruction}\n{schema_instruction}\n\n{_system_prompt}"
        ).strip()

        # Add system prompt
        messages.append({"role": "system", "content": combined_system_prompt})

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        # Get parameters
        _temperature = temperature or self.temperature
        _max_tokens = self.max_tokens
        _model = self.model

        try:
            logger.debug(f"Generating JSON with OpenAI using model {_model}")

            # Only use response_format for supported models
            kwargs: Dict[str, Any] = {
                "model": _model,
                "messages": messages,
                "temperature": _temperature,
            }

            if _max_tokens is not None:
                kwargs["max_tokens"] = _max_tokens

            # Only use response_format for supported models
            if _model in ["gpt-4-turbo", "gpt-3.5-turbo"]:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)

            # Track token usage
            if hasattr(response, "usage") and response.usage is not None:
                usage = response.usage
                model_name = _model

                self.last_token_usage = {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "model": model_name,
                    "estimated_cost": self._calculate_cost(
                        model_name, usage.prompt_tokens, usage.completion_tokens
                    ),
                }

                logger.debug(
                    f"Token usage - Prompt: {usage.prompt_tokens}, "
                    f"Completion: {usage.completion_tokens}, "
                    f"Total: {usage.total_tokens}"
                )
            else:
                self.last_token_usage = None

            if not response.choices:
                logger.error("No choices returned from OpenAI")
                raise LLMServiceError("No choices returned from OpenAI")

            content = response.choices[0].message.content or ""

            try:
                result: Dict[str, Any] = json.loads(content)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from OpenAI: {e}")
                logger.debug(f"Raw content: {content}")
                raise LLMServiceError(f"Error parsing JSON from OpenAI: {e}")
        except openai.OpenAIError as e:
            logger.error(f"Error generating JSON with OpenAI: {e}")
            raise LLMServiceError(f"Error generating JSON with OpenAI: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating JSON with OpenAI: {e}")
            raise LLMServiceError(f"Unexpected error generating JSON with OpenAI: {e}")
