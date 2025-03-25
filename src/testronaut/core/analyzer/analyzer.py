"""
CLI Analyzer module.

This module is responsible for analyzing CLI tools and extracting their command structure.
It uses a combination of parsing help text and LLM-based analysis to understand
the CLI tool's capabilities.
"""

import logging
import re
import subprocess
from typing import Any, Dict, Optional

from testronaut.core.models import CliTool, Command, CommandParameter

logger = logging.getLogger(__name__)


class CliAnalyzer:
    """Analyzer for CLI tools."""

    def __init__(self, llm_manager=None):
        """Initialize CLI analyzer.

        Args:
            llm_manager: LLM manager for AI-assisted analysis
        """
        self.llm_manager = llm_manager

    def analyze_tool(self, tool_name: str, install_cmd: Optional[str] = None) -> CliTool:
        """Analyze a CLI tool and extract its command structure.

        Args:
            tool_name: Name or path of the CLI tool
            install_cmd: Command to install the tool if not already installed

        Returns:
            CliTool object containing the tool's metadata and commands
        """
        logger.info(f"Analyzing CLI tool: {tool_name}")

        # Install tool if needed and if install command is provided
        if install_cmd:
            self._install_tool(install_cmd)

        # Extract help text
        help_text = self._extract_help_text(tool_name)

        # Use LLM to analyze help text
        # In the initial version, without real LLM integration,
        # we'll use a simple parser for basic tools
        tool_metadata = self._analyze_help_text(tool_name, help_text)

        # Create CLI tool object
        commands_dict = {}
        for cmd_data in tool_metadata.get("commands", []):
            cmd_name = cmd_data.get("name", "")
            parameters = []

            # Convert options to parameters
            for opt_data in cmd_data.get("options", []):
                param = CommandParameter(
                    name=opt_data.get("name", ""),
                    description=opt_data.get("description", ""),
                    required=opt_data.get("required", False),
                    default=opt_data.get("default", None),
                    type=opt_data.get("type", "string"),
                    is_flag=opt_data.get("is_flag", False),
                    short_option=opt_data.get("short_option"),
                    long_option=opt_data.get("long_option"),
                )
                parameters.append(param)

            command = Command(
                name=cmd_name,
                description=cmd_data.get("description", ""),
                usage=cmd_data.get("usage", ""),
                parameters=parameters,
            )
            commands_dict[cmd_name] = command

        # Create the CLI tool object
        cli_tool = CliTool(
            name=tool_name,
            description=tool_metadata.get("description", ""),
            version=tool_metadata.get("version", "unknown"),
            commands=commands_dict,
            help_text=help_text,
            bin_path=tool_name,
            install_command=install_cmd,
        )

        return cli_tool

    def _install_tool(self, install_cmd: str) -> None:
        """Install a CLI tool using the provided command.

        Args:
            install_cmd: Command to install the tool
        """
        logger.info(f"Installing tool with command: {install_cmd}")
        try:
            process = subprocess.run(
                install_cmd,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"Installation output: {process.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install tool: {e.stderr}")
            raise RuntimeError(f"Failed to install tool with command: {install_cmd}")

    def _extract_help_text(self, tool_name: str) -> str:
        """Extract help text from the CLI tool.

        Args:
            tool_name: Name or path of the CLI tool

        Returns:
            Help text from the tool
        """
        logger.info(f"Extracting help text for: {tool_name}")
        try:
            # Try with --help flag
            process = subprocess.run(
                f"{tool_name} --help",
                shell=True,
                check=False,  # Don't fail if return code is non-zero
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # If --help didn't work, try -h
            if process.returncode != 0:
                process = subprocess.run(
                    f"{tool_name} -h",
                    shell=True,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            # Combine stdout and stderr as some tools output help to stderr
            help_text = process.stdout
            if process.stderr and not help_text:
                help_text = process.stderr

            return help_text
        except Exception as e:
            logger.error(f"Failed to extract help text: {str(e)}")
            raise RuntimeError(f"Failed to extract help text from {tool_name}")

    def _analyze_help_text(self, tool_name: str, help_text: str) -> Dict[str, Any]:
        """Analyze help text to extract tool metadata.

        In the future, this will use an LLM. For now, it uses a simple parser.

        Args:
            tool_name: Name of the CLI tool
            help_text: Help text from the tool

        Returns:
            Dictionary containing tool metadata
        """
        logger.info(f"Analyzing help text for: {tool_name}")

        # Simple parser as a placeholder until LLM integration
        description = ""
        version = "unknown"
        commands = []

        # Extract description (first line that's not empty)
        lines = help_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('Usage:'):
                description = line
                break

        # Extract version
        for line in lines:
            if 'version' in line.lower():
                parts = line.split()
                for part in parts:
                    if part.replace('.', '').isdigit():
                        version = part
                        break

        # Look for 'Commands:' section to identify available commands
        command_section = False
        command_options_section = False
        current_command = None

        for i, line in enumerate(lines):
            line = line.strip()

            # Identify the commands section
            if re.match(r'commands:?$', line.lower()):
                command_section = True
                continue

            # Look for command option sections like "Command 'process' options:"
            command_options_match = re.search(r"command\s+['\"]([\w-]+)['\"]", line.lower())
            if command_options_match:
                command_options_section = True
                command_name = command_options_match.group(1)
                # Check if this command already exists in our list
                cmd_exists = False
                for cmd in commands:
                    if cmd["name"] == command_name:
                        cmd_exists = True
                        current_command = cmd
                        break

                # If it doesn't exist, add it
                if not cmd_exists:
                    current_command = {
                        "name": command_name,
                        "description": f"Options for {command_name}",
                        "options": [],
                        "usage": ""
                    }
                    commands.append(current_command)
                continue

            # Extract commands from the commands section
            if command_section and line and not line.startswith('-') and "  " in line:
                parts = line.split(maxsplit=1)
                if len(parts) > 1:
                    command_name = parts[0].strip()
                    command_desc = parts[1].strip()

                    # Check if we already have this command (from command options section)
                    cmd_exists = False
                    for cmd in commands:
                        if cmd["name"] == command_name:
                            cmd_exists = True
                            cmd["description"] = command_desc  # Update description
                            break

                    # Add if it doesn't exist
                    if not cmd_exists:
                        commands.append({
                            "name": command_name,
                            "description": command_desc,
                            "options": [],
                            "usage": ""
                        })

            # End of commands section
            elif command_section and not line:
                command_section = False

        # If no commands were found, create a default command
        if not commands:
            commands.append({
                "name": tool_name,
                "description": description,
                "options": [],
                "usage": ""
            })

        return {
            "description": description,
            "version": version,
            "commands": commands
        }