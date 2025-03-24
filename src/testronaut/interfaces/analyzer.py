"""
CLI Analyzer Interface.

This module defines the interface for analyzing CLI tools and commands.
"""
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable
from pathlib import Path

from testronaut.models import CLITool, Command


@runtime_checkable
class CLIAnalyzer(Protocol):
    """Protocol defining the interface for CLI tool analyzers."""

    def analyze_cli_tool(self, tool_name: str, version: Optional[str] = None) -> CLITool:
        """
        Analyze a CLI tool and extract its commands, options, and arguments.

        Args:
            tool_name: The name of the CLI tool to analyze.
            version: Optional specific version of the tool to analyze.

        Returns:
            A CLITool object with all extracted information.

        Raises:
            CommandExecutionError: If the tool cannot be executed.
            ValidationError: If the tool information cannot be validated.
        """
        ...

    def update_command_info(self, command: Command) -> Command:
        """
        Update and enrich the information for a specific command.

        Args:
            command: The command object to update.

        Returns:
            The updated command object with enriched information.

        Raises:
            CommandExecutionError: If the command cannot be executed.
            ValidationError: If the command information cannot be validated.
        """
        ...

    def extract_examples(self, command: Command) -> List[Dict[str, Any]]:
        """
        Extract usage examples for a specific command.

        Args:
            command: The command to extract examples for.

        Returns:
            A list of dictionaries containing example information.

        Raises:
            CommandExecutionError: If the command help cannot be executed.
            ValidationError: If the examples cannot be extracted.
        """
        ...

    def verify_tool_installation(self, tool_name: str) -> bool:
        """
        Verify if a CLI tool is installed and accessible.

        Args:
            tool_name: The name of the CLI tool to verify.

        Returns:
            True if the tool is installed, False otherwise.
        """
        ...

    def get_tool_help_text(self, tool_name: str) -> str:
        """
        Get the help text for a CLI tool.

        Args:
            tool_name: The name of the CLI tool.

        Returns:
            The help text as a string.

        Raises:
            CommandExecutionError: If the help command cannot be executed.
        """
        ...

    def get_command_help_text(self, tool_name: str, command_name: str) -> str:
        """
        Get the help text for a specific command of a CLI tool.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.

        Returns:
            The help text as a string.

        Raises:
            CommandExecutionError: If the help command cannot be executed.
        """
        ...