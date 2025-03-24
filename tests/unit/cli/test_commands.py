"""
Unit tests for CLI commands.
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

from testronaut.cli.commands import analyze, generate, verify, report
from testronaut.cli.main import app


@pytest.mark.unit
class TestAnalyzeCommand:
    """Unit tests for the analyze command."""

    def test_analyze_command_help(self):
        """Test that analyze command help text is displayed."""
        runner = CliRunner()
        result = runner.invoke(analyze.app, ["--help"])
        assert result.exit_code == 0
        assert "Analyze CLI tool" in result.stdout


@pytest.mark.unit
class TestGenerateCommand:
    """Unit tests for the generate command."""

    def test_generate_command_help(self):
        """Test that generate command help text is displayed."""
        runner = CliRunner()
        result = runner.invoke(generate.app, ["--help"])
        assert result.exit_code == 0
        assert "Generate test plan" in result.stdout


@pytest.mark.unit
class TestVerifyCommand:
    """Unit tests for the verify command."""

    def test_verify_command_help(self):
        """Test that verify command help text is displayed."""
        runner = CliRunner()
        result = runner.invoke(verify.app, ["--help"])
        assert result.exit_code == 0
        assert "Execute tests and verify" in result.stdout


@pytest.mark.unit
class TestReportCommand:
    """Unit tests for the report command."""

    def test_report_command_help(self):
        """Test that report command help text is displayed."""
        runner = CliRunner()
        result = runner.invoke(report.app, ["--help"])
        assert result.exit_code == 0
        assert "Generate test report" in result.stdout

    def test_report_format_help(self):
        """Test that report command format option is displayed."""
        runner = CliRunner()
        result = runner.invoke(report.app, ["--help"])
        assert result.exit_code == 0
        assert "--format" in result.stdout