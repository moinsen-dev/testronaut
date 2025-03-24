"""
Mock LLM Provider for testing and development.

This module provides a mock implementation of the LLM provider interface
that returns predefined responses for testing.
"""
import json
import random
from typing import Dict, List, Any, Optional

from testronaut.utils.llm import LLMProviderRegistry


@LLMProviderRegistry.register("mock")
class MockProvider:
    """Mock LLM provider for testing and development."""

    def __init__(self):
        """Initialize the mock provider."""
        self.settings = {}
        self.predefined_responses = {}

    def initialize(self, settings: Dict[str, Any]) -> None:
        """
        Initialize the mock provider with settings.

        Args:
            settings: Provider-specific settings.
        """
        self.settings = settings
        self.predefined_responses = settings.get("predefined_responses", {})

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """
        Generate text from the mock LLM based on a prompt.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature (0.0 to 1.0).
            stop_sequences: Sequences that will stop generation.

        Returns:
            Generated text from the mock LLM.
        """
        # Check for predefined responses
        for key, response in self.predefined_responses.items():
            if key in prompt:
                return response

        # Generate a basic mock response
        return self._generate_mock_response(prompt, system_prompt, temperature)

    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output from the mock LLM.

        Args:
            prompt: The user prompt to send to the LLM.
            schema: JSON schema defining the expected structure.
            system_prompt: Optional system prompt for context.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            Generated structured data conforming to the schema.
        """
        # Check for predefined responses
        for key, response in self.predefined_responses.items():
            if key in prompt and isinstance(response, dict):
                return response

        # Generate a mock JSON response based on the schema
        return self._generate_mock_json(schema, prompt, temperature)

    def _generate_mock_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Generate a mock text response.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            temperature: Temperature setting (0.0 to 1.0).

        Returns:
            A mock response string.
        """
        # Simple mock responses based on prompt content
        if "error" in prompt.lower():
            return "I encountered an error processing that request."

        if "hello" in prompt.lower() or "hi" in prompt.lower():
            return "Hello! I'm a mock AI assistant. How can I help you today?"

        if "help" in prompt.lower():
            return "I'm here to help! As a mock AI assistant, I can pretend to answer questions and generate text."

        if "test" in prompt.lower():
            return "This is a test response from the mock LLM provider. Everything seems to be working properly."

        # Default response with some randomness based on temperature
        responses = [
            "I'm a mock AI assistant. This is a simulated response for testing purposes.",
            "As a mock provider, I generate simple responses without using a real LLM.",
            "This is a placeholder response from the mock provider.",
            "Mock response: This text is generated for testing the LLM integration.",
            "For development purposes only: This response comes from the mock provider."
        ]

        # Use temperature to add randomness
        if temperature > 0.5:
            return random.choice(responses)
        else:
            return responses[0]

    def _generate_mock_json(
        self,
        schema: Dict[str, Any],
        prompt: str,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Generate mock JSON based on a schema.

        Args:
            schema: JSON schema to follow.
            prompt: The prompt that was sent.
            temperature: Temperature setting (0.0 to 1.0).

        Returns:
            A mock JSON object conforming to the schema.
        """
        # Start with an empty result
        result = {}

        # Process the schema to create a valid mock response
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                prop_type = prop_schema.get("type", "string")

                if prop_type == "string":
                    result[prop_name] = f"Mock {prop_name} value"
                elif prop_type == "integer" or prop_type == "number":
                    result[prop_name] = random.randint(1, 100)
                elif prop_type == "boolean":
                    result[prop_name] = random.choice([True, False])
                elif prop_type == "array":
                    items_schema = prop_schema.get("items", {})
                    items_type = items_schema.get("type", "string")

                    if items_type == "string":
                        result[prop_name] = [f"Mock item {i}" for i in range(1, 4)]
                    elif items_type == "integer" or items_type == "number":
                        result[prop_name] = [random.randint(1, 100) for _ in range(3)]
                    elif items_type == "object":
                        result[prop_name] = [
                            self._generate_mock_json(items_schema, prompt, temperature)
                            for _ in range(2)
                        ]
                    else:
                        result[prop_name] = []
                elif prop_type == "object":
                    result[prop_name] = self._generate_mock_json(prop_schema, prompt, temperature)

        return result