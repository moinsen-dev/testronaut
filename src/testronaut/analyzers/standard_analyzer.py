"""
Standard CLI Analyzer Implementation.

This module provides a standard implementation of the CLI analyzer interface.
"""

import re
from typing import Any, Dict, List, Optional

from testronaut.interfaces import CLIAnalyzer
from testronaut.models import Argument, CLITool, Command, Example, Option
from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import CommandExecutionError, ValidationError
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class StandardCLIAnalyzer(CLIAnalyzer):
    """Standard implementation of CLI tool analyzer."""

    def __init__(self, command_runner: Optional[CommandRunner] = None):
        """
        Initialize the CLI analyzer.

        Args:
            command_runner: Command runner for executing CLI commands.
        """
        self.command_runner = command_runner or CommandRunner()
        # Common help options across many CLI tools
        self.help_options = ["--help", "-h", "help"]

    def verify_tool_installation(self, tool_name: str) -> bool:
        """
        Verify if a CLI tool is installed and accessible.

        Args:
            tool_name: The name of the CLI tool to verify.

        Returns:
            True if the tool is installed, False otherwise.
        """
        logger.debug(f"Verifying installation of tool: {tool_name}")
        return self.command_runner.is_command_available(tool_name)

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
        logger.debug(f"Getting help text for tool: {tool_name}")

        # Try different help options
        for help_option in self.help_options:
            try:
                result = self.command_runner.run(f"{tool_name} {help_option}")
                if result.succeeded:
                    return result.output
            except CommandExecutionError:
                continue

        # If no help option worked, try without any options
        try:
            result = self.command_runner.run(tool_name)
            return result.output
        except CommandExecutionError as e:
            logger.error(f"Failed to get help text for {tool_name}: {str(e)}")
            raise CommandExecutionError(
                f"Failed to get help text for {tool_name}", details={"error": str(e)}
            )

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
        logger.debug(f"Getting help text for command: {tool_name} {command_name}")

        # Try different help options
        for help_option in self.help_options:
            try:
                result = self.command_runner.run(f"{tool_name} {command_name} {help_option}")
                if result.succeeded:
                    return result.output
            except CommandExecutionError:
                continue

        # Try help command format (e.g., git help commit)
        try:
            result = self.command_runner.run(f"{tool_name} help {command_name}")
            if result.succeeded:
                return result.output
        except CommandExecutionError:
            pass

        raise CommandExecutionError(
            f"Failed to get help text for command {tool_name} {command_name}",
            details={"attempted_options": self.help_options},
        )

    def get_tool_version(self, tool_name: str) -> Optional[str]:
        """
        Get the version of a CLI tool.

        Args:
            tool_name: The name of the CLI tool.

        Returns:
            The version as a string, or None if not found.
        """
        logger.debug(f"Getting version for tool: {tool_name}")

        # Common version options
        version_options = ["--version", "-V", "-v", "version"]

        for option in version_options:
            try:
                result = self.command_runner.run(f"{tool_name} {option}")
                if result.succeeded:
                    # Extract version using regex
                    version_match = re.search(r"(\d+\.\d+\.\d+)", result.output)
                    if version_match:
                        return version_match.group(1)
                    return result.output.strip()
            except CommandExecutionError:
                continue

        return None

    def extract_commands(self, tool_name: str, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract commands from the help text of a CLI tool.

        Args:
            tool_name: The name of the CLI tool.
            help_text: The help text of the tool.

        Returns:
            A list of dictionaries with command information.
        """
        logger.debug(f"Extracting commands for tool: {tool_name}")
        commands = []

        # Common patterns for commands in help text
        command_patterns = [
            # Pattern for "Commands:" section with indented commands
            r"(?:Commands|Available commands):\s*\n((?:\s+\w+\s+.*\n)+)",
            # Pattern for "Subcommands:" section
            r"(?:Subcommands):\s*\n((?:\s+\w+.*\n)+)",
            # Pattern for command lists with descriptions
            r"^\s+(\w+)\s+(.*?)$",
        ]

        for pattern in command_patterns:
            matches = re.findall(pattern, help_text, re.MULTILINE)
            if matches:
                if isinstance(matches[0], tuple):
                    # If matches are tuples, we have command and description
                    for match in matches:
                        commands.append(
                            {
                                "name": match[0].strip(),
                                "description": match[1].strip() if len(match) > 1 else None,
                            }
                        )
                else:
                    # Otherwise, we have a block of text with commands
                    for block in matches:
                        for line in block.split("\n"):
                            if line.strip():
                                parts = line.strip().split(maxsplit=1)
                                cmd_name = parts[0].strip()
                                cmd_desc = parts[1].strip() if len(parts) > 1 else None
                                commands.append({"name": cmd_name, "description": cmd_desc})

        return commands

    def extract_options(self, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract options from the help text.

        Args:
            help_text: The help text to parse.

        Returns:
            A list of dictionaries with option information.
        """
        logger.debug("Extracting options from help text")
        options = []

        # Common patterns for options in help text
        option_patterns = [
            # Pattern for "-o, --option DESCRIPTION" format
            r"^\s+(-\w),?\s+(--[\w-]+)(?:\s+[<[][\w-]+[>\]])?\s+(.*?)$",
            # Pattern for "--option DESCRIPTION" format
            r"^\s+(--[\w-]+)(?:\s+[<[][\w-]+[>\]])?\s+(.*?)$",
            # Pattern for "-o DESCRIPTION" format
            r"^\s+(-\w)(?:\s+[<[][\w-]+[>\]])?\s+(.*?)$",
        ]

        for pattern in option_patterns:
            matches = re.findall(pattern, help_text, re.MULTILINE)
            for match in matches:
                if len(match) == 3:  # short and long form
                    options.append(
                        {
                            "short_form": match[0],
                            "long_form": match[1],
                            "description": match[2].strip(),
                            "name": match[1].lstrip("-"),
                        }
                    )
                elif len(match) == 2:  # only one form
                    form = match[0]
                    is_short = form.startswith("-") and not form.startswith("--")
                    options.append(
                        {
                            "short_form": form if is_short else None,
                            "long_form": None if is_short else form,
                            "description": match[1].strip(),
                            "name": form.lstrip("-"),
                        }
                    )

        return options

    def extract_arguments(self, help_text: str) -> List[Dict[str, Any]]:
        """
        Extract arguments from the help text.

        Args:
            help_text: The help text to parse.

        Returns:
            A list of dictionaries with argument information.
        """
        logger.debug("Extracting arguments from help text")
        arguments = []

        # Common patterns for arguments in help text
        arg_patterns = [
            # Pattern for "ARG Description" format
            r"^\s+([A-Z_]+|\<[\w-]+\>|\[[\w-]+\])\s+(.*?)$",
        ]

        position = 0
        for pattern in arg_patterns:
            matches = re.findall(pattern, help_text, re.MULTILINE)
            for match in matches:
                # Skip if it looks like an option
                if match[0].startswith("-"):
                    continue

                # Determine if required based on brackets
                required = not (match[0].startswith("[") and match[0].endswith("]"))

                # Clean up the name
                name = match[0].strip("<>[]").lower()

                arguments.append(
                    {
                        "name": name,
                        "description": match[1].strip(),
                        "required": required,
                        "position": position,
                    }
                )
                position += 1

        return arguments

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
        logger.debug(f"Extracting examples for command: {command.name}")

        tool_name = command.cli_tool.name
        command_name = command.name

        try:
            help_text = self.get_command_help_text(tool_name, command_name)
        except CommandExecutionError:
            logger.warning(f"Could not get help text for {tool_name} {command_name}")
            return []

        examples = []

        # Common patterns for examples in help text
        example_patterns = [
            # Pattern for "Examples:" section
            r"(?:Examples|EXAMPLES):\s*\n((?:\s+.*\n)+)",
            # Pattern for individual example lines
            r"^\s+(\$\s+.*|\w+\s+.*?:.*)",
        ]

        for pattern in example_patterns:
            matches = re.findall(pattern, help_text, re.MULTILINE)

            if matches:
                if len(matches[0].split("\n")) > 1:  # Block of examples
                    for block in matches:
                        for line in block.split("\n"):
                            line = line.strip()
                            if line:
                                # Remove prompts like "$" or ">"
                                cmd_line = re.sub(r"^\s*[$>]\s*", "", line)
                                if cmd_line.startswith(tool_name):
                                    examples.append({"command_line": cmd_line, "description": None})
                else:  # Individual examples
                    for match in matches:
                        # Remove prompts like "$" or ">"
                        cmd_line = re.sub(r"^\s*[$>]\s*", "", match)
                        if cmd_line.startswith(tool_name):
                            examples.append({"command_line": cmd_line, "description": None})

        return examples

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
        logger.debug(f"Updating information for command: {command.name}")

        try:
            help_text = self.get_command_help_text(command.cli_tool.name, command.name)
            command.help_text = help_text

            # Extract syntax if available
            syntax_match = re.search(r"(?:Usage|USAGE):\s*(.*?)$", help_text, re.MULTILINE)
            if syntax_match:
                command.syntax = syntax_match.group(1).strip()

            # Extract description if available
            desc_match = re.search(
                r"(?:Description|DESCRIPTION):\s*(.*?)$", help_text, re.MULTILINE | re.DOTALL
            )
            if desc_match:
                command.description = desc_match.group(1).strip()

            # Extract options
            options_data = self.extract_options(help_text)
            for option_data in options_data:
                option = Option(
                    command_id=command.id,
                    name=option_data.get("name", ""),
                    short_form=option_data.get("short_form"),
                    long_form=option_data.get("long_form"),
                    description=option_data.get("description"),
                    required=False,  # Usually options are optional
                )
                command.options.append(option)

            # Extract arguments
            args_data = self.extract_arguments(help_text)
            for arg_data in args_data:
                argument = Argument(
                    command_id=command.id,
                    name=arg_data.get("name", ""),
                    description=arg_data.get("description"),
                    required=arg_data.get("required", False),
                    position=arg_data.get("position", 0),
                )
                command.arguments.append(argument)

            # Extract examples
            examples_data = self.extract_examples(command)
            for example_data in examples_data:
                example = Example(
                    command_id=command.id,
                    command_line=example_data.get("command_line", ""),
                    description=example_data.get("description"),
                )
                command.examples.append(example)

            return command

        except (CommandExecutionError, ValidationError) as e:
            logger.error(f"Failed to update command {command.name}: {str(e)}")
            # Return the command as-is without raising to allow partial processing
            return command

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
        logger.info(f"Analyzing CLI tool: {tool_name}")

        # Check if tool is installed
        if not self.verify_tool_installation(tool_name):
            raise CommandExecutionError(
                f"CLI tool {tool_name} is not installed or not found in PATH",
                details={"solution": f"Install {tool_name} or provide the full path"},
            )

        # Get tool help text
        help_text = self.get_tool_help_text(tool_name)

        # Get tool version if not provided
        if not version:
            version = self.get_tool_version(tool_name)

        # Create CLI tool model
        cli_tool = CLITool(name=tool_name, version=version, help_text=help_text)

        # Extract description from help text
        desc_match = re.search(
            r"(?:Description|DESCRIPTION):\s*(.*?)$", help_text, re.MULTILINE | re.DOTALL
        )
        if desc_match:
            cli_tool.description = desc_match.group(1).strip()

        # Extract commands
        commands_data = self.extract_commands(tool_name, help_text)

        # Create command models
        for cmd_data in commands_data:
            command = Command(
                cli_tool_id=cli_tool.id,
                name=cmd_data.get("name", ""),
                description=cmd_data.get("description"),
            )
            cli_tool.commands.append(command)

        # Update each command with more detailed information
        for command in cli_tool.commands:
            self.update_command_info(command)

        logger.info(f"Completed analysis of {tool_name}, found {len(cli_tool.commands)} commands")
        return cli_tool
