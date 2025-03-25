"""
Result Verifier Interface.

This module defines the interface for verifying test results against expected outputs.
"""
from typing import Any, Dict, Protocol, runtime_checkable

from testronaut.models import TestCase, TestResult


@runtime_checkable
class ResultVerifier(Protocol):
    """Protocol defining the interface for result verifiers."""

    def verify_result(
        self,
        test_case: TestCase,
        test_result: TestResult
    ) -> bool:
        """
        Verify a test result against the expected output.

        Args:
            test_case: The test case containing the expected output.
            test_result: The test result containing the actual output.

        Returns:
            True if the result matches the expected output, False otherwise.

        Raises:
            VerificationError: If the verification process fails.
        """
        ...

    def compare_exact(
        self,
        expected: str,
        actual: str,
        ignore_whitespace: bool = True,
        ignore_case: bool = False
    ) -> bool:
        """
        Compare two strings for exact match.

        Args:
            expected: The expected string.
            actual: The actual string.
            ignore_whitespace: Whether to ignore whitespace differences.
            ignore_case: Whether to ignore case differences.

        Returns:
            True if the strings match, False otherwise.
        """
        ...

    def compare_contains(
        self,
        expected: str,
        actual: str,
        ignore_case: bool = False
    ) -> bool:
        """
        Check if the actual string contains the expected string.

        Args:
            expected: The expected substring.
            actual: The actual string.
            ignore_case: Whether to ignore case differences.

        Returns:
            True if the actual string contains the expected string, False otherwise.
        """
        ...

    def compare_semantic(
        self,
        expected: str,
        actual: str,
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Compare two strings semantically using NLP techniques.

        Args:
            expected: The expected string.
            actual: The actual string.
            threshold: The similarity threshold for a match.

        Returns:
            A dictionary with similarity score and match status.

        Raises:
            SemanticComparisonError: If the semantic comparison fails.
        """
        ...

    def verify_return_code(
        self,
        expected: int,
        actual: int
    ) -> bool:
        """
        Verify that the return code matches the expected value.

        Args:
            expected: The expected return code.
            actual: The actual return code.

        Returns:
            True if the return codes match, False otherwise.
        """
        ...

    def verify_json_output(
        self,
        expected: str,
        actual: str,
        strict: bool = False
    ) -> Dict[str, Any]:
        """
        Verify JSON output against expected structure.

        Args:
            expected: The expected JSON string or schema.
            actual: The actual JSON string.
            strict: Whether to require exact structure match.

        Returns:
            A dictionary with match status and differences.

        Raises:
            VerificationError: If the JSON parsing fails.
        """
        ...