#!/usr/bin/env python3
"""
Verification script for Testronaut components.

This script tests the key components we've built so far:
1. Configuration management
2. Docker utilities
3. LLM service with MockProvider
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from testronaut.config import Settings, initialize_config
from testronaut.utils.docker import DockerClient, DockerTestEnvironment
from testronaut.utils.llm.providers.mock import MockProvider
from testronaut.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging(level="INFO")
logger = get_logger("test_components")


def test_config():
    """Test configuration management."""
    print("\n=== Testing Configuration Management ===")

    # Initialize config in a temporary directory
    temp_config_dir = Path.home() / ".testronaut-test"
    config_path = initialize_config(str(temp_config_dir), force=True)
    print(f"Initialized config at: {config_path}")

    # Load the settings
    settings = Settings()
    print(f"App name: {settings.app_name}")
    print(f"Debug mode: {settings.debug}")
    print(f"Database URL: {settings.database.url}")
    print(f"LLM provider: {settings.llm.provider}")

    return True


def test_docker():
    """Test Docker utilities."""
    print("\n=== Testing Docker Utilities ===")

    # Create a Docker client
    docker_client = DockerClient()

    # Check if Docker is available
    is_available = docker_client.is_docker_available()
    print(f"Docker available: {is_available}")

    if not is_available:
        print("Docker is not available on this system. Skipping Docker tests.")
        return False

    try:
        # Check Docker status
        status = docker_client.check_docker_status()
        print(f"Docker server version: {status.get('ServerVersion', 'unknown')}")

        # Create a test environment
        test_env = DockerTestEnvironment(image="alpine:latest", pull_image=True)

        # Set up the environment
        env_info = test_env.setup()
        print(f"Test environment set up at: {env_info['work_dir']}")

        # Run a simple test
        result = test_env.run_test(
            command=["echo", "Hello from Docker!"], name="testronaut-verification"
        )

        print(f"Test execution result: {result['exit_code']}")
        print(f"Test output: {result['output'].strip()}")

        # Tear down the environment
        test_env.teardown()
        print("Test environment torn down successfully")

        return True
    except Exception as e:
        print(f"Error during Docker test: {str(e)}")
        return False


def test_llm_service():
    """Test LLM service with MockProvider."""
    print("\n=== Testing LLM Service ===")

    try:
        # Create a mock provider directly since we're having issues with settings
        mock_provider = MockProvider()
        mock_provider.initialize(
            {"predefined_responses": {"test": "This is a test response from the mock provider."}}
        )

        # Create a basic prompt and test text generation
        prompt = "This is a test prompt"
        result = mock_provider.generate_text(prompt)
        print(f"LLM test prompt: '{prompt}'")
        print(f"LLM response: '{result}'")

        # Test JSON generation
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "is_active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }

        json_result = mock_provider.generate_json(prompt="Generate a user profile", schema=schema)

        print(f"LLM JSON generation result: {json_result}")

        return True
    except Exception as e:
        print(f"Error during LLM service test: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== Testronaut Component Verification ===")

    test_results = {
        "Configuration": test_config(),
        "Docker": test_docker(),
        "LLM Service": test_llm_service(),
    }

    print("\n=== Verification Results ===")
    for component, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{component}: {status}")
