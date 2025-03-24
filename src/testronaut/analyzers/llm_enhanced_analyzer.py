"""
LLM-Enhanced CLI Analyzer Implementation.

This module provides an implementation of the CLI analyzer interface that uses
LLM capabilities to enhance the analysis of CLI tools.
"""

from typing import Any, Dict, List, Optional

from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.interfaces import CLIAnalyzer
from testronaut.models import CLITool, Command
from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import CommandExecutionError, LLMServiceError
from testronaut.utils.llm import LLMService
from testronaut.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class LLMEnhancedAnalyzer(CLIAnalyzer):
    """LLM-enhanced implementation of CLI tool analyzer."""

    def __init__(
        self,
        command_runner: Optional[CommandRunner] = None,
        llm_service: Optional[LLMService] = None,
    ):
        """
        Initialize the LLM-enhanced CLI analyzer.

        Args:
            command_runner: Command runner for executing CLI commands.
            llm_service: LLM service for enhancing analysis.
        """
        self.standard_analyzer = StandardCLIAnalyzer(command_runner)
        self.llm_service = llm_service or LLMService()

    def verify_tool_installation(self, tool_name: str) -> bool:
        """
        Verify if a CLI tool is installed and accessible.

        Args:
            tool_name: The name of the CLI tool to verify.

        Returns:
            True if the tool is installed, False otherwise.
        """
        return self.standard_analyzer.verify_tool_installation(tool_name)

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
        return self.standard_analyzer.get_tool_help_text(tool_name)

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
        return self.standard_analyzer.get_command_help_text(tool_name, command_name)

    def _enhance_description_with_llm(self, description: Optional[str], help_text: str) -> str:
        """
        Enhance a tool or command description using the LLM.

        Args:
            description: The original description.
            help_text: The full help text to analyze.

        Returns:
            Enhanced description as a string.
        """
        if not description or len(description.strip()) < 10:
            prompt = f"""
            Based on the following help text for a CLI tool or command, provide a clear,
            concise description of what it does. Focus on the main purpose and key functionality.
            Keep the description under 100 words.

            Help text:
            ```
            {help_text[:2000]}  # Limit to 2000 chars to avoid token limits
            ```
            """

            try:
                return self.llm_service.generate_text(prompt)
            except LLMServiceError as e:
                logger.warning(f"Failed to enhance description with LLM: {str(e)}")
                return description or ""
        return description or ""

    def _extract_examples_with_llm(
        self, tool_name: str, command_name: str, help_text: str
    ) -> List[Dict[str, Any]]:
        """
        Extract examples using the LLM.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            help_text: The help text to analyze.

        Returns:
            A list of dictionaries containing example information.
        """
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "command_line": {
                        "type": "string",
                        "description": "The full command line example",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the example does",
                    },
                },
                "required": ["command_line"],
            },
        }

        prompt = f"""
        Based on the following help text for the command '{tool_name} {command_name}',
        extract or generate 2-5 useful example command usages. If there are explicit examples
        in the help text, extract those. If not, generate realistic examples based on the
        available options and arguments.

        Each example should start with the full command including '{tool_name} {command_name}'.

        Help text:
        ```
        {help_text[:3000]}  # Limit to 3000 chars to avoid token limits
        ```
        """

        try:
            examples = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Generated {len(examples)} examples with LLM")
            return examples
        except LLMServiceError as e:
            logger.warning(f"Failed to extract examples with LLM: {str(e)}")
            # Fall back to standard analyzer's method if LLM fails
            return []

    def extract_examples(self, command: Command) -> List[Dict[str, Any]]:
        """
        Extract usage examples for a specific command, enhanced with LLM.

        Args:
            command: The command to extract examples for.

        Returns:
            A list of dictionaries containing example information.

        Raises:
            CommandExecutionError: If the command help cannot be executed.
            ValidationError: If the examples cannot be extracted.
        """
        # First try the standard method
        examples = self.standard_analyzer.extract_examples(command)

        # If we got no examples or just a few, try with LLM
        if len(examples) < 2:
            try:
                tool_name = command.cli_tool.name
                command_name = command.name
                help_text = command.help_text or self.get_command_help_text(tool_name, command_name)

                llm_examples = self._extract_examples_with_llm(tool_name, command_name, help_text)

                # Merge examples, avoiding duplicates
                existing_cmd_lines = {ex.get("command_line") for ex in examples}
                for ex in llm_examples:
                    if ex.get("command_line") not in existing_cmd_lines:
                        examples.append(ex)
                        existing_cmd_lines.add(ex.get("command_line"))

            except (CommandExecutionError, LLMServiceError) as e:
                logger.warning(f"Failed to enhance examples with LLM: {str(e)}")

        return examples

    def update_command_info(self, command: Command) -> Command:
        """
        Update and enrich the information for a specific command with LLM assistance.

        Args:
            command: The command object to update.

        Returns:
            The updated command object with enriched information.

        Raises:
            CommandExecutionError: If the command cannot be executed.
            ValidationError: If the command information cannot be validated.
        """
        # First update with standard analyzer
        command = self.standard_analyzer.update_command_info(command)

        try:
            # Enhance description with LLM
            if command.help_text:
                command.description = self._enhance_description_with_llm(
                    command.description, command.help_text
                )

            return command
        except Exception as e:
            logger.error(f"Failed to enhance command info with LLM: {str(e)}")
            return command

    def analyze_cli_tool(self, tool_name: str, version: Optional[str] = None) -> CLITool:
        """
        Analyze a CLI tool and extract its commands, options, and arguments with LLM enhancement.

        Args:
            tool_name: The name of the CLI tool to analyze.
            version: Optional specific version of the tool to analyze.

        Returns:
            A CLITool object with all extracted information.

        Raises:
            CommandExecutionError: If the tool cannot be executed.
            ValidationError: If the tool information cannot be validated.
        """
        # First analyze with standard analyzer
        cli_tool = self.standard_analyzer.analyze_cli_tool(tool_name, version)

        try:
            # Enhance tool description with LLM
            if cli_tool.help_text:
                cli_tool.description = self._enhance_description_with_llm(
                    cli_tool.description, cli_tool.help_text
                )

            # If we don't have any commands detected but we have help text,
            # try to extract commands using LLM
            if not cli_tool.commands and cli_tool.help_text:
                self._extract_commands_with_llm(cli_tool)

            return cli_tool
        except Exception as e:
            logger.error(f"Failed to enhance CLI tool analysis with LLM: {str(e)}")
            return cli_tool

    def _extract_commands_with_llm(self, cli_tool: CLITool) -> None:
        """
        Extract commands using the LLM when standard extraction fails.

        Args:
            cli_tool: The CLI tool to extract commands for.
        """
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the command"},
                    "description": {
                        "type": "string",
                        "description": "Brief description of what the command does",
                    },
                },
                "required": ["name"],
            },
        }

        prompt = f"""
        Based on the following help text for the CLI tool '{cli_tool.name}',
        extract all available commands (or subcommands). Focus on identifying distinct commands
        that users can execute.

        Help text:
        ```
        {cli_tool.help_text[:3000] if cli_tool.help_text else "No help text available"}
        ```
        """

        try:
            commands_data = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Extracted {len(commands_data)} commands with LLM")

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

        except LLMServiceError as e:
            logger.warning(f"Failed to extract commands with LLM: {str(e)}")
