"""
Functional tests for the analyze workflow.

These tests verify the end-to-end functionality of analyzing a CLI tool
and generating a test plan.
"""

import os
import json
import pytest
from pathlib import Path


@pytest.mark.functional
class TestAnalyzeWorkflow:
    """Tests for the analyze workflow."""

    def test_analyze_and_generate_workflow(self, test_environment, testronaut_cli):
        """
        Test the complete analyze and generate workflow.

        This test verifies:
        1. Analyzing a CLI tool
        2. Generating a test plan from the analysis
        """
        # Extract environment variables
        tool_path = test_environment["tool_path"]
        output_dir = test_environment["output_dir"]
        tool_name = test_environment["tool_name"]

        # Step 1: Analyze the tool
        analyze_result = testronaut_cli([
            "analyze",
            "--tool", tool_path,
            "--output-dir", output_dir
        ])

        # Verify analyze command succeeded
        assert analyze_result.returncode == 0, f"Analyze command failed: {analyze_result.stderr}"
        assert "Analyzing" in analyze_result.stdout
        assert tool_path in analyze_result.stdout

        # Check that analysis file was created
        analysis_file = Path(output_dir) / f"{tool_name}_analysis.json"
        assert analysis_file.exists(), f"Analysis file not created: {analysis_file}"

        # Step 2: Generate test plan
        generate_result = testronaut_cli([
            "generate",
            "--tool", tool_path,
            "--output-dir", output_dir
        ])

        # Verify generate command succeeded
        assert generate_result.returncode == 0, f"Generate command failed: {generate_result.stderr}"
        assert "Generating" in generate_result.stdout

        # Check that test plan file was created
        test_plan_file = Path(output_dir) / f"{tool_name}_test_plan.json"
        assert test_plan_file.exists(), f"Test plan file not created: {test_plan_file}"

        # Validate the content of the test plan
        try:
            with open(test_plan_file, "r") as f:
                test_plan = json.load(f)

            # Basic structure validation
            assert "tool_name" in test_plan, "Test plan missing tool_name"
            assert "test_cases" in test_plan, "Test plan missing test_cases"
            assert len(test_plan["test_cases"]) > 0, "Test plan has no test cases"

            # Validate test cases for the expected commands
            commands = ["run", "list"]
            for command in commands:
                found = False
                for test_case in test_plan["test_cases"]:
                    if command in test_case["command_line"]:
                        found = True
                        break
                assert found, f"No test case found for command '{command}'"

        except json.JSONDecodeError:
            assert False, f"Test plan file is not valid JSON: {test_plan_file}"

    def test_analyze_invalid_tool(self, test_environment, testronaut_cli):
        """Test analyze with an invalid tool path."""
        output_dir = test_environment["output_dir"]
        invalid_tool = "/path/to/nonexistent/tool"

        # Analyze non-existent tool
        result = testronaut_cli([
            "analyze",
            "--tool", invalid_tool,
            "--output-dir", output_dir
        ])

        # Verify command failed appropriately
        assert result.returncode != 0, "Command should fail with non-existent tool"
        assert "Error" in result.stdout, "Error message not displayed for invalid tool"

    def test_analyze_help(self, testronaut_cli):
        """Test the analyze command help."""
        result = testronaut_cli(["analyze", "--help"])

        # Verify help output
        assert result.returncode == 0
        assert "Analyze CLI tool" in result.stdout
        assert "--tool" in result.stdout