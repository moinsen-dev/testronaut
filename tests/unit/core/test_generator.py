"""
Unit tests for the generator module.
"""

from unittest.mock import MagicMock, patch
import os
import tempfile
import pytest
import json
import shutil
from pathlib import Path

from testronaut.core.models import CliTool, Command, CommandParameter
from testronaut.core.models.test_plan import TPTestPlan, TPTestCase
from testronaut.core.generator.generator import TestPlanGenerator


@pytest.mark.unit
class TestTestPlanGenerator:
    """Tests for the TestPlanGenerator class."""

    @pytest.fixture
    def sample_cli_tool(self):
        """Create a sample CLI tool for testing."""
        command1 = Command(
            name="command1",
            description="First command",
            usage="test command1 [options]",
            parameters=[
                CommandParameter(
                    name="param1",
                    description="First parameter",
                    required=False,
                    long_option="--param1",
                )
            ],
        )
        command2 = Command(
            name="command2",
            description="Second command",
            usage="test command2 [options]",
            parameters=[],
        )
        commands = {"command1": command1, "command2": command2}
        return CliTool(
            name="test",
            description="Test tool",
            version="1.0.0",
            commands=commands,
            help_text="Test help text",
            bin_path="/path/to/test",
        )

    @pytest.fixture
    def test_output_dir(self):
        """Create a temporary directory for test outputs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_generator_initialization(self, test_output_dir):
        """Test that the generator initializes correctly."""
        # Test with default output directory
        generator = TestPlanGenerator()
        assert generator.output_dir.endswith("generated_tests")
        assert generator.llm_manager is None

        # Test with custom output directory
        generator = TestPlanGenerator(output_dir=test_output_dir)
        assert generator.output_dir == test_output_dir

        # Test with LLM manager
        llm_manager = MagicMock()
        generator = TestPlanGenerator(llm_manager=llm_manager, output_dir=test_output_dir)
        assert generator.llm_manager == llm_manager
        assert generator.output_dir == test_output_dir

    def test_generate_test_plan(self, sample_cli_tool):
        """Test generating a test plan from a CLI tool."""
        generator = TestPlanGenerator()
        test_plan = generator.generate_test_plan(sample_cli_tool)

        # Verify test plan properties
        assert isinstance(test_plan, TPTestPlan)
        assert test_plan.tool_name == sample_cli_tool.name
        assert test_plan.version == sample_cli_tool.version
        assert len(test_plan.test_cases) > 0  # Should have test cases

    def test_generate_command_test_cases(self, sample_cli_tool):
        """Test generating test cases for a command."""
        generator = TestPlanGenerator()
        command = sample_cli_tool.commands["command1"]

        test_cases = generator._generate_command_test_cases(sample_cli_tool, command)

        # Verify that we have at least two test cases (help and basic)
        assert len(test_cases) >= 2
        assert all(isinstance(tc, TPTestCase) for tc in test_cases)

        # Check that there's a help test
        help_test = next((tc for tc in test_cases if "help" in tc.name), None)
        assert help_test is not None
        assert "--help" in help_test.command_line

        # Check that there's a basic test
        basic_test = next((tc for tc in test_cases if "basic" in tc.name), None)
        assert basic_test is not None
        assert sample_cli_tool.name in basic_test.command_line

    def test_save_test_plan(self, sample_cli_tool, test_output_dir):
        """Test saving a test plan to disk."""
        generator = TestPlanGenerator(output_dir=test_output_dir)
        test_plan = generator.generate_test_plan(sample_cli_tool)

        # Test saving as JSON
        file_path = generator.save_test_plan(test_plan, output_format="json")
        assert os.path.exists(file_path)
        assert file_path.endswith(".json")

        # Verify the file contains valid JSON
        with open(file_path, "r") as f:
            data = json.load(f)
            assert data["tool_name"] == test_plan.tool_name
            assert data["version"] == test_plan.version
            assert len(data["test_cases"]) == len(test_plan.test_cases)

        # Test with unsupported format
        with pytest.raises(ValueError):
            generator.save_test_plan(test_plan, output_format="invalid")

    def test_load_test_plan(self, sample_cli_tool, test_output_dir):
        """Test loading a test plan from disk."""
        generator = TestPlanGenerator(output_dir=test_output_dir)
        test_plan = generator.generate_test_plan(sample_cli_tool)
        file_path = generator.save_test_plan(test_plan)

        # Load test plan and verify
        loaded_plan = generator.load_test_plan(file_path)
        assert isinstance(loaded_plan, TPTestPlan)
        assert loaded_plan.tool_name == test_plan.tool_name
        assert loaded_plan.version == test_plan.version
        assert len(loaded_plan.test_cases) == len(test_plan.test_cases)

        # Test loading with unsupported format
        with pytest.raises(ValueError):
            generator.load_test_plan("test_plan.unknown")

    def test_generate_pytest_file(self, sample_cli_tool, test_output_dir):
        """Test generating a pytest file from a test plan."""
        generator = TestPlanGenerator(output_dir=test_output_dir)
        test_plan = generator.generate_test_plan(sample_cli_tool)
        pytest_file = generator.generate_pytest_file(test_plan)

        # Verify file exists
        assert os.path.exists(pytest_file)
        assert pytest_file.endswith(".py")

        # Verify file content
        with open(pytest_file, "r") as f:
            content = f.read()
            assert "import pytest" in content
            assert sample_cli_tool.name in content
            for test_case in test_plan.test_cases:
                assert test_case.name.lower() in content

    def test_llm_enhancement(self, sample_cli_tool):
        """Test enhancing test cases with LLM."""
        # Setup mock LLM manager
        llm_manager = MagicMock()
        generator = TestPlanGenerator(llm_manager=llm_manager)
        command = sample_cli_tool.commands["command1"]

        # Create some test cases
        test_cases = generator._generate_command_test_cases(sample_cli_tool, command)
        original_count = len(test_cases)

        # Set up the enhancer to pass through the test cases unchanged
        # In a real implementation this might add more test cases
        test_cases = generator._enhance_test_cases_with_llm(
            sample_cli_tool, command, test_cases
        )

        # Since we're not really enhancing yet, verify we have the same test cases
        assert len(test_cases) == original_count