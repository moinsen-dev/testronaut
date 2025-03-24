"""
Unit tests for the CLI main module.
"""

import pytest
from typer.testing import CliRunner

from testronaut.cli.main import app, print_banner


def test_app_creation():
    """Test that the Typer app was created correctly."""
    assert app.info.name == "testronaut"
    assert "AI-assisted end-to-end CLI testing tool" in app.info.help


def test_cli_help(cli_runner):
    """Test that the CLI help command works."""
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "testronaut" in result.stdout
    assert "analyze" in result.stdout
    assert "generate" in result.stdout
    assert "verify" in result.stdout
    assert "report" in result.stdout


def test_print_banner():
    """Test that the banner printing function works."""
    # This is a simple test that just ensures no exceptions
    print_banner()  # Should not raise an exception