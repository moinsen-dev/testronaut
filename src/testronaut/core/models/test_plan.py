"""
Data models for test plans and test cases.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class TestCaseStatus(str, Enum):
    """
    Status of a test case.
    """
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestStepType(str, Enum):
    """
    Type of test step.
    """
    COMMAND = "command"
    ASSERTION = "assertion"
    SETUP = "setup"
    TEARDOWN = "teardown"


class TestStep(BaseModel):
    """
    Represents a step in a test case.
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStep":
        """Create instance from dictionary."""
        return cls(**data)


class TestCase(BaseModel):
    """
    Represents a test case.
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
    status: TestCaseStatus = Field(default=TestCaseStatus.PENDING, description="Test case status")
    result: Optional[str] = Field(default=None, description="Test case result message")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create instance from dictionary."""
        return cls(**data)


class TestPlan(BaseModel):
    """
    Represents a test plan.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the test plan")
    tool_name: str = Field(..., description="Name of the CLI tool being tested")
    description: str = Field(..., description="Test plan description")
    version: Optional[str] = Field(default=None, description="Version of the CLI tool")
    test_cases: List[TestCase] = Field(default_factory=list, description="Test cases in the plan")
    global_setup: Optional[List[TestStep]] = Field(default_factory=list, description="Global setup steps")
    global_teardown: Optional[List[TestStep]] = Field(default_factory=list, description="Global teardown steps")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator of the test plan")
    model_used: Optional[str] = Field(default=None, description="LLM model used to generate the plan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = self.model_dump()
        # Convert nested objects
        data["test_cases"] = [tc.to_dict() for tc in self.test_cases]
        data["global_setup"] = [step.to_dict() for step in self.global_setup]
        data["global_teardown"] = [step.to_dict() for step in self.global_teardown]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestPlan":
        """Create instance from dictionary."""
        # Convert nested lists back to objects
        if "test_cases" in data:
            data["test_cases"] = [TestCase.from_dict(tc) for tc in data["test_cases"]]
        if "global_setup" in data:
            data["global_setup"] = [TestStep.from_dict(step) for step in data["global_setup"]]
        if "global_teardown" in data:
            data["global_teardown"] = [TestStep.from_dict(step) for step in data["global_teardown"]]
        return cls(**data)