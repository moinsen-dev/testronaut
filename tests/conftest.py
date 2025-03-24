"""
Pytest configuration file for the Testronaut project.
Contains fixtures and configuration for tests.
"""
import os
import sys
import pytest
from pathlib import Path

# Add src directory to path so we can import testronaut package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def cli_runner():
    """
    Fixture for testing CLI commands.
    Returns a runner function for invoking CLI commands.
    """
    from typer.testing import CliRunner
    runner = CliRunner()
    return runner


@pytest.fixture
def sample_cli_tool():
    """
    Fixture that provides a path to a sample CLI tool for testing.
    """
    return "testronaut"  # This will be the name of our own CLI tool for initial testing