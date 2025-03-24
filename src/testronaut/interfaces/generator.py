"""
Test Generator Interface.

This module defines the interface for generating test plans and test cases.
"""
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable

from testronaut.models import CLITool, Command, TestPlan, TestCase


@runtime_checkable
class TestGenerator(Protocol):
    """Protocol defining the interface for test generators."""

    def generate_test_plan(
        self,
        cli_tool: CLITool,
        name: Optional[str] = None,
        description: Optional[str] = None,
        commands: Optional[List[str]] = None,
        complexity: Optional[str] = None
    ) -> TestPlan:
        """
        Generate a test plan for a CLI tool.

        Args:
            cli_tool: The CLI tool to generate a test plan for.
            name: Optional name for the test plan. Default is auto-generated.
            description: Optional description for the test plan.
            commands: Optional list of command names to include in the test plan.
                      If None, all commands will be considered.
            complexity: Optional complexity level for the tests.
                        Can be "simple", "moderate", or "complex".

        Returns:
            A TestPlan object with test cases.

        Raises:
            ValidationError: If the test plan cannot be generated.
        """
        ...

    def generate_test_cases(
        self,
        command: Command,
        count: int = 3,
        complexity: str = "moderate"
    ) -> List[TestCase]:
        """
        Generate test cases for a specific command.

        Args:
            command: The command to generate test cases for.
            count: The number of test cases to generate.
            complexity: The complexity level of the test cases.
                        Can be "simple", "moderate", or "complex".

        Returns:
            A list of TestCase objects.

        Raises:
            ValidationError: If the test cases cannot be generated.
        """
        ...

    def generate_dependency(
        self,
        test_case: TestCase,
        dependency_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a dependency for a test case.

        Args:
            test_case: The test case to generate a dependency for.
            dependency_type: The type of dependency to generate.
                            Can be "file", "env_var", "command", "service", etc.
            **kwargs: Additional keyword arguments specific to the dependency type.

        Returns:
            A dictionary with dependency information.

        Raises:
            ValidationError: If the dependency cannot be generated.
        """
        ...

    def enrich_test_case(self, test_case: TestCase) -> TestCase:
        """
        Enrich a test case with more detailed information.

        Args:
            test_case: The test case to enrich.

        Returns:
            The enriched test case.

        Raises:
            ValidationError: If the test case cannot be enriched.
        """
        ...