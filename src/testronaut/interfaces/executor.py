"""
Test Executor Interface.

This module defines the interface for executing test cases and test plans.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from testronaut.models import Dependency, TestCase, TestPlan, TestResult


@runtime_checkable
class TestExecutor(Protocol):
    """Protocol defining the interface for test executors."""

    def execute_test_plan(
        self,
        test_plan: TestPlan,
        environment: Optional[Dict[str, Any]] = None,
        work_dir: Optional[Path] = None
    ) -> TestPlan:
        """
        Execute all test cases in a test plan.

        Args:
            test_plan: The test plan to execute.
            environment: Optional environment variables for the test execution.
            work_dir: Optional working directory for the test execution.

        Returns:
            The test plan with updated test case statuses and results.

        Raises:
            ExecutionError: If the test plan execution fails.
        """
        ...

    def execute_test_case(
        self,
        test_case: TestCase,
        environment: Optional[Dict[str, Any]] = None,
        work_dir: Optional[Path] = None
    ) -> TestResult:
        """
        Execute a single test case.

        Args:
            test_case: The test case to execute.
            environment: Optional environment variables for the test execution.
            work_dir: Optional working directory for the test execution.

        Returns:
            The result of the test case execution.

        Raises:
            ExecutionError: If the test case execution fails.
        """
        ...

    def prepare_dependencies(
        self,
        dependencies: List[Dependency],
        work_dir: Path
    ) -> List[Dependency]:
        """
        Prepare dependencies for a test case.

        Args:
            dependencies: The list of dependencies to prepare.
            work_dir: The working directory for the test execution.

        Returns:
            The list of dependencies with updated satisfaction status.

        Raises:
            ExecutionError: If the dependencies cannot be prepared.
        """
        ...

    def cleanup_dependencies(
        self,
        dependencies: List[Dependency],
        work_dir: Path
    ) -> None:
        """
        Clean up dependencies after a test case execution.

        Args:
            dependencies: The list of dependencies to clean up.
            work_dir: The working directory for the test execution.

        Raises:
            ExecutionError: If the dependencies cannot be cleaned up.
        """
        ...

    def execute_in_container(
        self,
        test_case: TestCase,
        image: str,
        environment: Optional[Dict[str, Any]] = None,
        work_dir: Optional[Path] = None
    ) -> TestResult:
        """
        Execute a test case in a Docker container.

        Args:
            test_case: The test case to execute.
            image: The Docker image to use.
            environment: Optional environment variables for the test execution.
            work_dir: Optional working directory for the test execution.

        Returns:
            The result of the test case execution.

        Raises:
            DockerError: If the Docker container execution fails.
            ExecutionError: If the test case execution fails.
        """
        ...