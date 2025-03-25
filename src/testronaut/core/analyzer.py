"""
CLI Analyzer module.

This module is responsible for analyzing CLI tools and extracting their command structure.
It uses a combination of parsing help text and LLM-based analysis to understand
the CLI tool's capabilities.
"""

import logging
import subprocess
from typing import Any, Dict, List, Optional

from testronaut.llm.manager import LLMManager
from testronaut.models.cli_tool import CLITool
from testronaut.models.command import Argument, Command, Option

logger = logging.getLogger(__name__)


class CLIAnalyzer:
    """Analyzer for CLI tools."""

    def __init__(self, llm_manager: LLMManager):
        """Initialize CLI analyzer.

        Args:
            llm_manager: LLM manager for AI-assisted analysis
        """
        self.llm_manager = llm_manager

    def analyze_tool(self, tool_name: str, install_cmd: Optional[str] = None) -> CLITool:
        """Analyze a CLI tool and extract its command structure.

        Args:
            tool_name: Name or path of the CLI tool
            install_cmd: Command to install the tool if not already installed

        Returns:
            CLITool object containing the tool's metadata and commands
        """
        logger.info(f"Analyzing CLI tool: {tool_name}")

        # Install tool if needed and if install command is provided
        if install_cmd:
            self._install_tool(install_cmd)

        # Extract help text
        help_text = self._extract_help_text(tool_name)

        # Use LLM to analyze help text
        tool_metadata = self._analyze_with_llm(tool_name, help_text)

        # Create CLI tool object
        cli_tool = CLITool(
            name=tool_name,
            version=tool_metadata.get("version", "unknown"),
            help_text=help_text,
            description=tool_metadata.get("description", ""),
            commands=self._extract_commands(tool_name, tool_metadata),
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

    def _analyze_with_llm(self, tool_name: str, help_text: str) -> Dict[str, Any]:
        """Use LLM to analyze help text and extract tool metadata.

        Args:
            tool_name: Name of the CLI tool
            help_text: Help text from the tool

        Returns:
            Dictionary containing tool metadata
        """
        logger.info(f"Analyzing help text with LLM for: {tool_name}")

        prompt = f"""
        Analyze the following help text for the CLI tool '{tool_name}' and extract its structure:

        ```
        {help_text}
        ```

        Extract the following information:
        1. Tool version (if available)
        2. Tool description
        3. List of available commands
        4. For each command, extract:
           - Command name
           - Command description
           - Options (flags) with their descriptions
           - Arguments with their descriptions

        Format your response as a structured JSON object.
        """

        response = self.llm_manager.generate(prompt)

        try:
            # The LLM should return a JSON string, which we parse
            # In a real implementation, this would include proper JSON handling
            # For this example, we assume the response is already a dict
            return response
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            raise RuntimeError("Failed to analyze CLI tool structure with LLM")

    def _extract_commands(self, tool_name: str, tool_metadata: Dict[str, Any]) -> List[Command]:
        """Extract commands from tool metadata.

        Args:
            tool_name: Name of the CLI tool
            tool_metadata: Metadata extracted by LLM

        Returns:
            List of Command objects
        """
        commands = []

        # Extract commands from metadata
        raw_commands = tool_metadata.get("commands", [])

        for cmd_data in raw_commands:
            # Extract options
            options = []
            for opt_data in cmd_data.get("options", []):
                option = Option(
                    name=opt_data.get("name", ""),
                    short_form=opt_data.get("short_form", ""),
                    long_form=opt_data.get("long_form", ""),
                    description=opt_data.get("description", ""),
                    required=opt_data.get("required", False),
                    default_value=opt_data.get("default_value", ""),
                    value_type=opt_data.get("value_type", "string"),
                )
                options.append(option)

            # Extract arguments
            arguments = []
            for arg_data in cmd_data.get("arguments", []):
                argument = Argument(
                    name=arg_data.get("name", ""),
                    description=arg_data.get("description", ""),
                    required=arg_data.get("required", False),
                    default_value=arg_data.get("default_value", ""),
                    value_type=arg_data.get("value_type", "string"),
                    position=arg_data.get("position", 0),
                )
                arguments.append(argument)

            # Create command
            command = Command(
                name=cmd_data.get("name", ""),
                description=cmd_data.get("description", ""),
                syntax=cmd_data.get("syntax", ""),
                help_text=cmd_data.get("help_text", ""),
                is_subcommand=cmd_data.get("is_subcommand", False),
                parent_command_id=cmd_data.get("parent_command_id", ""),
                options=options,
                arguments=arguments,
            )

            commands.append(command)

        return commands
