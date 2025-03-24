"""
Module for generating tests from analyzed CLI tool data.
"""

from typing import Dict, List, Optional, Any
import os
import json
from pathlib import Path

from testronaut.core.models import CliTool, Command
from testronaut.core.models.test_plan import TPTestPlan, TPTestCase


class TestPlanGenerator:
    """
    Generates test plans and test cases based on analyzed CLI tools.
    """

    def __init__(self, llm_manager=None, output_dir: str = None):
        """
        Initialize the TestPlanGenerator.

        Args:
            llm_manager: Optional LLM manager for enhanced test generation
            output_dir: Directory to save generated test files
        """
        self.llm_manager = llm_manager
        self.output_dir = output_dir or os.path.join(os.getcwd(), "generated_tests")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_test_plan(self, cli_tool: CliTool) -> TPTestPlan:
        """
        Generate a test plan for a CLI tool.

        Args:
            cli_tool: The CLI tool to generate tests for

        Returns:
            A TPTestPlan object containing test cases
        """
        test_plan = TPTestPlan(
            tool_name=cli_tool.name,
            description=f"Test plan for {cli_tool.name}",
            version=cli_tool.version,
            test_cases=[]
        )

        # Generate test cases for each command
        for command_name, command in cli_tool.commands.items():
            test_cases = self._generate_command_test_cases(cli_tool, command)
            test_plan.test_cases.extend(test_cases)

        return test_plan

    def _generate_command_test_cases(self, cli_tool: CliTool, command: Command) -> List[TPTestCase]:
        """
        Generate test cases for a specific command.

        Args:
            cli_tool: The CLI tool
            command: The command to generate test cases for

        Returns:
            List of TPTestCase objects
        """
        test_cases = []

        # Basic help command test
        help_test = TPTestCase(
            name=f"{command.name}_help_test",
            description=f"Test help output for {command.name}",
            command_line=f"{cli_tool.name} {command.name} --help",
            expected_exit_code=0,
            expected_output_contains=["help", "usage"],
            expected_error_contains=[],
        )
        test_cases.append(help_test)

        # Basic execution test (if no required parameters)
        if not any(param.required for param in command.parameters):
            basic_test = TPTestCase(
                name=f"{command.name}_basic_test",
                description=f"Basic test for {command.name}",
                command_line=f"{cli_tool.name} {command.name}",
                expected_exit_code=0,
                expected_output_contains=[],
                expected_error_contains=[],
            )
            test_cases.append(basic_test)

        # Test with parameters if the command has any
        if command.parameters:
            # Generate a test with all optional parameters
            optional_params = [param for param in command.parameters if not param.required]
            if optional_params:
                param_str = " ".join(
                    [p.long_option or p.short_option for p in optional_params if p.is_flag]
                )
                param_str += " ".join(
                    [f"{p.long_option or p.short_option} test_value" for p in optional_params if not p.is_flag]
                )

                if param_str:
                    param_test = TPTestCase(
                        name=f"{command.name}_with_params_test",
                        description=f"Test {command.name} with parameters",
                        command_line=f"{cli_tool.name} {command.name} {param_str}",
                        expected_exit_code=0,
                        expected_output_contains=[],
                        expected_error_contains=[],
                    )
                    test_cases.append(param_test)

        # If LLM manager is available, enhance test cases
        if self.llm_manager:
            test_cases = self._enhance_test_cases_with_llm(
                cli_tool, command, test_cases
            )

        return test_cases

    def _enhance_test_cases_with_llm(
        self, cli_tool: CliTool, command: Command, test_cases: List[TPTestCase]
    ) -> List[TPTestCase]:
        """
        Enhance test cases using LLM capabilities.

        Args:
            cli_tool: The CLI tool
            command: The command
            test_cases: Initial test cases

        Returns:
            Enhanced list of test cases
        """
        # This would use the LLM to improve test cases
        # For now, return the original test cases
        return test_cases

    def save_test_plan(self, test_plan: TPTestPlan, output_format: str = "json") -> str:
        """
        Save a test plan to a file.

        Args:
            test_plan: The test plan to save
            output_format: Format to save the test plan in (json, yaml)

        Returns:
            Path to the saved file
        """
        filename = f"{test_plan.tool_name}_test_plan"
        if output_format == "json":
            file_path = os.path.join(self.output_dir, f"{filename}.json")
            with open(file_path, "w") as f:
                json.dump(test_plan.to_dict(), f, indent=2)
            return file_path
        elif output_format == "yaml":
            file_path = os.path.join(self.output_dir, f"{filename}.yaml")
            # Implementation for YAML would go here
            raise NotImplementedError("YAML output is not yet implemented")
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def load_test_plan(self, file_path: str) -> TPTestPlan:
        """
        Load a test plan from a file.

        Args:
            file_path: Path to the test plan file

        Returns:
            The loaded TPTestPlan object
        """
        file_extension = Path(file_path).suffix.lower()

        if file_extension == ".json":
            with open(file_path, "r") as f:
                data = json.load(f)
                return TPTestPlan.from_dict(data)
        elif file_extension in [".yaml", ".yml"]:
            # Implementation for YAML would go here
            raise NotImplementedError("YAML input is not yet implemented")
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

    def generate_pytest_file(self, test_plan: TPTestPlan) -> str:
        """
        Generate a pytest file from a test plan.

        Args:
            test_plan: The test plan

        Returns:
            Path to the generated pytest file
        """
        output_file = os.path.join(self.output_dir, f"test_{test_plan.tool_name}.py")

        with open(output_file, "w") as f:
            f.write(f"""
import pytest
import subprocess
from pathlib import Path

# Generated test file for {test_plan.tool_name} version {test_plan.version}

class Test{test_plan.tool_name.capitalize().replace('-', '_')}:
    \"\"\"Test cases for {test_plan.tool_name}.\"\"\"
""")

            for test_case in test_plan.test_cases:
                # Convert test case to pytest function
                f.write(f"""
    def {test_case.name.lower()}(self):
        \"\"\"{test_case.description}\"\"\"
        result = subprocess.run(
            "{test_case.command_line}",
            shell=True,
            capture_output=True,
            text=True
        )

        # Check exit code
        assert result.returncode == {test_case.expected_exit_code}, f"Expected exit code {test_case.expected_exit_code}, got {{result.returncode}}"

""")
                # Add expected output checks
                if test_case.expected_output_contains:
                    f.write(f"        # Check expected output\n")
                    for expected in test_case.expected_output_contains:
                        f.write(f'        assert "{expected}" in result.stdout.lower(), f"Expected output to contain \\"{expected}\\", but it did not."\n')

                # Add expected error checks
                if test_case.expected_error_contains:
                    f.write(f"        # Check expected errors\n")
                    for expected in test_case.expected_error_contains:
                        f.write(f'        assert "{expected}" in result.stderr.lower(), f"Expected error to contain \\"{expected}\\", but it did not."\n')

                f.write("\n")

        return output_file