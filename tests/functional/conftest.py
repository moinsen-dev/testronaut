"""
Pytest configuration for functional tests.

This module contains fixtures and configurations specifically for functional tests,
which test end-to-end workflows of the Testronaut application.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import pytest
import sys
import json

# Import our mock CLI implementation
from tests.functional.mock_cli import (
    analyze_command,
    generate_command,
    verify_command,
    report_command
)


@pytest.fixture
def functional_test_dir():
    """
    Create a temporary directory for functional test outputs.

    This fixture creates a clean temporary directory for tests to use,
    which is cleaned up automatically after the test completes.
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        yield temp_dir
    finally:
        # Clean up the directory after the test is complete
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_cli_tool_path(functional_test_dir):
    """
    Create a sample CLI tool script for testing.

    This generates a simple CLI tool script with a defined command structure
    that can be analyzed by Testronaut.

    Returns:
        str: Path to the generated CLI tool script
    """
    # Create a subdirectory for the tool
    tool_dir = Path(functional_test_dir) / "tool"
    tool_dir.mkdir(exist_ok=True)

    # Create a simple CLI tool script
    tool_path = tool_dir / "sample_tool.py"
    with open(tool_path, "w") as f:
        f.write('''#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description="Sample CLI tool for testing")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # 'run' command
    run_parser = subparsers.add_parser("run", help="Run a job")
    run_parser.add_argument("--input", "-i", help="Input file")
    run_parser.add_argument("--output", "-o", help="Output file")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # 'list' command
    list_parser = subparsers.add_parser("list", help="List available jobs")
    list_parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")

    args = parser.parse_args()

    if args.command == "run":
        print(f"Running job with input={args.input}, output={args.output}")
    elif args.command == "list":
        print("Available jobs: job1, job2, job3")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
''')

    # Make the script executable
    os.chmod(tool_path, 0o755)

    return str(tool_path)


@pytest.fixture
def testronaut_cli():
    """
    Fixture for invoking the Testronaut CLI in functional tests.

    This returns a function that can be used to run Testronaut commands
    and returns the result of the command.

    Returns:
        callable: Function to run Testronaut commands
    """

    def _run_testronaut(args):
        """
        Run a Testronaut command with the given arguments.

        Args:
            args (list): Command line arguments for Testronaut

        Returns:
            subprocess.CompletedProcess: Result of the command execution
        """
        # Parse the command and arguments
        if not args:
            return subprocess.CompletedProcess(
                args=["mock_cli"],
                returncode=1,
                stdout="Please specify a command",
                stderr=""
            )

        command = args[0]
        command_args = args[1:]

        # Convert list arguments to an argparse.Namespace
        namespace = type('Args', (), {})()

        # Set default values
        namespace.tool = None
        namespace.output_dir = "./testronaut-output"
        namespace.format = "html"  # Only for report command

        # Parse command-specific arguments
        i = 0
        while i < len(command_args):
            arg = command_args[i]
            if arg in ["--tool", "-t"] and i + 1 < len(command_args):
                namespace.tool = command_args[i + 1]
                i += 2
            elif arg in ["--output-dir", "-o"] and i + 1 < len(command_args):
                namespace.output_dir = command_args[i + 1]
                i += 2
            elif arg in ["--format"] and i + 1 < len(command_args):
                namespace.format = command_args[i + 1]
                i += 2
            elif arg in ["--help", "-h"]:
                # Simulate help output
                return subprocess.CompletedProcess(
                    args=["mock_cli", command, "--help"],
                    returncode=0,
                    stdout=f"Analyze CLI tool\n  --tool      Tool to analyze\n  --output-dir Output directory",
                    stderr=""
                )
            else:
                i += 1

        # Capture stdout to return it
        import io
        import contextlib
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                if command == "analyze":
                    returncode = analyze_command(namespace)
                elif command == "generate":
                    returncode = generate_command(namespace)
                elif command == "verify":
                    returncode = verify_command(namespace)
                elif command == "report":
                    returncode = report_command(namespace)
                else:
                    returncode = 1
                    print(f"Unknown command: {command}")
            except Exception as e:
                returncode = 1
                print(f"Error: {str(e)}", file=stderr)

        return subprocess.CompletedProcess(
            args=["mock_cli"] + args,
            returncode=returncode,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue()
        )

    return _run_testronaut


@pytest.fixture
def test_environment(functional_test_dir, sample_cli_tool_path):
    """
    Set up a complete test environment.

    This fixture sets up a test environment with:
    - A temporary directory for outputs
    - A sample CLI tool for testing
    - Environment variables

    Returns:
        dict: Dictionary containing environment information
    """
    # Create output directory
    output_dir = Path(functional_test_dir) / "output"
    output_dir.mkdir(exist_ok=True)

    # Get the tool name from the path (without extension)
    tool_name = Path(sample_cli_tool_path).stem

    return {
        "output_dir": str(output_dir),
        "tool_path": sample_cli_tool_path,
        "tool_name": tool_name
    }