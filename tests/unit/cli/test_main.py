"""
Unit tests for the CLI main module.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from testronaut.cli.main import app, print_banner


@pytest.mark.unit
def test_app_creation():
    """Test that the Typer app is created with the correct name."""
    assert app.info.name == "testronaut"
    assert "AI-assisted" in app.info.help


@pytest.mark.unit
def test_cli_help():
    """Test that the CLI help text is displayed correctly."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "testronaut" in result.stdout
    assert "Commands" in result.stdout
    assert "analyze" in result.stdout
    assert "generate" in result.stdout
    assert "verify" in result.stdout
    assert "report" in result.stdout


@pytest.mark.unit
def test_print_banner():
    """Test that the banner is printed correctly."""
    with patch("testronaut.cli.main.rprint") as mock_print:
        print_banner()
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "Testronaut" in args
        assert "AI-assisted" in args