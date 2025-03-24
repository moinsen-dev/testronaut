"""
Test plan and test execution models.

This module defines the data models for test plans, test cases, dependencies,
test results, and test reports.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, ForwardRef, List, Optional

from sqlmodel import JSON, Column, Field, Relationship

from testronaut.models.base import BaseModel

# Forward references for type hints
TestCaseRef = ForwardRef("TestCase")
DependencyRef = ForwardRef("Dependency")
TestResultRef = ForwardRef("TestResult")


class TestStatus(str, Enum):
    """Enum representing the status of a test case or test plan."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestPlan(BaseModel, table=True):
    """Model representing a test plan for a CLI tool."""

    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    cli_tool_id: str = Field(foreign_key="clitool.id", index=True)
    status: TestStatus = Field(default=TestStatus.PENDING)
    meta_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    test_cases: List[TestCaseRef] = Relationship(
        back_populates="test_plan", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class TestCase(BaseModel, table=True):
    """Model representing a test case within a test plan."""

    test_plan_id: str = Field(foreign_key="testplan.id", index=True)
    name: str
    description: Optional[str] = Field(default=None)
    command_id: Optional[str] = Field(default=None, foreign_key="command.id")
    command_line: str
    expected_output: Optional[str] = Field(default=None)
    expected_return_code: int = Field(default=0)
    timeout_seconds: int = Field(default=60)
    status: TestStatus = Field(default=TestStatus.PENDING)
    meta_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    test_plan: TestPlan = Relationship(back_populates="test_cases")
    dependencies: List[DependencyRef] = Relationship(
        back_populates="test_case", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    results: List[TestResultRef] = Relationship(
        back_populates="test_case", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Dependency(BaseModel, table=True):
    """Model representing a dependency for a test case."""

    test_case_id: str = Field(foreign_key="testcase.id", index=True)
    dependency_type: str  # e.g., "file", "env_var", "command", "service"
    name: str
    description: Optional[str] = Field(default=None)
    value: Optional[str] = Field(default=None)
    is_satisfied: bool = Field(default=False)

    # Relationships
    test_case: TestCase = Relationship(back_populates="dependencies")


class TestResult(BaseModel, table=True):
    """Model representing the result of a test case execution."""

    test_case_id: str = Field(foreign_key="testcase.id", index=True)
    execution_time: datetime = Field(default_factory=datetime.now)
    duration_ms: int = Field(default=0)
    return_code: int
    status: TestStatus
    output: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    environment: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Relationships
    test_case: TestCase = Relationship(back_populates="results")


class TestReport(BaseModel, table=True):
    """Model representing a test report for a test plan."""

    test_plan_id: str = Field(foreign_key="testplan.id", index=True)
    execution_time: datetime = Field(default_factory=datetime.now)
    duration_ms: int = Field(default=0)
    total_tests: int = Field(default=0)
    passed_tests: int = Field(default=0)
    failed_tests: int = Field(default=0)
    error_tests: int = Field(default=0)
    skipped_tests: int = Field(default=0)
    summary: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))


# Resolve forward references
TestPlan.update_forward_refs()
TestCase.update_forward_refs()
Dependency.update_forward_refs()
TestResult.update_forward_refs()
