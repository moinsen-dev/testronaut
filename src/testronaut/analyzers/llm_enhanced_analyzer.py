"""
LLM-Enhanced CLI Analyzer Implementation.

This module provides an implementation of the CLI analyzer interface that uses
LLM capabilities to enhance the analysis of CLI tools.
"""

import time
from typing import Any, Dict, List, Optional, cast

from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.interfaces import CLIAnalyzer
from testronaut.models import Argument, CLITool, Command, Example, Option
from testronaut.models.cli_tool import (
    add_relationship_analysis,
)
from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import CommandExecutionError, LLMServiceError, ValidationError
from testronaut.utils.llm import LLMService
from testronaut.utils.llm.prompts import CLIAnalysisPrompts
from testronaut.utils.llm.result_processor import LLMResultProcessor
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
        self.result_processor = LLMResultProcessor()

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

    def get_command_help_text(
        self, tool_name: str, command_name: str, parent_path: str = ""
    ) -> str:
        """
        Get the help text for a specific command of a CLI tool.
        Enhanced version that uses LLM as fallback when conventional methods fail.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            parent_path: The parent command path (if this is a subcommand).

        Returns:
            The help text as a string.

        Raises:
            CommandExecutionError: If the help command cannot be executed.
        """
        try:
            # First try standard method
            return self.standard_analyzer.get_command_help_text(
                tool_name, command_name, parent_path
            )
        except CommandExecutionError as e:
            logger.warning(
                f"Standard help text retrieval failed for {command_name}. Trying LLM fallback."
            )
            # If standard method fails, try to use LLM to generate synthetic help text
            return self._generate_command_help_with_llm(
                tool_name, command_name, parent_path, str(e)
            )

    def _generate_command_help_with_llm(
        self, tool_name: str, command_name: str, parent_path: str, error_message: str
    ) -> str:
        """
        Generate synthetic help text for a command using LLM when conventional methods fail.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            parent_path: The parent command path (if this is a subcommand).
            error_message: The error message from the conventional method.

        Returns:
            Synthetic help text as a string.

        Raises:
            CommandExecutionError: If the LLM generation fails.
        """
        # Build the full command path
        if parent_path:
            full_cmd = f"{tool_name} {parent_path} {command_name}"
        else:
            full_cmd = f"{tool_name} {command_name}"

        # Get tool help text to provide context
        try:
            tool_help = self.standard_analyzer.get_tool_help_text(tool_name)
        except CommandExecutionError:
            tool_help = f"CLI tool {tool_name} with command {command_name}"

        # Use the specialized prompt for command structure inference
        prompt = CLIAnalysisPrompts.command_structure_inference(
            tool_name=full_cmd if not parent_path else tool_name,
            command_name="" if not parent_path else command_name,
            tool_help_text=tool_help,
            error_context=error_message,
        )

        try:
            # Generate synthetic help text
            synthetic_help = self.llm_service.generate_text(prompt)
            logger.info(f"Generated synthetic help text for {full_cmd} using LLM")
            return synthetic_help
        except LLMServiceError as e:
            logger.error(f"LLM generation failed for {full_cmd}: {str(e)}")
            raise CommandExecutionError(
                f"Failed to get help text for command {full_cmd} (LLM fallback failed)",
                details={"error": str(e), "original_error": error_message},
            )

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
            # Create a prompt using our prompt template
            prompt = CLIAnalysisPrompts.command_purpose_analysis("unknown", help_text, description)

            try:
                response = self.llm_service.generate_text(prompt)
                processed_description = self.result_processor.process_command_purpose(response)
                return processed_description
            except (LLMServiceError, ValidationError) as e:
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
        # Use the examples prompt template
        prompt = CLIAnalysisPrompts.command_examples_extraction(
            tool_name, command_name, help_text, num_examples=3
        )

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

        try:
            # Try to get structured JSON examples
            examples = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Generated {len(examples)} examples with LLM (structured)")
            return cast(List[Dict[str, Any]], examples)
        except LLMServiceError:
            # Fall back to text generation and processing
            try:
                response = self.llm_service.generate_text(prompt)
                examples = self.result_processor.process_examples(response)
                logger.debug(f"Generated {len(examples)} examples with LLM (text)")
                return examples
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to extract examples with LLM: {str(e)}")
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
                help_text = command.help_text or self.get_command_help_text(
                    tool_name,
                    command_name,
                    parent_path=command.parent_command.name if command.parent_command else "",
                )

                llm_examples = self._extract_examples_with_llm(tool_name, command_name, help_text)

                # Merge examples, avoiding duplicates
                existing_cmd_lines = {ex.get("command_line") for ex in examples}
                for ex in llm_examples:
                    if ex.get("command_line") not in existing_cmd_lines:
                        examples.append(ex)
                        existing_cmd_lines.add(ex.get("command_line"))

            except (CommandExecutionError, LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to enhance examples with LLM: {str(e)}")

        return examples

    def _analyze_command_semantics(self, command: Command) -> Dict[str, Any]:
        """
        Perform semantic analysis of a command using LLM.

        Args:
            command: The command to analyze.

        Returns:
            Dictionary with semantic analysis information.
        """
        if not command.help_text or not command.cli_tool:
            return {}

        # Use the semantic analysis prompt template
        prompt = CLIAnalysisPrompts.command_semantic_analysis(
            command.cli_tool.name, command.name, command.help_text
        )

        schema = {
            "type": "object",
            "properties": {
                "primary_function": {
                    "type": "string",
                    "description": "The main purpose of the command",
                },
                "common_use_cases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Scenarios where this command would be used",
                },
                "key_options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "importance": {"type": "string"},
                        },
                    },
                    "description": "Most important options for this command",
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "unknown"],
                    "description": "How potentially destructive this command is",
                },
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative commands or approaches",
                },
                "common_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Common usage patterns for this command",
                },
            },
            "required": ["primary_function", "risk_level"],
        }

        try:
            # Try to get structured JSON analysis
            analysis = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Generated semantic analysis for command: {command.name}")
            return cast(Dict[str, Any], analysis)
        except LLMServiceError:
            # Fall back to text generation and processing
            try:
                response = self.llm_service.generate_text(prompt)
                analysis = self.result_processor.process_semantic_analysis(response)
                return analysis
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze command semantics: {str(e)}")
                return {}

    def _analyze_command_relationships(self, cli_tool: CLITool) -> Dict[str, Any]:
        """
        Analyze relationships between commands using LLM.

        Args:
            cli_tool: The CLI tool containing commands.

        Returns:
            Dictionary with relationship information.
        """
        if not cli_tool.commands:
            return {"parent_child": [], "workflows": [], "dependencies": []}

        # Prepare command data for the prompt
        commands = [
            {"name": cmd.name, "description": cmd.description or "No description"}
            for cmd in cli_tool.commands
        ]

        # Use the relationships analysis prompt template
        prompt = CLIAnalysisPrompts.command_relationships_analysis(cli_tool.name, commands)

        schema = {
            "type": "object",
            "properties": {
                "parent_child": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"parent": {"type": "string"}, "child": {"type": "string"}},
                        "required": ["parent", "child"],
                    },
                },
                "workflows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "steps": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "steps"],
                    },
                },
                "dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "depends_on": {"type": "string"},
                        },
                        "required": ["command", "depends_on"],
                    },
                },
            },
        }

        try:
            # Try to get structured JSON relationships
            relationships = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Generated relationship analysis for tool: {cli_tool.name}")
            return cast(Dict[str, Any], relationships)
        except LLMServiceError:
            # Fall back to text generation and processing
            try:
                response = self.llm_service.generate_text(prompt)
                relationships = self.result_processor.process_relationships(response)
                return relationships
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze command relationships: {str(e)}")
                return {"parent_child": [], "workflows": [], "dependencies": []}

    def update_command_info(self, command: Command) -> Command:
        """
        Update and enrich the information for a specific command, enhanced with LLM.

        Args:
            command: The command object to update.

        Returns:
            The updated command object with enriched information.

        Raises:
            CommandExecutionError: If the command cannot be executed.
            ValidationError: If the command information cannot be validated.
        """
        # First try standard updater
        try:
            return self.standard_analyzer.update_command_info(command)
        except CommandExecutionError as e:
            logger.warning(
                f"Standard command info update failed for {command.name}. Using LLM enhancement."
            )

            # Get tool help text for context
            try:
                tool_help = self.standard_analyzer.get_tool_help_text(command.cli_tool.name)
            except CommandExecutionError:
                tool_help = f"CLI tool {command.cli_tool.name}"

            # Build parent path for generating help with LLM
            command_path_parts = []
            current_command = command

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

            # Generate synthetic help text using LLM
            try:
                help_text = self._generate_command_help_with_llm(
                    command.cli_tool.name, command.name, command_path, str(e)
                )
                command.help_text = help_text

                # Extract command information using LLM
                command_info = self._extract_command_structure_with_llm(
                    command.cli_tool.name, command.name, help_text
                )

                # Update command description
                if command_info.get("description"):
                    command.description = command_info["description"]
                else:
                    # Fall back to enhancing any existing description
                    command.description = self._enhance_description_with_llm(
                        command.description, help_text
                    )

                # Add options
                for option_data in command_info.get("options", []):
                    option = Option(
                        command_id=command.id,
                        name=option_data.get("name", ""),
                        short_form=option_data.get("short_form"),
                        long_form=option_data.get("long_form"),
                        description=option_data.get("description", ""),
                        required=option_data.get("required", False),
                    )
                    command.options.append(option)

                # Add arguments
                for arg_data in command_info.get("arguments", []):
                    argument = Argument(
                        command_id=command.id,
                        name=arg_data.get("name", ""),
                        description=arg_data.get("description", ""),
                        required=arg_data.get("required", False),
                    )
                    command.arguments.append(argument)

                # Add examples
                for example_data in command_info.get("examples", []):
                    example = Example(
                        command_id=command.id,
                        command_line=example_data.get("command_line", ""),
                        description=example_data.get("description"),
                    )
                    command.examples.append(example)

                # Process subcommands if they exist
                for subcmd_data in command_info.get("subcommands", []):
                    subcmd_name = subcmd_data.get("name", "")
                    if not subcmd_name:
                        continue

                    # Check if this subcommand already exists
                    existing_subcmd = None
                    for cmd in command.cli_tool.commands:
                        if (
                            hasattr(cmd, "name")
                            and getattr(cmd, "name", "").lower() == subcmd_name.lower()
                            and hasattr(cmd, "parent_command_id")
                            and getattr(cmd, "parent_command_id", None) == command.id
                        ):
                            existing_subcmd = cmd
                            break

                    if not existing_subcmd:
                        # Create new subcommand
                        subcommand = Command(
                            cli_tool_id=command.cli_tool.id,
                            name=subcmd_name,
                            description=subcmd_data.get("description", ""),
                            parent_command_id=command.id,
                            is_subcommand=True,
                        )
                        command.cli_tool.commands.append(subcommand)

                return command

            except CommandExecutionError as llm_error:
                logger.error(
                    f"LLM-enhanced command info update failed for {command.name}: {str(llm_error)}"
                )
                raise CommandExecutionError(
                    f"Failed to update command {command.name}",
                    details={"error": str(llm_error), "original_error": str(e)},
                )

    def _analyze_tool_purpose(self, cli_tool: CLITool) -> Dict[str, Any]:
        """
        Analyze the overall purpose of a CLI tool using LLM.

        Args:
            cli_tool: The CLI tool to analyze.

        Returns:
            Dictionary with purpose analysis information.
        """
        if not cli_tool.help_text:
            return {}

        prompt = CLIAnalysisPrompts.tool_purpose_analysis(cli_tool.name, cli_tool.help_text)

        schema = {
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "description": "The main purpose of the tool",
                },
                "background": {
                    "type": "string",
                    "description": "Technical context for understanding the tool",
                },
                "use_cases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Common use cases for the tool",
                },
                "testing_considerations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Special considerations for testing",
                },
            },
            "required": ["purpose"],
        }

        try:
            # Try to get structured JSON analysis
            analysis = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Generated purpose analysis for tool: {cli_tool.name}")
            return cast(Dict[str, Any], analysis)
        except LLMServiceError:
            # Fall back to text generation and processing
            try:
                response = self.llm_service.generate_text(prompt)
                analysis = self.result_processor.process_tool_purpose_analysis(response)
                return analysis
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze tool purpose: {str(e)}")
                return {}

    def _analyze_subcommand_purpose(self, command: Command) -> str:
        """
        Analyze the purpose of a specific subcommand using LLM.

        Args:
            command: The command to analyze.

        Returns:
            String with the command's purpose.
        """
        if not command.help_text or not command.cli_tool:
            return ""

        prompt = CLIAnalysisPrompts.subcommand_purpose_analysis(
            command.cli_tool.name, command.name, command.help_text
        )

        schema = {
            "type": "object",
            "properties": {
                "purpose": {
                    "type": "string",
                    "description": "The specific purpose of this command",
                },
            },
            "required": ["purpose"],
        }

        try:
            analysis = self.llm_service.generate_json(prompt, schema)
            logger.debug(f"Generated purpose analysis for command: {command.name}")
            return cast(Dict[str, Any], analysis).get("purpose", "")
        except LLMServiceError:
            # Fall back to text generation
            try:
                response = self.llm_service.generate_text(prompt)
                # Extract purpose from text response
                return self.result_processor.extract_purpose(response)
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze command purpose: {str(e)}")
                return ""

    def _verify_and_complete_command(self, command: Command) -> None:
        """
        Verify that a command has complete information and use LLM to fill gaps.

        Args:
            command: The command to verify and complete.
        """
        # Check if options are missing but likely needed
        if not command.options and "option" in (command.help_text or "").lower():
            logger.info(f"Generating missing options for command: {command.name}")
            try:
                cmd_data = self._extract_command_structure_with_llm(
                    command.cli_tool.name, command.name, command.help_text or ""
                )
                if "options" in cmd_data and isinstance(cmd_data["options"], list):
                    for opt_data in cmd_data["options"]:
                        option = Option(
                            command_id=command.id,
                            name=opt_data.get("name", ""),
                            description=opt_data.get("description"),
                            short_form=opt_data.get("short_form"),
                            long_form=opt_data.get("long_form"),
                            required=opt_data.get("required", False),
                        )
                        command.options.append(option)
            except Exception as e:
                logger.warning(f"Failed to generate options for {command.name}: {str(e)}")

        # Check if arguments are missing but likely needed
        if not command.arguments and "argument" in (command.help_text or "").lower():
            logger.info(f"Generating missing arguments for command: {command.name}")
            try:
                cmd_data = self._extract_command_structure_with_llm(
                    command.cli_tool.name, command.name, command.help_text or ""
                )
                if "arguments" in cmd_data and isinstance(cmd_data["arguments"], list):
                    for i, arg_data in enumerate(cmd_data["arguments"]):
                        argument = Argument(
                            command_id=command.id,
                            name=arg_data.get("name", ""),
                            description=arg_data.get("description"),
                            required=arg_data.get("required", False),
                            position=i,
                        )
                        command.arguments.append(argument)
            except Exception as e:
                logger.warning(f"Failed to generate arguments for {command.name}: {str(e)}")

        # Check if examples are missing
        if not command.examples:
            logger.info(f"Generating examples for command: {command.name}")
            try:
                examples = self.extract_examples(command)
                if examples:
                    for example in examples:
                        cmd_line = example.get("command_line", "")
                        desc = example.get("description", "")
                        if cmd_line:
                            command.examples.append(
                                Example(
                                    command_id=command.id, command_line=cmd_line, description=desc
                                )
                            )
            except Exception as e:
                logger.warning(f"Failed to generate examples for {command.name}: {str(e)}")

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
        logger.info(f"Starting LLM-enhanced analysis of CLI tool: {tool_name}")
        logger.info("Phase 1/4: Running standard analysis...")

        # First analyze with standard analyzer
        start_time = time.time()
        cli_tool = self.standard_analyzer.analyze_cli_tool(tool_name, version)
        standard_time = time.time() - start_time
        logger.info(f"Standard analysis completed in {standard_time:.2f} seconds")

        try:
            logger.info("Phase 2/4: Enhancing analysis with LLM...")

            # Enhance tool description with LLM
            if cli_tool.help_text:
                logger.info("Enhancing tool description using LLM...")
                start_time = time.time()
                cli_tool.description = self._enhance_description_with_llm(
                    cli_tool.description, cli_tool.help_text
                )
                logger.info(
                    f"Description enhancement completed in {time.time() - start_time:.2f} seconds"
                )

            # NEW: Analyze tool purpose and background
            logger.info("Analyzing tool purpose and background...")
            start_time = time.time()
            purpose_analysis = self._analyze_tool_purpose(cli_tool)
            cli_tool.purpose = purpose_analysis.get("purpose", "")
            cli_tool.background = purpose_analysis.get("background", "")
            cli_tool.use_cases = purpose_analysis.get("use_cases", [])
            cli_tool.testing_considerations = purpose_analysis.get("testing_considerations", [])
            logger.info(
                f"Tool purpose analysis completed in {time.time() - start_time:.2f} seconds"
            )

            # If we don't have any commands detected but we have help text,
            # try to extract commands using LLM
            if not cli_tool.commands and cli_tool.help_text:
                logger.info("No commands detected. Attempting to extract commands using LLM...")
                start_time = time.time()
                self._extract_commands_with_llm(cli_tool)
                logger.info(
                    f"Command extraction completed in {time.time() - start_time:.2f} seconds"
                )

            # NEW: Phase 3/4: Enhance commands with purposes and missing details
            if cli_tool.commands:
                logger.info("Phase 3/4: Enhancing commands with purposes and details...")
                start_time = time.time()
                for command in cli_tool.commands:
                    logger.info(f"Analyzing purpose for command: {command.name}")
                    command.purpose = self._analyze_subcommand_purpose(command)

                    # Verify and complete command details
                    self._verify_and_complete_command(command)

                logger.info(
                    f"Command enhancement completed in {time.time() - start_time:.2f} seconds"
                )

            # Analyze command relationships and add as metadata
            if cli_tool.commands:
                logger.info("Phase 4/4: Analyzing command relationships...")
                start_time = time.time()
                relationships = self._analyze_command_relationships(cli_tool)
                if relationships:
                    # Use the helper function to add relationship analysis
                    add_relationship_analysis(cli_tool, relationships)

                    # Apply relationship insights to the command structure
                    self._apply_relationship_insights(cli_tool, relationships)
                logger.info(
                    f"Relationship analysis completed in {time.time() - start_time:.2f} seconds"
                )

            logger.info("LLM-enhanced analysis complete!")
            return cli_tool
        except Exception as e:
            logger.error(f"Failed to enhance CLI tool analysis with LLM: {str(e)}")
            logger.info("Returning results from standard analysis")
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
                if isinstance(cmd_data, dict):
                    command = Command(
                        cli_tool_id=cli_tool.id,
                        name=cmd_data.get("name", ""),
                        description=cmd_data.get("description"),
                    )
                    cli_tool.commands.append(command)

            # Update each command with more detailed information
            for command in cli_tool.commands:
                self.update_command_info(command)

        except (LLMServiceError, ValidationError) as e:
            logger.warning(f"Failed to extract commands with LLM: {str(e)}")

    def _apply_relationship_insights(
        self, cli_tool: CLITool, relationships: Dict[str, Any]
    ) -> None:
        """
        Apply relationship insights to the command structure.

        Args:
            cli_tool: The CLI tool to update.
            relationships: The relationship information from LLM analysis.
        """
        # Create a dictionary of commands by name for easy lookup
        commands_by_name = {cmd.name: cmd for cmd in cli_tool.commands}

        # Apply parent-child relationships
        for relation in relationships.get("parent_child", []):
            if not isinstance(relation, dict):
                continue

            parent_name = relation.get("parent")
            child_name = relation.get("child")

            # Skip if names are missing or invalid
            if not parent_name or not child_name:
                continue

            # Skip if commands don't exist
            if parent_name not in commands_by_name or child_name not in commands_by_name:
                continue

            parent_cmd = commands_by_name[parent_name]
            child_cmd = commands_by_name[child_name]

            # Update subcommand relationship if it doesn't already exist
            if not child_cmd.is_subcommand and not child_cmd.parent_command_id:
                child_cmd.is_subcommand = True
                child_cmd.parent_command_id = parent_cmd.id

                # Add to parent's subcommands list if using an ORM
                if not any(subcmd.id == child_cmd.id for subcmd in parent_cmd.subcommands):
                    parent_cmd.subcommands.append(child_cmd)

    def _extract_command_structure_with_llm(
        self, tool_name: str, command_name: str, help_text: str
    ) -> Dict[str, Any]:
        """
        Extract command structure and information using LLM when regex patterns might fail.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            help_text: The help text to analyze.

        Returns:
            Dictionary with command structure information.
        """
        import time

        logger.info(f"Extracting command structure for '{command_name}' using LLM...")
        start_time = time.time()

        # Build prompt for LLM
        logger.debug("Building prompt for LLM command structure extraction...")
        prompt = f"""
        Analyze the following help text for the command '{tool_name} {command_name}' and extract its structure.

        Extract the following information:
        1. Description: What the command does
        2. Options: All command-line options with their descriptions and whether they're required
        3. Arguments: All positional arguments with their descriptions and whether they're required
        4. Examples: Any usage examples shown
        5. Subcommands: Any subcommands mentioned with their descriptions

        Help text:
        ```
        {help_text[:3000]}  # Limiting to 3000 chars to avoid token limits
        ```

        Format your response as a structured JSON object.
        """

        # Define schema for the LLM response
        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "short_form": {"type": "string", "nullable": True},
                            "long_form": {"type": "string", "nullable": True},
                            "description": {"type": "string"},
                            "required": {"type": "boolean"},
                            "takes_value": {"type": "boolean"},
                        },
                        "required": ["name", "description"],
                    },
                },
                "arguments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "required": {"type": "boolean"},
                        },
                        "required": ["name"],
                    },
                },
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "command_line": {"type": "string"},
                            "description": {"type": "string", "nullable": True},
                        },
                        "required": ["command_line"],
                    },
                },
                "subcommands": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string", "nullable": True},
                        },
                        "required": ["name"],
                    },
                },
            },
            "required": ["description"],
        }

        try:
            # Generate structured JSON analysis
            logger.debug("Calling LLM service for structured command extraction...")
            result = self.llm_service.generate_json(prompt, schema)
            elapsed_time = time.time() - start_time
            logger.info(
                f"Extracted command structure for '{command_name}' in {elapsed_time:.2f} seconds"
            )

            # Log summary of extracted information
            options_count = len(result.get("options", []))
            args_count = len(result.get("arguments", []))
            examples_count = len(result.get("examples", []))
            subcommands_count = len(result.get("subcommands", []))
            logger.info(
                f"Extracted: {options_count} options, {args_count} arguments, "
                + f"{examples_count} examples, {subcommands_count} subcommands"
            )

            return result
        except LLMServiceError:
            # Fall back to text generation and parsing
            logger.warning("Structured JSON generation failed, falling back to text extraction...")
            try:
                response = self.llm_service.generate_text(prompt)
                result = self.result_processor.extract_json_from_text(response)
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Extracted command structure using text parsing in {elapsed_time:.2f} seconds"
                )
                return result
            except (LLMServiceError, ValidationError) as e:
                elapsed_time = time.time() - start_time
                logger.warning(
                    f"Failed to extract command structure with LLM after {elapsed_time:.2f} seconds: {str(e)}"
                )
                return {}
