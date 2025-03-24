"""
Models related to test plans and test cases.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class TestCaseStatus(str, Enum):
    """
    Status of a test case execution.
    """
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestStepType(str, Enum):
    """
    Type of test step.
    """
    COMMAND = "command"  # Execute a CLI command
    ASSERTION = "assertion"  # Assert something about the state
    SETUP = "setup"  # Setup step
    TEARDOWN = "teardown"  # Teardown step
    VERIFICATION = "verification"  # AI verification step


class TestStep(BaseModel):
    """
    Model representing a step in a test case.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the step")
    type: TestStepType = Field(..., description="Type of step")
    description: str = Field(..., description="Description of the step")
    command: Optional[str] = Field(None, description="Command to execute")
    expected_exit_code: Optional[int] = Field(None, description="Expected exit code from command")
    expected_output: Optional[str] = Field(None, description="Expected output pattern or content")
    timeout: Optional[int] = Field(None, description="Timeout in seconds for the command")
    depends_on: Optional[List[str]] = Field(default_factory=list, description="IDs of steps this step depends on")
    environment: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")
    status: TestCaseStatus = Field(default=TestCaseStatus.NOT_RUN, description="Test case status")
    actual_result: Optional[str] = Field(default=None, description="Actual result message")
    actual_exit_code: Optional[int] = Field(default=None, description="Actual exit code from command")
    actual_output: Optional[str] = Field(default=None, description="Actual output from command")
    actual_error: Optional[str] = Field(default=None, description="Actual error from command")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStep":
        """Create instance from dictionary."""
        return cls(**data)


class TPTestCase(BaseModel):
    """
    Model representing a test case.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the test case")
    name: str = Field(..., description="Test case name")
    description: str = Field(..., description="Test case description")
    command_line: str = Field(..., description="Command line to execute")
    expected_exit_code: int = Field(default=0, description="Expected exit code")
    expected_output_contains: List[str] = Field(default_factory=list, description="Expected output contains")
    expected_error_contains: List[str] = Field(default_factory=list, description="Expected error contains")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the test case")
    steps: List[TestStep] = Field(default_factory=list, description="Steps in the test case")
    status: TestCaseStatus = Field(default=TestCaseStatus.NOT_RUN, description="Test case status")
    result: Optional[str] = Field(default=None, description="Test case result message")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TPTestCase":
        """Create instance from dictionary."""
        # Convert steps to TestStep objects if they exist
        if "steps" in data:
            data["steps"] = [TestStep.from_dict(step) for step in data["steps"]]
        return cls(**data)


class TPTestPlan(BaseModel):
    """
    Model representing a test plan.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the test plan")
    tool_name: str = Field(..., description="Name of the CLI tool being tested")
    description: str = Field(..., description="Test plan description")
    version: Optional[str] = Field(default=None, description="Version of the CLI tool")
    test_cases: List[TPTestCase] = Field(default_factory=list, description="Test cases in the plan")
    global_setup: Optional[List[TestStep]] = Field(default_factory=list, description="Global setup steps")
    global_teardown: Optional[List[TestStep]] = Field(default_factory=list, description="Global teardown steps")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator of the test plan")
    model_used: Optional[str] = Field(default=None, description="LLM model used to generate the plan")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the test plan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = self.model_dump()
        # Convert nested objects
        data["test_cases"] = [tc.to_dict() for tc in self.test_cases]
        data["global_setup"] = [step.to_dict() for step in self.global_setup]
        data["global_teardown"] = [step.to_dict() for step in self.global_teardown]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TPTestPlan":
        """Create instance from dictionary."""
        # Convert nested lists back to objects
        if "test_cases" in data:
            data["test_cases"] = [TPTestCase.from_dict(tc) for tc in data["test_cases"]]
        if "global_setup" in data:
            data["global_setup"] = [TestStep.from_dict(step) for step in data["global_setup"]]
        if "global_teardown" in data:
            data["global_teardown"] = [TestStep.from_dict(step) for step in data["global_teardown"]]
        return cls(**data)

    def add_test_case(self, test_case: TPTestCase) -> None:
        """Add a test case to the test plan."""
        self.test_cases.append(test_case)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the test plan."""
        self.metadata[key] = value