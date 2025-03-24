"""
Unit tests for CLI command modules.
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from testronaut.cli.commands.analyze import app as analyze_app
from testronaut.cli.commands.generate import app as generate_app
from testronaut.cli.commands.verify import app as verify_app
from testronaut.cli.commands.report import app as report_app


class TestAnalyzeCommand:
    """Tests for the analyze command."""

    def test_analyze_command_help(self, cli_runner):
        """Test the analyze command help."""
        result = cli_runner.invoke(analyze_app, ["--help"])
        assert result.exit_code == 0
        assert "Analyze CLI tool" in result.stdout


class TestGenerateCommand:
    """Tests for the generate command."""

    def test_generate_command_help(self, cli_runner):
        """Test the generate command help."""
        result = cli_runner.invoke(generate_app, ["--help"])
        assert result.exit_code == 0
        assert "Generate test plan" in result.stdout


class TestVerifyCommand:
    """Tests for the verify command."""

    def test_verify_command_help(self, cli_runner):
        """Test the verify command help."""
        result = cli_runner.invoke(verify_app, ["--help"])
        assert result.exit_code == 0
        assert "Execute tests and verify" in result.stdout


class TestReportCommand:
    """Tests for the report command."""

    def test_report_command_help(self, cli_runner):
        """Test the report command help."""
        result = cli_runner.invoke(report_app, ["--help"])
        assert result.exit_code == 0
        assert "Generate test report" in result.stdout

    def test_report_format_help(self, cli_runner):
        """Test that the report command has a format option."""
        result = cli_runner.invoke(report_app, ["--help"])
        assert "format" in result.stdout.lower()
        assert "html" in result.stdout.lower() or "report format" in result.stdout.lower()