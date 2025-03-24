"""
Testronaut Data Models.

This package contains the SQLModel-based data models used in the Testronaut application.
"""

from testronaut.models.base import BaseModel, Repository, create_db_and_tables, get_session
from testronaut.models.cli_tool import Argument, CLITool, Command, Example, Option
from testronaut.models.test_plan import (
    Dependency,
    TestCase,
    TestPlan,
    TestReport,
    TestResult,
    TestStatus,
)

__all__ = [
    # Base models and DB utilities
    "BaseModel",
    "create_db_and_tables",
    "get_session",
    "Repository",
    # CLI Tool models
    "CLITool",
    "Command",
    "Option",
    "Argument",
    "Example",
    # Test Plan models
    "TestStatus",
    "TestPlan",
    "TestCase",
    "Dependency",
    "TestResult",
    "TestReport",
]
