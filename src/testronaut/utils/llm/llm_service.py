"""
LLM Service

This module provides a service for interacting with LLM providers.
"""

import json
import time
from typing import Any, Dict, Optional

from testronaut.config import Settings
from testronaut.factory import registry
from testronaut.utils.errors import LLMServiceError, ValidationError
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class LLMService:
    """Service for interacting with LLM providers."""

    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize the LLM service.

        Args:
            provider_name: Optional name of the LLM provider to use.
                If not specified, the default provider from settings is used.
        """
        self.settings = Settings()
        self.provider_name = provider_name or self.settings.llm.provider
        logger.debug(f"Initializing LLM service with provider: {self.provider_name}")

        # Get provider factory
        provider_factory = registry.get_factory("llm_provider")
        if not provider_factory:
            raise LLMServiceError("LLM provider factory not registered")

        # Create provider
        try:
            self.provider = provider_factory.create(self.provider_name)
            logger.debug(f"Created LLM provider: {self.provider_name}")
        except Exception as e:
            logger.error(f"Failed to create LLM provider {self.provider_name}: {str(e)}")
            raise LLMServiceError(f"Failed to create LLM provider: {str(e)}")

    def generate_text(self, prompt: str, model: Optional[str] = None, task: str = "general") -> str:
        """
        Generate text using the LLM provider.

        Args:
            prompt: The prompt to send to the LLM.
            model: Optional specific model to use. If not specified,
                the default model for the task from settings is used.
            task: The task for which text is being generated.
                Used to select the appropriate model.

        Returns:
            The generated text.

        Raises:
            LLMServiceError: If the LLM service fails.
        """
        logger.debug(f"Generating text for task: {task}")
        start_time = time.time()

        # Truncate prompt for logging to avoid huge logs
        short_prompt = prompt[:150] + "..." if len(prompt) > 150 else prompt
        logger.debug(f"Prompt: {short_prompt}")

        # Get the model to use
        model_to_use = self._get_model_for_task(model, task)
        logger.debug(f"Using model: {model_to_use}")

        try:
            response = self.provider.generate_text(prompt, model=model_to_use)
            elapsed_time = time.time() - start_time
            logger.debug(f"Text generation completed in {elapsed_time:.2f} seconds")
            return response
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Text generation failed after {elapsed_time:.2f} seconds: {str(e)}")
            raise LLMServiceError(f"Failed to generate text: {str(e)}")

    def generate_json(
        self, prompt: str, schema: Dict[str, Any], model: Optional[str] = None, task: str = "json"
    ) -> Any:
        """
        Generate structured JSON data using the LLM provider.

        Args:
            prompt: The prompt to send to the LLM.
            schema: The JSON schema to validate the response against.
            model: Optional specific model to use. If not specified,
                the default model for the task from settings is used.
            task: The task for which JSON is being generated.
                Used to select the appropriate model.

        Returns:
            The generated data as a Python object.

        Raises:
            LLMServiceError: If the LLM service fails.
            ValidationError: If the generated JSON cannot be validated against the schema.
        """
        logger.debug(f"Generating JSON for task: {task}")
        start_time = time.time()

        # Truncate prompt for logging to avoid huge logs
        short_prompt = prompt[:150] + "..." if len(prompt) > 150 else prompt
        logger.debug(f"Prompt: {short_prompt}")

        # Get the model to use
        model_to_use = self._get_model_for_task(model, task)
        logger.debug(f"Using model: {model_to_use}")

        # Check if provider supports native JSON generation
        if hasattr(self.provider, "generate_json") and callable(self.provider.generate_json):
            try:
                json_data = self.provider.generate_json(prompt, schema, model=model_to_use)
                elapsed_time = time.time() - start_time
                logger.debug(f"JSON generation completed in {elapsed_time:.2f} seconds")
                # Quick validation - check that we got valid JSON
                self._validate_json_structure(json_data, schema)
                return json_data
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.warning(
                    f"Native JSON generation failed after {elapsed_time:.2f} seconds: {str(e)}"
                )
                # Fall back to text generation
                logger.debug("Falling back to text generation with JSON extraction")
        else:
            logger.debug("Provider doesn't support native JSON generation, using text generation")

        # Use text generation with additional JSON instructions
        json_prompt = self._create_json_prompt(prompt, schema)

        try:
            start_text_time = time.time()
            text_response = self.provider.generate_text(json_prompt, model=model_to_use)
            text_elapsed = time.time() - start_text_time
            logger.debug(f"Text generation for JSON completed in {text_elapsed:.2f} seconds")

            # Extract JSON from text
            start_extract_time = time.time()
            json_data = self._extract_json_from_text(text_response)
            extract_elapsed = time.time() - start_extract_time
            logger.debug(f"JSON extraction completed in {extract_elapsed:.2f} seconds")

            # Validate against schema
            self._validate_json_structure(json_data, schema)

            total_elapsed = time.time() - start_time
            logger.debug(f"Total JSON generation completed in {total_elapsed:.2f} seconds")
            return json_data
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"JSON generation failed after {elapsed_time:.2f} seconds: {str(e)}")
            raise LLMServiceError(f"Failed to generate JSON: {str(e)}")

    def _get_model_for_task(self, model: Optional[str], task: str) -> str:
        """
        Get the model to use for a specific task.

        Args:
            model: Optional specific model to use.
            task: The task for which the model is needed.

        Returns:
            The model to use.
        """
        if model:
            return model

        # Get provider settings
        provider_settings = self.settings.llm.current_provider_settings
        models = provider_settings.get("models", {})

        # First check if there's a specific model for this task
        if task in models:
            return models[task]

        # Fall back to default model
        if "default" in models:
            return models["default"]

        # Fall back to global model setting
        return self.settings.llm.model

    def _create_json_prompt(self, prompt: str, schema: Dict[str, Any]) -> str:
        """
        Create a prompt for generating JSON data.

        Args:
            prompt: The original prompt.
            schema: The JSON schema.

        Returns:
            A prompt for generating JSON data.
        """
        return f"""
        {prompt}

        Important: Your response must be valid JSON data conforming to the following schema:
        ```json
        {json.dumps(schema, indent=2)}
        ```

        Respond ONLY with the JSON data, no preamble or explanation.
        Ensure all property names and values are properly quoted according to JSON syntax.
        """

    def _extract_json_from_text(self, text: str) -> Any:
        """
        Extract JSON data from text.

        Args:
            text: The text containing JSON data.

        Returns:
            The extracted JSON data.

        Raises:
            ValidationError: If JSON cannot be extracted.
        """
        # Try to find JSON blocks in the text
        json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        import re

        json_matches = re.findall(json_pattern, text)

        # If we found JSON blocks, try each one
        if json_matches:
            for match in json_matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # If no JSON blocks, try the entire text
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to fix common JSON errors
            clean_text = self._clean_json_text(text)
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Failed to extract JSON from text: {str(e)}")

    def _clean_json_text(self, text: str) -> str:
        """
        Clean JSON text by fixing common errors.

        Args:
            text: The text to clean.

        Returns:
            The cleaned text.
        """
        # Remove all lines before the first { or [ and after the last } or ]
        start_idx = min(
            text.find("{") if text.find("{") != -1 else len(text),
            text.find("[") if text.find("[") != -1 else len(text),
        )
        end_idx = max(
            text.rfind("}") if text.rfind("}") != -1 else 0,
            text.rfind("]") if text.rfind("]") != -1 else 0,
        )

        if start_idx < end_idx:
            text = text[start_idx : end_idx + 1]

        return text

    def _validate_json_structure(self, data: Any, schema: Dict[str, Any]) -> None:
        """
        Validate JSON data against a schema.

        Args:
            data: The data to validate.
            schema: The schema to validate against.

        Raises:
            ValidationError: If the data does not match the schema.
        """
        # Simple validation of basic structure
        schema_type = schema.get("type")

        if schema_type == "object":
            if not isinstance(data, dict):
                raise ValidationError(f"Expected object, got {type(data)}")

            # Check required properties
            required = schema.get("required", [])
            for prop in required:
                if prop not in data:
                    raise ValidationError(f"Missing required property: {prop}")

        elif schema_type == "array":
            if not isinstance(data, list):
                raise ValidationError(f"Expected array, got {type(data)}")

        # More sophisticated validation could be added here
        logger.debug("JSON validation passed")
