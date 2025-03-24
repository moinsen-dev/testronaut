"""
Integration tests for the analyzer and generator modules.
"""

import os
import pytest
import tempfile
import shutil
import json
from unittest.mock import patch, MagicMock

from testronaut.core.analyzer import CliAnalyzer
from testronaut.core.generator.generator import TestGenerator
from testronaut.core.models import CliTool, TestPlan, TestCase


class TestAnalyzerGeneratorIntegration:
    """Test cases for the integration between analyzer and generator."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @patch('subprocess.run')
    def test_analyze_and_generate(self, mock_run, temp_output_dir):
        """Test that analyzer output can be used by generator to create test plans."""
        # Setup mock responses for subprocess calls (simulating CLI tool help output)
        process_mock = MagicMock()
        process_mock.stdout = """
        mytool - A tool for CLI testing
        Version 1.2.3

        Usage: mytool [options] <command>

        Commands:
          run      Run a specific task
          list     List available tasks
          help     Show this help message

        Options:
          -v, --verbose  Enable verbose output
          -h, --help     Show this help
        """
        process_mock.stderr = ""
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Create analyzer and analyze "mytool"
        analyzer = CliAnalyzer()
        cli_tool = analyzer.analyze_tool("mytool")

        # Verify the analysis results
        assert isinstance(cli_tool, CliTool)
        assert cli_tool.name == "mytool"
        assert cli_tool.version == "1.2.3"
        assert len(cli_tool.commands) > 0

        # Create generator and generate test plan
        generator = TestGenerator(output_dir=temp_output_dir)
        test_plan = generator.generate_test_plan(cli_tool)

        # Verify the generated test plan
        assert isinstance(test_plan, TestPlan)
        assert test_plan.tool_name == "mytool"
        assert test_plan.version == "1.2.3"
        assert len(test_plan.test_cases) > 0

        # Verify that test cases were generated for the commands in cli_tool
        command_names = set(cli_tool.commands.keys())
        test_case_commands = set()
        for test_case in test_plan.test_cases:
            cmd_parts = test_case.command_line.split()
            if len(cmd_parts) > 1:
                test_case_commands.add(cmd_parts[1])  # The command name is typically the second part

        # Check that all commands have at least one test
        assert command_names.issubset(test_case_commands)

        # Test saving and loading the test plan
        file_path = generator.save_test_plan(test_plan)
        assert os.path.exists(file_path)

        # Reload the test plan and verify it's the same
        loaded_plan = generator.load_test_plan(file_path)
        assert loaded_plan.tool_name == test_plan.tool_name
        assert loaded_plan.version == test_plan.version
        assert len(loaded_plan.test_cases) == len(test_plan.test_cases)

        # Test generating pytest file
        pytest_file = generator.generate_pytest_file(test_plan)
        assert os.path.exists(pytest_file)

        # Verify pytest file content
        with open(pytest_file, "r") as f:
            content = f.read()
            assert "import pytest" in content
            assert "import subprocess" in content
            assert "class TestMytool" in content
            for test_case in test_plan.test_cases:
                assert test_case.name.lower() in content

    @patch('subprocess.run')
    def test_complex_command_analysis_and_generation(self, mock_run, temp_output_dir):
        """Test analyzing and generating tests for a complex command with arguments."""
        # Setup mock response with a command that has various parameter types
        process_mock = MagicMock()
        process_mock.stdout = """
        complex-tool - A tool with complex commands
        Version 2.0.0

        Usage: complex-tool [options] <command>

        Commands:
          process     Process files with various options
          configure   Configure the tool settings

        Options:
          --help      Show this help message
          --version   Show version information

        Command 'process' options:
          -i, --input FILE       Input file (required)
          -o, --output FILE      Output file
          -f, --format FORMAT    Output format (json, xml, yaml)
          -v, --verbose          Enable verbose output
          --no-backup            Disable automatic backups
        """
        process_mock.stderr = ""
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Create analyzer and analyze the complex tool
        analyzer = CliAnalyzer()
        cli_tool = analyzer.analyze_tool("complex-tool")

        # Verify complex tool analysis
        assert isinstance(cli_tool, CliTool)
        assert cli_tool.name == "complex-tool"
        assert cli_tool.version == "2.0.0"
        assert "process" in cli_tool.commands
        assert "configure" in cli_tool.commands

        # Create generator and generate test plan
        generator = TestGenerator(output_dir=temp_output_dir)
        test_plan = generator.generate_test_plan(cli_tool)

        # Verify test plan for complex tool
        assert isinstance(test_plan, TestPlan)
        assert test_plan.tool_name == "complex-tool"
        assert test_plan.version == "2.0.0"

        # Verify test cases were generated for complex commands
        assert len(test_plan.test_cases) > 0

        # Generate and check pytest file
        pytest_file = generator.generate_pytest_file(test_plan)
        assert os.path.exists(pytest_file)

        # Verify pytest file content for complex tests
        with open(pytest_file, "r") as f:
            content = f.read()
            assert "class TestComplex_tool" in content