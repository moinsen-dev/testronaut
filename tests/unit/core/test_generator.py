"""
Unit tests for the test generator module.
"""

import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open

from testronaut.core.generator.generator import TestGenerator
from testronaut.core.models import CliTool, Command, CommandParameter, TestPlan, TestCase


class TestTestGenerator:
    """Test cases for the TestGenerator class."""

    @pytest.fixture
    def sample_cli_tool(self):
        """Create a sample CLI tool for testing."""
        # Create parameters for a command
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
        command1 = Command(
            name="test-cmd",
            description="A test command",
            usage="tool test-cmd [options]",
            parameters=[param1, param2]
        )

        command2 = Command(
            name="simple-cmd",
            description="A simple command with no required parameters",
            usage="tool simple-cmd",
            parameters=[param1]
        )

        # Create CLI tool
        cli_tool = CliTool(
            name="tool",
            description="A test tool",
            version="1.0.0",
            commands={"test-cmd": command1, "simple-cmd": command2},
            help_text="Help text",
            bin_path="/usr/bin/tool"
        )

        return cli_tool

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_generator_initialization(self):
        """Test that the generator can be initialized properly."""
        generator = TestGenerator()
        assert generator is not None
        assert generator.llm_manager is None
        assert generator.output_dir.endswith("generated_tests")

        # Test with custom output directory
        custom_dir = "/tmp/custom_tests"
        generator = TestGenerator(output_dir=custom_dir)
        assert generator.output_dir == custom_dir

        # Test with LLM manager
        llm_manager = MagicMock()
        generator = TestGenerator(llm_manager=llm_manager)
        assert generator.llm_manager == llm_manager

    def test_generate_test_plan(self, sample_cli_tool):
        """Test generating a test plan from a CLI tool."""
        generator = TestGenerator()
        test_plan = generator.generate_test_plan(sample_cli_tool)

        # Verify the test plan
        assert isinstance(test_plan, TestPlan)
        assert test_plan.tool_name == sample_cli_tool.name
        assert test_plan.version == sample_cli_tool.version
        assert len(test_plan.test_cases) > 0

        # Verify that test cases were generated for each command
        test_case_names = [tc.name for tc in test_plan.test_cases]
        assert any("test-cmd" in name for name in test_case_names)
        assert any("simple-cmd" in name for name in test_case_names)

    def test_generate_command_test_cases(self, sample_cli_tool):
        """Test generating test cases for a command."""
        generator = TestGenerator()
        command = sample_cli_tool.commands["simple-cmd"]

        test_cases = generator._generate_command_test_cases(sample_cli_tool, command)

        # Verify test cases
        assert len(test_cases) >= 2  # Should have help test and basic test at minimum

        # Check for the help test case
        help_tests = [tc for tc in test_cases if "help" in tc.name.lower()]
        assert len(help_tests) == 1
        assert help_tests[0].command_line == f"{sample_cli_tool.name} {command.name} --help"
        assert help_tests[0].expected_exit_code == 0

        # Check for the basic test case (no required parameters)
        basic_tests = [tc for tc in test_cases if "basic" in tc.name.lower()]
        assert len(basic_tests) == 1
        assert basic_tests[0].command_line == f"{sample_cli_tool.name} {command.name}"

        # Now test a command with required parameters (shouldn't have a basic test)
        command_with_req = sample_cli_tool.commands["test-cmd"]
        test_cases = generator._generate_command_test_cases(sample_cli_tool, command_with_req)
        basic_tests = [tc for tc in test_cases if "basic" in tc.name.lower()]
        assert len(basic_tests) == 0

    def test_save_test_plan(self, sample_cli_tool, temp_output_dir):
        """Test saving a test plan to a file."""
        generator = TestGenerator(output_dir=temp_output_dir)
        test_plan = generator.generate_test_plan(sample_cli_tool)

        # Test JSON saving
        file_path = generator.save_test_plan(test_plan, output_format="json")
        assert os.path.exists(file_path)
        assert file_path.endswith(".json")

        # Verify file contents
        with open(file_path, "r") as f:
            data = json.load(f)
            assert data["tool_name"] == test_plan.tool_name
            assert data["version"] == test_plan.version
            assert len(data["test_cases"]) == len(test_plan.test_cases)

        # Test unsupported format
        with pytest.raises(ValueError):
            generator.save_test_plan(test_plan, output_format="unsupported")

        # Test YAML format (not implemented yet)
        with pytest.raises(NotImplementedError):
            generator.save_test_plan(test_plan, output_format="yaml")

    def test_load_test_plan(self, sample_cli_tool, temp_output_dir):
        """Test loading a test plan from a file."""
        generator = TestGenerator(output_dir=temp_output_dir)
        test_plan = generator.generate_test_plan(sample_cli_tool)

        # Save then load the test plan
        file_path = generator.save_test_plan(test_plan)
        loaded_plan = generator.load_test_plan(file_path)

        # Verify loaded plan
        assert isinstance(loaded_plan, TestPlan)
        assert loaded_plan.tool_name == test_plan.tool_name
        assert loaded_plan.version == test_plan.version
        assert len(loaded_plan.test_cases) == len(test_plan.test_cases)

        # Test unsupported format
        with pytest.raises(ValueError):
            generator.load_test_plan("test.unsupported")

        # Test YAML format (not implemented yet)
        with pytest.raises(NotImplementedError):
            generator.load_test_plan("test.yaml")

    def test_generate_pytest_file(self, sample_cli_tool, temp_output_dir):
        """Test generating a pytest file from a test plan."""
        generator = TestGenerator(output_dir=temp_output_dir)
        test_plan = generator.generate_test_plan(sample_cli_tool)

        # Generate pytest file
        file_path = generator.generate_pytest_file(test_plan)
        assert os.path.exists(file_path)
        assert file_path.endswith(".py")

        # Verify file contains expected content
        with open(file_path, "r") as f:
            content = f.read()
            assert "import pytest" in content
            assert "import subprocess" in content
            assert f"Generated test file for {test_plan.tool_name}" in content
            assert f"class Test{test_plan.tool_name.capitalize()}" in content

            # Check that each test case has a method
            for test_case in test_plan.test_cases:
                assert f"def {test_case.name.lower()}(self)" in content
                assert test_case.command_line in content

    @patch.object(TestGenerator, '_enhance_test_cases_with_llm')
    def test_llm_enhancement(self, mock_enhance, sample_cli_tool):
        """Test enhancement of test cases using LLM."""
        # Setup mock
        mock_enhanced_cases = [
            TestCase(
                name="enhanced_test",
                description="Enhanced test case",
                command_line="tool test-cmd --output test.out",
                expected_exit_code=0,
                expected_output_contains=["success"],
                expected_error_contains=[],
            )
        ]
        mock_enhance.return_value = mock_enhanced_cases

        # Create generator with mock LLM manager
        llm_manager = MagicMock()
        generator = TestGenerator(llm_manager=llm_manager)

        # Generate test cases
        command = sample_cli_tool.commands["test-cmd"]
        test_cases = generator._generate_command_test_cases(sample_cli_tool, command)

        # Verify that the enhancement function was called
        mock_enhance.assert_called_once()

        # Verify that the enhanced test cases were returned
        assert test_cases == mock_enhanced_cases