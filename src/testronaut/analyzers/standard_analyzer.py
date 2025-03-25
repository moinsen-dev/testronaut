"""
Standard CLI Analyzer Implementation.

This module provides a standard implementation of the CLI analyzer interface.
"""

import re
from typing import Any, Dict, List, Optional, Set

from testronaut.interfaces import CLIAnalyzer
from testronaut.models import Argument, CLITool, Command, Example, Option
from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import CommandExecutionError
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

    def get_command_help_text(
        self, tool_name: str, command_name: str, parent_path: str = ""
    ) -> str:
        """
        Get the help text for a specific command of a CLI tool.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            parent_path: The parent command path (if this is a subcommand).

        Returns:
            The help text as a string.

        Raises:
            CommandExecutionError: If the help command cannot be executed.
        """
        # Build the full command path
        if parent_path:
            full_cmd = f"{tool_name} {parent_path} {command_name}"
        else:
            full_cmd = f"{tool_name} {command_name}"

        logger.debug(f"Getting help text for command: {full_cmd}")

        # First, try the most reliable option: --help
        try:
            result = self.command_runner.run(f"{full_cmd} --help")
            if result.succeeded:
                return result.output
        except CommandExecutionError:
            logger.debug(f"Failed to get help with --help for {full_cmd}")

        # Then, try shorter help option
        try:
            result = self.command_runner.run(f"{full_cmd} -h")
            if result.succeeded:
                return result.output
        except CommandExecutionError:
            logger.debug(f"Failed to get help with -h for {full_cmd}")

        # Try help subcommand format (e.g., git help commit)
        try:
            result = self.command_runner.run(f"{tool_name} help {command_name}")
            if result.succeeded:
                return result.output
        except CommandExecutionError:
            logger.debug(f"Failed to get help with help subcommand for {full_cmd}")

        # Try running the command with no arguments if it's a subcommand
        if parent_path:
            try:
                result = self.command_runner.run(full_cmd)
                if result.succeeded:
                    return result.output
            except CommandExecutionError:
                logger.debug(f"Failed to run command without args: {full_cmd}")

        # If all attempts failed, raise an error
        raise CommandExecutionError(
            f"Failed to get help text for command {full_cmd}",
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
        existing_cmd_names = set()  # Track command names to avoid duplicates

        # Look for the "Commands" section in the help text
        # This pattern works for rich-formatted CLI help (like Typer with rich formatting)
        commands_section_match = re.search(
            r"Commands[^\n]*\n(.*?)(?:\n\n|\Z)", help_text, re.DOTALL
        )

        if commands_section_match:
            commands_section = commands_section_match.group(1)
            # Process each line in the commands section
            for line in commands_section.split("\n"):
                # Skip separator lines and empty lines
                if not line.strip() or re.match(
                    r"^[\s\u2500\u256d\u256e\u2570\u256f\u2502]+$", line
                ):
                    continue

                # Extract command name and description
                # This works for "command    description" format
                parts = re.split(r"\s{2,}", line.strip(), maxsplit=1)
                if len(parts) >= 1:
                    # Clean up command name (remove UI characters)
                    cmd_name = parts[0].strip()
                    cmd_name = re.sub(
                        r"[\u2500\u256d\u256e\u2570\u256f\u2502]", "", cmd_name
                    ).strip()

                    # Clean up description
                    cmd_desc = parts[1].strip() if len(parts) > 1 else None
                    if cmd_desc:
                        cmd_desc = re.sub(
                            r"[\u2500\u256d\u256e\u2570\u256f\u2502]", "", cmd_desc
                        ).strip()

                    # Check for duplicates (case-insensitive)
                    if cmd_name.lower() not in existing_cmd_names:
                        commands.append({"name": cmd_name, "description": cmd_desc})
                        existing_cmd_names.add(cmd_name.lower())

        # If no commands were found with the above pattern, try simpler patterns
        if not commands:
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
                            cmd_name = match[0].strip()
                            cmd_desc = match[1].strip() if len(match) > 1 else None

                            # Check for duplicates (case-insensitive)
                            if cmd_name.lower() not in existing_cmd_names:
                                commands.append({"name": cmd_name, "description": cmd_desc})
                                existing_cmd_names.add(cmd_name.lower())
                    else:
                        # Otherwise, we have a block of text with commands
                        for block in matches:
                            for line in block.split("\n"):
                                if line.strip():
                                    parts = line.strip().split(maxsplit=1)
                                    cmd_name = parts[0].strip()
                                    cmd_desc = parts[1].strip() if len(parts) > 1 else None

                                    # Check for duplicates (case-insensitive)
                                    if cmd_name.lower() not in existing_cmd_names:
                                        commands.append({"name": cmd_name, "description": cmd_desc})
                                        existing_cmd_names.add(cmd_name.lower())

        logger.debug(f"Extracted {len(commands)} commands from help text")
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

        # Build command path for subcommands by traversing the parent chain
        command_path_parts: List[str] = []
        current_command = command

        # First, check if the command has a parent
        while hasattr(current_command, "parent_command_id") and current_command.parent_command_id:
            # Find the parent command by ID
            parent_command = None
            for cmd in command.cli_tool.commands:
                if hasattr(cmd, "id") and cmd.id == current_command.parent_command_id:
                    parent_command = cmd
                    break

            # If found, add to path and continue up the chain
            if parent_command and hasattr(parent_command, "name"):
                command_path_parts.insert(0, parent_command.name)
                current_command = parent_command
            else:
                break

        # Build the full command path
        command_path = " ".join(command_path_parts)

        # Build the full command string
        if command_path:
            full_cmd = f"{tool_name} {command_path} {command_name}"
        else:
            full_cmd = f"{tool_name} {command_name}"

        try:
            help_text = self.get_command_help_text(
                tool_name, command_name, parent_path=command_path
            )
        except CommandExecutionError:
            logger.warning(f"Could not get help text for {full_cmd}")
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

    def update_command_info(
        self, command: Command, processed_commands: Optional[Set[str]] = None
    ) -> Command:
        """
        Update and enrich the information for a specific command.

        Args:
            command: The command object to update.
            processed_commands: Set of already processed command IDs to prevent cycles.

        Returns:
            The updated command object with enriched information.

        Raises:
            CommandExecutionError: If the command cannot be executed.
            ValidationError: If the command information cannot be validated.
        """
        # Initialize processed_commands set if not provided
        if processed_commands is None:
            processed_commands = set()

        # Check if command has already been processed to prevent cycles
        command_id = getattr(command, "id", None)
        if command_id and command_id in processed_commands:
            logger.warning(
                f"Cycle detected: Command {command.name} has already been processed. Skipping."
            )
            return command

        # Add current command ID to processed set
        if command_id:
            processed_commands.add(command_id)

        logger.debug(f"Updating information for command: {command.name}")

        try:
            # Build command path for subcommands by traversing the parent chain
            command_path_parts: List[str] = []
            current_command = command

            # First, check if the command has a parent
            while (
                hasattr(current_command, "parent_command_id") and current_command.parent_command_id
            ):
                # Find the parent command by ID
                parent_command = None
                for cmd in command.cli_tool.commands:
                    if hasattr(cmd, "id") and cmd.id == current_command.parent_command_id:
                        parent_command = cmd
                        break

                # If found, add to path and continue up the chain
                if parent_command and hasattr(parent_command, "name"):
                    command_path_parts.insert(0, parent_command.name)
                    current_command = parent_command
                else:
                    break

            # Build the full command path
            command_path = " ".join(command_path_parts)

            help_text = self.get_command_help_text(
                command.cli_tool.name, command.name, command_path
            )
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

            # Extract subcommands by analyzing help text for this command
            # Build the command path for subcommand extraction
            cmd_path = command.name
            if command_path:
                cmd_path = f"{command_path} {cmd_path}"

            subcommands_data = self.extract_commands(
                f"{command.cli_tool.name} {cmd_path}", help_text
            )

            # Process subcommands
            if subcommands_data:
                for subcmd_data in subcommands_data:
                    # Check if this subcommand already exists
                    subcmd_name = subcmd_data.get("name", "")

                    # Skip if the subcommand name is the same as the parent to avoid cycles
                    if subcmd_name.lower() == command.name.lower():
                        logger.warning(
                            f"Skipping subcommand {subcmd_name} to avoid cycle with parent command {command.name}"
                        )
                        continue

                    existing_subcmd = None
                    for cmd in command.cli_tool.commands:
                        if (
                            hasattr(cmd, "name")
                            and hasattr(cmd, "parent_command_id")
                            and getattr(cmd, "name", "").lower() == subcmd_name.lower()
                            and getattr(cmd, "parent_command_id", None) == command.id
                        ):
                            existing_subcmd = cmd
                            break

                    if not existing_subcmd:
                        # Create new subcommand
                        subcommand = Command(
                            cli_tool_id=command.cli_tool.id,
                            name=subcmd_name,
                            description=subcmd_data.get("description"),
                            parent_command_id=command.id,
                            is_subcommand=True,
                        )
                        command.cli_tool.commands.append(subcommand)

            return command
        except CommandExecutionError as e:
            logger.error(f"Failed to update command {command.name}: {str(e)}")
            raise CommandExecutionError(
                f"Failed to update command {command.name}", details={"error": str(e)}
            )

    def analyze_cli_tool(self, tool_name: str, version: Optional[str] = None) -> CLITool:
        """
        Analyze a CLI tool and extract its commands, options, and arguments.
        Uses a two-phase approach to prevent cycles and provide accurate progress reporting.

        Args:
            tool_name: The name of the CLI tool to analyze.
            version: Optional specific version of the tool to analyze.

        Returns:
            A CLITool object with all extracted information.

        Raises:
            CommandExecutionError: If the tool cannot be executed.
            ValidationError: If the tool information cannot be validated.
        """
        logger.debug(f"Analyzing CLI tool: {tool_name}")

        # Check if tool is installed
        logger.debug(f"Step 1/7: Verifying installation of {tool_name}...")
        if not self.verify_tool_installation(tool_name):
            raise CommandExecutionError(
                f"CLI tool {tool_name} is not installed or not found in PATH",
                details={"solution": f"Install {tool_name} or provide the full path"},
            )

        # Get tool help text
        logger.debug(f"Step 2/7: Retrieving main help text for {tool_name}...")
        help_text = self.get_tool_help_text(tool_name)

        # Get tool version if not provided
        if not version:
            logger.debug(f"Step 3/7: Detecting version of {tool_name}...")
            version = self.get_tool_version(tool_name)
            logger.debug(f"Detected version: {version or 'unknown'}")

        # Create CLI tool model
        cli_tool = CLITool(name=tool_name, version=version, help_text=help_text)

        # Extract description from help text
        desc_match = re.search(
            r"(?:Description|DESCRIPTION):\s*(.*?)$", help_text, re.MULTILINE | re.DOTALL
        )
        if desc_match:
            cli_tool.description = desc_match.group(1).strip()

        # Phase 1: Extract and discover all commands (discovery phase)
        logger.debug(f"Step 4/7: Extracting top-level commands for {tool_name}...")
        commands_data = self.extract_commands(tool_name, help_text)
        logger.debug(f"Found {len(commands_data)} top-level commands")

        # Create command models for top-level commands
        for cmd_data in commands_data:
            command = Command(
                cli_tool_id=cli_tool.id,
                name=cmd_data.get("name", ""),
                description=cmd_data.get("description"),
            )
            cli_tool.commands.append(command)

        # Phase 1.5: Build command tree structure and count total commands
        logger.debug("Step 5/7: Building command tree structure...")
        # A set to track discovered command IDs and prevent cycles
        discovered_cmds: Set[str] = set()

        # Discovery queue
        discovery_queue = list(cli_tool.commands)
        discovery_index = 0

        # Discover subcommands without full analysis
        while discovery_index < len(discovery_queue):
            command = discovery_queue[discovery_index]
            discovery_index += 1

            # Skip if already discovered
            command_id = getattr(command, "id", None)
            if command_id and command_id in discovered_cmds:
                continue

            if command_id:
                discovered_cmds.add(command_id)

            logger.debug(f"Discovering command structure: {command.name}")

            # Build command path for this command
            cmd_path_parts: List[str] = []
            curr = command
            while hasattr(curr, "parent_command_id") and curr.parent_command_id:
                # Find parent
                parent = None
                for cmd in cli_tool.commands:
                    if hasattr(cmd, "id") and cmd.id == curr.parent_command_id:
                        parent = cmd
                        break

                if parent and hasattr(parent, "name"):
                    cmd_path_parts.insert(0, parent.name)
                    curr = parent
                else:
                    break

            cmd_path = " ".join(cmd_path_parts)

            # Get help text for this command
            try:
                cmd_help = self.get_command_help_text(cli_tool.name, command.name, cmd_path)

                # Extract subcommands
                subcmd_path = command.name
                if cmd_path:
                    subcmd_path = f"{cmd_path} {subcmd_path}"

                subcmds_data = self.extract_commands(f"{cli_tool.name} {subcmd_path}", cmd_help)

                # Add subcommands to tree and queue
                for subcmd_data in subcmds_data:
                    subcmd_name = subcmd_data.get("name", "")

                    # Skip if the subcommand name is the same as the parent to avoid cycles
                    command_name = getattr(command, "name", "")
                    if subcmd_name.lower() == command_name.lower():
                        logger.warning(
                            f"Skipping subcommand {subcmd_name} to avoid cycle with parent command {command_name}"
                        )
                        continue

                    # Check if this subcommand already exists
                    existing = None
                    for cmd in cli_tool.commands:
                        if (
                            hasattr(cmd, "name")
                            and hasattr(cmd, "parent_command_id")
                            and getattr(cmd, "name", "").lower() == subcmd_name.lower()
                            and getattr(cmd, "parent_command_id", None) == command_id
                        ):
                            existing = cmd
                            break

                    if not existing:
                        # Create new subcommand
                        subcommand = Command(
                            cli_tool_id=cli_tool.id,
                            name=subcmd_name,
                            description=subcmd_data.get("description"),
                            parent_command_id=command_id,
                            is_subcommand=True,
                        )
                        cli_tool.commands.append(subcommand)
                        discovery_queue.append(subcommand)
            except Exception as e:
                logger.warning(
                    f"Error discovering subcommands for {getattr(command, 'name', 'unknown')}: {str(e)}"
                )

        # Count total commands for accurate progress reporting
        total_commands = len(cli_tool.commands)
        logger.debug(f"Discovered {total_commands} total commands in command tree")

        # Phase 2: Analyze each command with detailed information
        logger.debug("Step 6/7: Analyzing detailed command information...")
        processed_commands: Set[str] = set()  # Track processed commands to prevent cycles

        for i, command in enumerate(cli_tool.commands):
            logger.debug(
                f"Analyzing command {i + 1}/{total_commands}: {getattr(command, 'name', 'unknown')}"
            )
            self.update_command_info(command, processed_commands)

        # Clean up duplicate commands with different capitalization
        logger.debug("Step 7/7: Cleaning up and finalizing analysis...")
        self._clean_up_duplicate_commands(cli_tool)

        # Count total commands including subcommands
        top_level_count = 0
        subcommand_count = 0
        for cmd in cli_tool.commands:
            if not hasattr(cmd, "is_subcommand") or not getattr(cmd, "is_subcommand", False):
                top_level_count += 1
            else:
                subcommand_count += 1

        logger.debug(
            f"Analysis complete! Found {top_level_count} top-level commands and {subcommand_count} subcommands"
        )
        return cli_tool

    def _clean_up_duplicate_commands(self, cli_tool: CLITool) -> None:
        """
        Clean up duplicate commands with different capitalization.

        Args:
            cli_tool: The CLI tool to clean up.
        """
        # Track commands by lowercase name
        commands_by_name: Dict[str, Command] = {}
        duplicates_to_remove: List[Command] = []

        # First, identify duplicates
        for cmd in cli_tool.commands:
            if not hasattr(cmd, "name"):
                continue

            lower_name = cmd.name.lower()
            if lower_name in commands_by_name:
                # Keep the one with the lowercase name or the first one found
                if hasattr(cmd, "name") and cmd.name.islower():
                    duplicates_to_remove.append(commands_by_name[lower_name])
                    commands_by_name[lower_name] = cmd
                else:
                    duplicates_to_remove.append(cmd)
            else:
                commands_by_name[lower_name] = cmd

        # Remove duplicates
        for cmd in duplicates_to_remove:
            if cmd in cli_tool.commands:
                cli_tool.commands.remove(cmd)

        # Do the same for subcommands
        for cmd in cli_tool.commands:
            self._clean_up_duplicate_subcommands(cmd)

    def _clean_up_duplicate_subcommands(self, command: Command) -> None:
        """
        Clean up duplicate subcommands with different capitalization.

        Args:
            command: The command to clean up subcommands for.
        """
        # Track subcommands by lowercase name
        subcommands_by_name: Dict[str, Command] = {}
        duplicates_to_remove: List[Command] = []

        # First, identify duplicates
        for subcmd in command.subcommands:
            if not hasattr(subcmd, "name"):
                continue

            lower_name = subcmd.name.lower()
            if lower_name in subcommands_by_name:
                # Keep the one with the lowercase name or the first one found
                if hasattr(subcmd, "name") and subcmd.name.islower():
                    duplicates_to_remove.append(subcommands_by_name[lower_name])
                    subcommands_by_name[lower_name] = subcmd
                else:
                    duplicates_to_remove.append(subcmd)
            else:
                subcommands_by_name[lower_name] = subcmd

        # Remove duplicates
        for subcmd in duplicates_to_remove:
            if subcmd in command.subcommands:
                command.subcommands.remove(subcmd)

        # Do the same for nested subcommands
        for subcmd in command.subcommands:
            self._clean_up_duplicate_subcommands(subcmd)

    def _count_subcommands(self, command: Command) -> int:
        """
        Recursively count subcommands of a command.

        Args:
            command: The command to count subcommands for.

        Returns:
            The total number of subcommands.
        """
        count = len(command.subcommands)
        for subcmd in command.subcommands:
            count += self._count_subcommands(subcmd)
        return count
