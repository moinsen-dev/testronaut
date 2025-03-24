"""
Unit tests for the analyzer module.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
import subprocess
from pathlib import Path

from testronaut.core.analyzer import CliAnalyzer
from testronaut.core.models import CliTool, Command, CommandParameter


@pytest.mark.unit
class TestCliAnalyzer:
    """Test cases for the CliAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test that the analyzer can be initialized."""
        analyzer = CliAnalyzer()
        assert analyzer is not None
        assert analyzer.llm_manager is None

        # Test with LLM manager
        llm_manager = MagicMock()
        analyzer = CliAnalyzer(llm_manager=llm_manager)
        assert analyzer.llm_manager == llm_manager

    @patch('subprocess.run')
    def test_extract_help_text(self, mock_run):
        """Test the help text extraction method."""
        # Setup mock
        process_mock = MagicMock()
        process_mock.stdout = "Test help output"
        process_mock.stderr = ""
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Create analyzer and extract help
        analyzer = CliAnalyzer()
        help_text = analyzer._extract_help_text("test-tool")

        # Verify
        assert help_text == "Test help output"
        mock_run.assert_called_once_with(
            "test-tool --help",
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @patch('subprocess.run')
    def test_extract_help_text_fallback(self, mock_run):
        """Test the help text extraction method with fallback to -h."""
        # Setup mocks for first call (--help fails)
        fail_process = MagicMock()
        fail_process.stdout = ""
        fail_process.stderr = ""
        fail_process.returncode = 1

        # Setup mocks for second call (-h succeeds)
        success_process = MagicMock()
        success_process.stdout = "Test help output from -h"
        success_process.stderr = ""
        success_process.returncode = 0

        # Configure mock to return different values on successive calls
        mock_run.side_effect = [fail_process, success_process]

        # Create analyzer and extract help
        analyzer = CliAnalyzer()
        help_text = analyzer._extract_help_text("test-tool")

        # Verify
        assert help_text == "Test help output from -h"
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            "test-tool --help",
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        mock_run.assert_any_call(
            "test-tool -h",
            shell=True,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @patch.object(CliAnalyzer, '_extract_help_text')
    @patch.object(CliAnalyzer, '_analyze_help_text')
    def test_analyze_tool(self, mock_analyze, mock_extract):
        """Test the analyze_tool method."""
        # Setup mocks
        mock_extract.return_value = "Mock help text"
        mock_analyze.return_value = {
            "description": "A test tool",
            "version": "1.0.0",
            "commands": [
                {
                    "name": "test-cmd",
                    "description": "A test command",
                    "usage": "test-tool test-cmd",
                    "options": [
                        {
                            "name": "verbose",
                            "description": "Enable verbose output",
                            "required": False,
                            "is_flag": True,
                            "short_option": "-v",
                            "long_option": "--verbose",
                        }
                    ],
                }
            ],
        }

        # Create analyzer and analyze tool
        analyzer = CliAnalyzer()
        result = analyzer.analyze_tool("test-tool")

        # Verify
        assert isinstance(result, CliTool)
        assert result.name == "test-tool"
        assert result.description == "A test tool"
        assert result.version == "1.0.0"
        assert "test-cmd" in result.commands
        assert result.commands["test-cmd"].name == "test-cmd"
        assert result.commands["test-cmd"].description == "A test command"
        assert len(result.commands["test-cmd"].parameters) == 1
        assert result.commands["test-cmd"].parameters[0].name == "verbose"
        assert result.commands["test-cmd"].parameters[0].is_flag == True

    @patch('subprocess.run')
    def test_install_tool_success(self, mock_run):
        """Test successful tool installation."""
        # Setup mock
        process_mock = MagicMock()
        process_mock.stdout = "Installation successful"
        process_mock.stderr = ""
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Create analyzer and install tool
        analyzer = CliAnalyzer()
        result = analyzer._install_tool("pip install test-tool")

        # Verify
        assert result is None  # Method doesn't return anything on success
        mock_run.assert_called_once_with(
            "pip install test-tool",
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @patch('subprocess.run')
    def test_install_tool_failure(self, mock_run):
        """Test tool installation failure."""
        # Setup mock to raise CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd="pip install test-tool",
            output="",
            stderr="Installation failed"
        )

        # Create analyzer
        analyzer = CliAnalyzer()

        # Verify exception is raised
        with pytest.raises(RuntimeError) as excinfo:
            analyzer._install_tool("pip install test-tool")

        assert "Failed to install tool" in str(excinfo.value)

    @patch('subprocess.run')
    def test_extract_help_text_stderr_fallback(self, mock_run):
        """Test fallback to stderr when stdout is empty."""
        # Setup mock where stdout is empty but stderr has content
        process_mock = MagicMock()
        process_mock.stdout = ""
        process_mock.stderr = "Help output from stderr"
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Create analyzer and extract help
        analyzer = CliAnalyzer()
        help_text = analyzer._extract_help_text("test-tool")

        # Verify
        assert help_text == "Help output from stderr"

    def test_analyze_help_text(self):
        """Test the help text analysis method."""
        analyzer = CliAnalyzer()

        # Test with a simple help text
        help_text = """
        mytool - A tool for testing
        Version 2.1.0

        Usage: mytool [options] <command>

        Commands:
          run      Run a task
          list     List available tasks
          help     Show help

        Options:
          -v, --verbose  Enable verbose output
          -h, --help     Show this help
        """

        result = analyzer._analyze_help_text("mytool", help_text)

        # Verify basic extraction
        assert result["description"] == "mytool - A tool for testing"
        assert result["version"] == "2.1.0"
        assert len(result["commands"]) >= 1

        # Check that at least one command was found
        command_names = [cmd["name"] for cmd in result["commands"]]
        assert any(name in command_names for name in ["run", "list", "help", "mytool"])

    def test_cli_tool_model_creation(self):
        """Test creating a CliTool model with commands."""
        # Create command parameters
        param1 = CommandParameter(
            name="verbose",
            description="Enable verbose output",
            is_flag=True,
            short_option="-v",
            long_option="--verbose"
        )

        param2 = CommandParameter(
            name="output",
            description="Output file",
            required=True,
            type="string",
            short_option="-o",
            long_option="--output"
        )

        # Create command
        command = Command(
            name="test-cmd",
            description="A test command",
            usage="tool test-cmd [options]",
            parameters=[param1, param2]
        )

        # Create CLI tool
        cli_tool = CliTool(
            name="tool",
            description="A test tool",
            version="1.0.0",
            commands={"test-cmd": command},
            help_text="Help text",
            bin_path="/usr/bin/tool"
        )

        # Verify model creation
        assert cli_tool.name == "tool"
        assert cli_tool.description == "A test tool"
        assert cli_tool.version == "1.0.0"
        assert "test-cmd" in cli_tool.commands
        assert cli_tool.commands["test-cmd"].name == "test-cmd"
        assert len(cli_tool.commands["test-cmd"].parameters) == 2
        assert cli_tool.commands["test-cmd"].parameters[0].name == "verbose"
        assert cli_tool.commands["test-cmd"].parameters[1].name == "output"