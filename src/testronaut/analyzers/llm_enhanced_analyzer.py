"""
LLM-Enhanced CLI Analyzer Implementation.

This module provides an implementation of the CLI analyzer interface that uses
LLM capabilities to enhance the analysis of CLI tools. It delegates specific
LLM interaction tasks to the LLMAnalysisHelper class.
"""

import re
import time
from typing import Any, Dict, List, Optional, cast, Union # Import Union

from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.interfaces import CLIAnalyzer
from testronaut.models import Argument, CLITool, Command, Example, Option
from testronaut.models.cli_tool import (
    TokenUsage,
    add_relationship_analysis,
    MetaData, # Import MetaData
)
from testronaut.utils.command import CommandRunner
from testronaut.utils.errors import CommandExecutionError, LLMServiceError, ValidationError
from testronaut.utils.llm import LLMService
# Prompts might not be needed directly here anymore if helper handles all prompt selection
# from testronaut.utils.llm.prompts import CLIAnalysisPrompts
from testronaut.utils.llm.result_processor import LLMResultProcessor
from testronaut.utils.logging import get_logger

# Import the new helper class
from .llm_helper import LLMAnalysisHelper

# Initialize logger
logger = get_logger(__name__)


class LLMEnhancedAnalyzer(CLIAnalyzer):
    """
    LLM-enhanced implementation of CLI tool analyzer.

    Orchestrates the analysis process, combining standard analysis techniques
    with LLM enhancements provided by LLMAnalysisHelper.
    """

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
        self.llm_service = llm_service or LLMService() # Keep LLMService instance
        self.result_processor = LLMResultProcessor() # Keep ResultProcessor instance
        # Instantiate the helper, passing dependencies
        self.llm_helper = LLMAnalysisHelper(self.llm_service, self.result_processor)
        self.token_usage = TokenUsage() # Keep token usage tracking here

    def _track_llm_usage(self) -> None:
        """
        Track token usage from the LLM service after an API call made via the helper.
        Assumes the LLMService instance updates its `last_token_usage` attribute.
        """
        llm_service = self.llm_service # Use the instance variable
        if hasattr(llm_service, "last_token_usage") and llm_service.last_token_usage:
            usage = llm_service.last_token_usage
            model = usage.get("model", self.llm_service.settings.llm.model) # Get model used
            self.token_usage.add_usage(
                total_tokens=usage.get("total_tokens", 0),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                model=model,
            )
            logger.debug(
                f"LLM token usage: +{usage.get('total_tokens', 0)} tokens, "
                f"model: {model or 'unknown'}, totals: {self.token_usage.total_tokens} tokens, "
                f"{self.token_usage.api_calls} calls, est. cost: ${self.token_usage.estimated_cost:.4f}"
            )
            # Reset last usage on service to prevent double counting
            llm_service.last_token_usage = None

    # --- Public Interface Methods ---

    def verify_tool_installation(self, tool_name: str) -> bool:
        """Delegates to standard analyzer."""
        return self.standard_analyzer.verify_tool_installation(tool_name)

    def get_tool_help_text(self, tool_name: str) -> str:
        """Delegates to standard analyzer."""
        return self.standard_analyzer.get_tool_help_text(tool_name)

    def get_command_help_text(
        self, tool_name: str, command_name: str, parent_path: str = ""
    ) -> str:
        """
        Get command help text, using LLM fallback if standard method fails.
        """
        try:
            return self.standard_analyzer.get_command_help_text(
                tool_name, command_name, parent_path
            )
        except CommandExecutionError as e:
            logger.warning(
                f"Standard help text retrieval failed for '{command_name}'. Trying LLM fallback."
            )
            try:
                # Get tool help for context, handle potential error
                tool_help = self.standard_analyzer.get_tool_help_text(tool_name)
            except CommandExecutionError:
                tool_help = f"Context for CLI tool '{tool_name}' with command '{command_name}'"

            # Call the helper method
            try:
                 synthetic_help = self.llm_helper.generate_command_help_with_llm(
                    tool_name, command_name, parent_path, str(e), tool_help
                 )
                 self._track_llm_usage() # Track usage after successful helper call
                 return synthetic_help
            except CommandExecutionError: # Catch error from helper
                 raise # Re-raise the specific error from the helper
            except Exception as llm_e: # Catch unexpected errors
                 logger.error(f"Unexpected error during LLM help generation fallback: {llm_e}", exc_info=True)
                 raise CommandExecutionError(
                    f"Failed to get help text for command {command_name} (LLM fallback failed unexpectedly)",
                    details={"error": str(llm_e), "original_error": str(e)},
                 ) from llm_e

    def extract_examples(self, command: Command) -> List[Dict[str, Any]]:
        """
        Extract usage examples, combining standard and LLM methods.
        """
        # First try the standard method
        examples = self.standard_analyzer.extract_examples(command)

        # If we got no examples or just a few, try with LLM
        if len(examples) < 2:
            try:
                # Safely get tool name, command name, and help text
                cli_tool_name = getattr(getattr(command, "cli_tool", None), "name", "unknown_tool")
                command_name = getattr(command, "name", "unknown_command")
                help_text = getattr(command, "help_text", "")

                if not help_text:
                     logger.warning(f"No help text available for command '{command_name}', cannot extract examples with LLM.")
                     return examples # Return standard examples if no help text

                # Call the helper method
                llm_examples = self.llm_helper.extract_examples_with_llm(
                    cli_tool_name, command_name, help_text
                )
                self._track_llm_usage() # Track usage

                # Merge examples, avoiding duplicates
                existing_cmd_lines = {ex.get("command_line", "") for ex in examples}
                for ex_data in llm_examples: # ex_data is Dict[str, str] from helper
                    cmd_line = ex_data.get("command_line")
                    if cmd_line and cmd_line not in existing_cmd_lines:
                        # Ensure structure matches expected List[Dict[str, Any]]
                        examples.append({
                            "command_line": cmd_line,
                            "description": ex_data.get("description", "")
                        })
                        existing_cmd_lines.add(cmd_line)

            except Exception as e:
                logger.error(
                    f"Failed during LLM example generation/extraction for '{getattr(command, 'name', 'unknown')}': {str(e)}",
                    exc_info=True
                )

        return examples # Return combined list

    def update_command_info(self, command: Command) -> Command:
        """
        Update and enrich command info using standard and LLM methods.
        """
        logger.debug(f"Updating command info for {command.name}")

        try:
            # 1. Run standard update first
            self.standard_analyzer.update_command_info(command)

            # 2. Ensure help text exists (using standard or LLM generation if needed)
            self._ensure_command_help_text(command)

            # 3. Enhance description if needed
            if command.help_text and (not command.description or len(command.description) < 20):
                try:
                    command.description = self.llm_helper.enhance_description_with_llm(
                        command.description, command.help_text, command.name
                    )
                    self._track_llm_usage()
                except Exception as e:
                    logger.warning(f"Failed to enhance description for '{command.name}' with LLM: {str(e)}")

            # 4. Extract options/args/examples/subcommands if missing, using LLM
            if command.help_text and (not command.options or not command.arguments):
                 logger.info(f"Attempting to extract structure for '{command.name}' using LLM as standard parsing might be incomplete.")
                 self._extract_structure_llm(command) # Calls helper internally

            # 5. Extract examples if missing
            if not command.examples:
                 logger.info(f"Attempting to extract examples for '{command.name}' using standard and LLM methods.")
                 examples_data = self.extract_examples(command) # Uses combined logic
                 # Add examples if new ones were found
                 existing_examples = {ex.command_line for ex in command.examples}
                 for ex_data in examples_data:
                     cmd_line = ex_data.get("command_line")
                     if cmd_line and cmd_line not in existing_examples:
                         command.examples.append(Example(
                             command_id=command.id,
                             command_line=cmd_line,
                             description=ex_data.get("description", "")
                         ))
                         existing_examples.add(cmd_line)

            # 6. Analyze purpose (moved from main analyze method)
            if command.help_text and not command.purpose:
                 try:
                     logger.info(f"Analyzing purpose for command: {command.name}")
                     command.purpose = self.llm_helper.analyze_subcommand_purpose(
                         command.cli_tool.name, command.name, command.help_text
                     )
                     self._track_llm_usage()
                 except Exception as e:
                     logger.warning(f"Failed to analyze purpose for command '{command.name}': {str(e)}")


            return command
        except Exception as e:
            logger.error(f"Failed during update_command_info for '{command.name}': {str(e)}", exc_info=True)
            # Metadata is not tracked per command, so no need to check/add it here.
            # Optionally, we could add an error flag or note to the command object itself if needed.
            return command # Return original command on error

    # --- Refactored Analysis Orchestration ---

    def _run_standard_analysis(
        self, tool_name: str, version: Optional[str], max_commands: Optional[int]
    ) -> CLITool:
        """Runs the standard analysis phase."""
        logger.info("Phase 1/4: Running standard analysis...")
        start_time = time.time()
        try:
            cli_tool = self.standard_analyzer.analyze_cli_tool(
                tool_name, version, max_commands=max_commands
            )
        except Exception as e:
            logger.error(f"Standard analysis failed for tool '{tool_name}': {e}", exc_info=True)
            cli_tool = CLITool(name=tool_name, version=version or "unknown")
            try:
                cli_tool.help_text = self.get_tool_help_text(tool_name)
            except Exception:
                logger.error(f"Could not retrieve basic help text for '{tool_name}'. Analysis severely limited.")
                cli_tool.help_text = f"Error retrieving help for {tool_name}"
        logger.info(f"Standard analysis phase completed in {time.time() - start_time:.2f} seconds")
        return cli_tool

    def _enhance_tool_with_llm(self, cli_tool: CLITool) -> None:
        """Enhances the top-level tool information using LLM."""
        logger.info("Phase 2/4: Enhancing tool analysis with LLM...")
        start_enhance_time = time.time()

        # Enhance tool description
        if cli_tool.help_text and (not cli_tool.description or len(cli_tool.description) < 10):
            logger.info("Enhancing tool description...")
            try:
                cli_tool.description = self.llm_helper.enhance_description_with_llm(
                    cli_tool.description, cli_tool.help_text, cli_tool.name
                )
                self._track_llm_usage()
            except Exception as e:
                logger.warning(f"Failed to enhance tool description: {e}")

        # Analyze tool purpose and background
        if cli_tool.help_text:
            logger.info("Analyzing tool purpose and background...")
            try:
                purpose_analysis = self.llm_helper.analyze_tool_purpose(cli_tool.name, cli_tool.help_text)
                self._track_llm_usage()
                cli_tool.purpose = purpose_analysis.get("purpose", cli_tool.purpose or "")
                cli_tool.background = purpose_analysis.get("background", cli_tool.background or "")
                cli_tool.use_cases = purpose_analysis.get("use_cases", cli_tool.use_cases or [])
                cli_tool.testing_considerations = purpose_analysis.get("testing_considerations", cli_tool.testing_considerations or [])
            except Exception as e:
                logger.warning(f"Failed to analyze tool purpose: {e}")

        # Extract commands if standard analysis failed to find any
        if not cli_tool.commands and cli_tool.help_text:
            logger.info("No commands found by standard analysis. Attempting LLM extraction...")
            self._extract_commands_with_llm(cli_tool) # Calls helper internally

        logger.info(f"Tool enhancement completed in {time.time() - start_enhance_time:.2f} seconds")

    def _enhance_commands_with_llm(self, cli_tool: CLITool) -> None:
        """Enhances individual commands using LLM."""
        if not cli_tool.commands:
            logger.info("Phase 3/4: No commands found to enhance.")
            return

        logger.info("Phase 3/4: Enhancing individual commands...")
        start_cmd_enhance_time = time.time()
        enhancement_errors = 0
        num_commands_to_process = len(cli_tool.commands)
        for i, command in enumerate(cli_tool.commands):
            cmd_name = getattr(command, "name", f"command_{i+1}")
            logger.info(f"Enhancing command {i+1}/{num_commands_to_process}: {cmd_name}")
            try:
                # update_command_info handles ensuring help text, enhancing description,
                # extracting structure, and analyzing purpose.
                self.update_command_info(command)
            except Exception as e:
                # Error is logged within update_command_info
                enhancement_errors += 1

        if enhancement_errors > 0:
            logger.warning(f"Encountered {enhancement_errors} errors during command enhancement.")
        logger.info(f"Command enhancement completed in {time.time() - start_cmd_enhance_time:.2f} seconds")

    def _analyze_relationships_with_llm(self, cli_tool: CLITool) -> None:
        """Analyzes command relationships using LLM."""
        if not cli_tool.commands:
            logger.info("Phase 4/4: No commands found to analyze relationships.")
            return

        logger.info("Phase 4/4: Analyzing command relationships...")
        start_rel_time = time.time()
        try:
            command_data = [
                {"name": cmd.name, "description": cmd.description or ""}
                for cmd in cli_tool.commands if hasattr(cmd, 'name')
            ]
            if command_data:
                relationships = self.llm_helper.analyze_command_relationships(cli_tool.name, command_data)
                self._track_llm_usage()
                if relationships:
                    add_relationship_analysis(cli_tool, relationships)
                    self._apply_relationship_insights(cli_tool, relationships)
            else:
                 logger.warning("No valid command data to analyze relationships.")
        except Exception as e:
            logger.error(f"Failed to analyze command relationships: {str(e)}", exc_info=True)
        logger.info(f"Relationship analysis completed in {time.time() - start_rel_time:.2f} seconds")


    def analyze_cli_tool(
        self, tool_name: str, version: Optional[str] = None, max_commands: Optional[int] = None
    ) -> CLITool:
        """
        Analyze a CLI tool using standard methods and LLM enhancements.
        """
        logger.info(f"Starting LLM-enhanced analysis of CLI tool: {tool_name}")
        logger.info("Phase 1/4: Running standard analysis...")

        self.token_usage = TokenUsage() # Reset token tracking

        start_time = time.time()
        try:
            cli_tool = self.standard_analyzer.analyze_cli_tool(
                tool_name, version, max_commands=max_commands
            )
        except Exception as e:
             logger.error(f"Standard analysis failed for tool '{tool_name}': {e}", exc_info=True)
             # Create a minimal CLITool object to allow potential LLM recovery
             cli_tool = CLITool(name=tool_name, version=version or "unknown")
             try:
                 # Try to get at least the basic help text
                 cli_tool.help_text = self.get_tool_help_text(tool_name)
             except Exception:
                 logger.error(f"Could not retrieve even basic help text for '{tool_name}'. Analysis severely limited.")
                 cli_tool.help_text = f"Error retrieving help for {tool_name}"

        standard_time = time.time() - start_time
        logger.info(f"Standard analysis phase completed in {standard_time:.2f} seconds")

        # --- LLM Enhancement Phase ---
        try:
            logger.info("Phase 2/4: Enhancing tool analysis with LLM...")
            start_enhance_time = time.time()

            # Enhance tool description
            if cli_tool.help_text and (not cli_tool.description or len(cli_tool.description) < 10):
                logger.info("Enhancing tool description...")
                try:
                    cli_tool.description = self.llm_helper.enhance_description_with_llm(
                        cli_tool.description, cli_tool.help_text, tool_name
                    )
                    self._track_llm_usage()
                except Exception as e:
                    logger.warning(f"Failed to enhance tool description: {e}")

            # Analyze tool purpose and background
            if cli_tool.help_text:
                logger.info("Analyzing tool purpose and background...")
                try:
                    purpose_analysis = self.llm_helper.analyze_tool_purpose(cli_tool.name, cli_tool.help_text)
                    self._track_llm_usage()
                    cli_tool.purpose = purpose_analysis.get("purpose", cli_tool.purpose or "")
                    cli_tool.background = purpose_analysis.get("background", cli_tool.background or "")
                    cli_tool.use_cases = purpose_analysis.get("use_cases", cli_tool.use_cases or [])
                    cli_tool.testing_considerations = purpose_analysis.get("testing_considerations", cli_tool.testing_considerations or [])
                except Exception as e:
                    logger.warning(f"Failed to analyze tool purpose: {e}")

            # Extract commands if standard analysis failed to find any
            if not cli_tool.commands and cli_tool.help_text:
                logger.info("No commands found by standard analysis. Attempting LLM extraction...")
                self._extract_commands_with_llm(cli_tool) # Calls helper internally

            logger.info(f"Tool enhancement completed in {time.time() - start_enhance_time:.2f} seconds")

            # --- Command Enhancement Phase ---
            if cli_tool.commands:
                logger.info("Phase 3/4: Enhancing individual commands...")
                start_cmd_enhance_time = time.time()
                enhancement_errors = 0
                num_commands_to_process = len(cli_tool.commands)
                for i, command in enumerate(cli_tool.commands):
                    cmd_name = getattr(command, "name", f"command_{i+1}")
                    logger.info(f"Enhancing command {i+1}/{num_commands_to_process}: {cmd_name}")
                    try:
                        # update_command_info now handles ensuring help text,
                        # enhancing description, extracting structure, and analyzing purpose.
                        self.update_command_info(command)
                    except Exception as e:
                        logger.error(f"Error enhancing command {cmd_name}: {str(e)}", exc_info=True)
                        enhancement_errors += 1

                if enhancement_errors > 0:
                    logger.warning(f"Encountered {enhancement_errors} errors during command enhancement.")
                logger.info(f"Command enhancement completed in {time.time() - start_cmd_enhance_time:.2f} seconds")

            # --- Relationship Analysis Phase ---
            if cli_tool.commands:
                logger.info("Phase 4/4: Analyzing command relationships...")
                start_rel_time = time.time()
                try:
                    # Prepare command data for the helper
                    command_data = [
                        {"name": cmd.name, "description": cmd.description or ""}
                        for cmd in cli_tool.commands if hasattr(cmd, 'name')
                    ]
                    if command_data:
                        relationships = self.llm_helper.analyze_command_relationships(cli_tool.name, command_data)
                        self._track_llm_usage()
                        if relationships:
                            add_relationship_analysis(cli_tool, relationships)
                            self._apply_relationship_insights(cli_tool, relationships)
                    else:
                         logger.warning("No valid command data to analyze relationships.")
                except Exception as e:
                    logger.error(f"Failed to analyze command relationships: {str(e)}", exc_info=True)
                logger.info(f"Relationship analysis completed in {time.time() - start_rel_time:.2f} seconds")

            # --- Finalization ---
            logger.info(
                f"LLM-enhanced analysis complete! Used {self.token_usage.total_tokens} tokens in "
                f"{self.token_usage.api_calls} API calls (est. cost: ${self.token_usage.estimated_cost:.4f})"
            )

            # Add token usage to metadata
            if not hasattr(cli_tool, "meta_data") or cli_tool.meta_data is None:
                 cli_tool.meta_data = MetaData()
            cli_tool.meta_data.llm_usage = self.token_usage

            return cli_tool

        except Exception as e:
            logger.error(f"Unexpected error during LLM enhancement phase for '{tool_name}': {str(e)}", exc_info=True)
            logger.info("Returning potentially incomplete analysis results.")
            # Ensure metadata exists before assigning token usage
            if not hasattr(cli_tool, "meta_data") or cli_tool.meta_data is None:
                 cli_tool.meta_data = MetaData()
            cli_tool.meta_data.llm_usage = self.token_usage # Store usage even if enhancement failed
            return cli_tool # Return the cli_tool object even if enhancement failed partially

    # --- Internal Helper Methods ---

    def _ensure_command_help_text(self, command: Command) -> None:
        """Ensures command.help_text is populated, using standard or LLM methods."""
        if command.help_text:
            return

        logger.info(f"Help text missing for '{command.name}'. Attempting retrieval/generation.")
        try:
            tool_name = getattr(command.cli_tool, "name", "unknown_tool")
            # Determine parent path
            parent_path = ""
            if command.is_subcommand and command.parent_command_id:
                 # Find parent command within the tool's command list
                 parent_cmd = next((cmd for cmd in getattr(command.cli_tool, 'commands', []) if cmd.id == command.parent_command_id), None)
                 if parent_cmd:
                     parent_path = parent_cmd.name # Assuming simple hierarchy for now

            # Try standard method first (which itself has LLM fallback)
            command.help_text = self.get_command_help_text(tool_name, command.name, parent_path)
            logger.info(f"Successfully retrieved/generated help text for '{command.name}'.")

        except CommandExecutionError as e:
            # This means both standard and its LLM fallback failed
            logger.error(f"Failed to retrieve or generate help text for '{command.name}' even with fallback: {e}", exc_info=True)
            command.help_text = f"Help text retrieval/generation failed for {command.name}" # Placeholder
        except Exception as e:
             logger.error(f"Unexpected error ensuring help text for '{command.name}': {e}", exc_info=True)
             command.help_text = f"Error retrieving help text for {command.name}" # Placeholder


    def _extract_structure_llm(self, command: Command) -> None:
        """Extracts structure (options, args, etc.) using LLM helper."""
        if not command.help_text:
             logger.warning(f"Cannot extract structure for '{command.name}': No help text.")
             return

        try:
            tool_name = getattr(command.cli_tool, "name", "unknown_tool")
            structure_data = self.llm_helper.extract_structure_with_llm(
                tool_name, command.name, command.help_text
            )
            self._track_llm_usage()

            # Process extracted data (only add if not already present from standard analysis)
            if structure_data:
                # Update description if better
                llm_desc = structure_data.get("description")
                if llm_desc and (not command.description or len(command.description) < len(llm_desc)):
                    command.description = llm_desc

                # Add missing options
                existing_options = {opt.name for opt in command.options} # Use name for comparison
                if "options" in structure_data and isinstance(structure_data["options"], list):
                    for opt_data in structure_data["options"]:
                        if isinstance(opt_data, dict):
                            opt_name = opt_data.get("name")
                            if opt_name and opt_name not in existing_options:
                                command.options.append(Option(
                                    command_id=command.id,
                                    name=opt_name,
                                    short_form=opt_data.get("short_form"),
                                    long_form=opt_data.get("long_form"),
                                    description=opt_data.get("description"),
                                    required=opt_data.get("required", False),
                                    # takes_value=opt_data.get("takes_value") # Add if needed
                                ))
                                existing_options.add(opt_name)

                # Add missing arguments
                existing_args = {arg.name for arg in command.arguments}
                if "arguments" in structure_data and isinstance(structure_data["arguments"], list):
                     for i, arg_data in enumerate(structure_data["arguments"]):
                         if isinstance(arg_data, dict):
                             arg_name = arg_data.get("name")
                             if arg_name and arg_name not in existing_args:
                                 command.arguments.append(Argument(
                                     command_id=command.id,
                                     name=arg_name,
                                     description=arg_data.get("description"),
                                     required=arg_data.get("required", False),
                                     position=len(command.arguments) # Append at the end
                                 ))
                                 existing_args.add(arg_name)

                # Add missing examples (handled by update_command_info calling extract_examples)

                # Add missing subcommands
                if "subcommands" in structure_data and isinstance(structure_data["subcommands"], list):
                    self._process_llm_subcommands(command, structure_data["subcommands"])

        except Exception as e:
            logger.error(f"Failed during LLM structure extraction for '{command.name}': {e}", exc_info=True)


    def _extract_commands_with_llm(self, cli_tool: CLITool) -> None:
        """
        Extracts top-level commands using LLM helper when standard fails.
        """
        if not cli_tool.help_text:
             logger.warning(f"Cannot extract commands for '{cli_tool.name}': No help text.")
             return

        logger.info(f"Attempting to extract commands for '{cli_tool.name}' using LLM.")
        try:
            # Use the structure extraction focused on commands
            structure = self.llm_helper.extract_structure_with_llm(
                cli_tool.name, cli_tool.name, cli_tool.help_text # Use tool name as command for top level
            )
            self._track_llm_usage()

            if structure and "subcommands" in structure and isinstance(structure["subcommands"], list):
                 logger.info(f"LLM identified {len(structure['subcommands'])} potential commands.")
                 self._process_llm_subcommands(cli_tool, structure["subcommands"], is_top_level=True) # Process as top-level

                 # Now update info for these newly found commands
                 for command in cli_tool.commands:
                     if not command.help_text: # Only update if needed
                         self.update_command_info(command)
            else:
                 logger.warning(f"LLM did not identify any commands for '{cli_tool.name}' from help text.")

        except Exception as e:
            logger.error(f"Failed during LLM command extraction for '{cli_tool.name}': {e}", exc_info=True)


    def _process_llm_subcommands(self, parent: Union[CLITool, Command], subcommands_data: List[Dict[str, Any]], is_top_level: bool = False) -> None:
        """Helper to process subcommands identified by LLM."""
        parent_id = parent.id if isinstance(parent, Command) else None
        # Get the actual CLITool object, whether parent is the tool or a command within it
        the_tool = parent if isinstance(parent, CLITool) else getattr(parent, "cli_tool", None)
        if not the_tool:
             logger.error(f"Could not determine CLITool object for parent {getattr(parent, 'name', 'unknown')}")
             return # Cannot proceed without the tool object

        tool_id = the_tool.id # Get tool ID from the tool object
        existing_commands = getattr(the_tool, "commands", []) # Get commands from the tool object
        commands_by_name = {cmd.name: cmd for cmd in existing_commands if hasattr(cmd, 'name')}

        subcommands_added = 0
        for subcmd_data in subcommands_data:
            if isinstance(subcmd_data, dict):
                subcommand_name = subcmd_data.get("name")
                # Fix for Pylance Error Line 884: Check if subcommand_name is not None
                if not subcommand_name:
                    logger.warning("LLM identified a subcommand without a name, skipping.")
                    continue

                # Check if this command/subcommand already exists at the correct level
                already_exists = False
                if subcommand_name in commands_by_name:
                    existing_cmd = commands_by_name[subcommand_name]
                    # Check if it's correctly parented (or top-level)
                    if (is_top_level and not getattr(existing_cmd, 'parent_command_id', None)) or \
                       (not is_top_level and getattr(existing_cmd, 'parent_command_id', None) == parent_id):
                        already_exists = True
                        # Update description if LLM provided one and existing is empty
                        if not existing_cmd.description and subcmd_data.get("description"):
                            existing_cmd.description = subcmd_data.get("description")


                if not already_exists:
                    subcommand = Command(
                        cli_tool_id=tool_id,
                        name=subcommand_name,
                        description=subcmd_data.get("description", ""),
                        is_subcommand=not is_top_level,
                        parent_command_id=parent_id,
                    )
                    existing_commands.append(subcommand) # Add to the tool's command list
                    commands_by_name[subcommand_name] = subcommand # Add to lookup
                    subcommands_added += 1

        if subcommands_added > 0:
             parent_name = getattr(parent, "name", "tool")
             logger.info(f"Added {subcommands_added} new subcommands identified by LLM under '{parent_name}'.")


    def _apply_relationship_insights(
        self, cli_tool: CLITool, relationships: Dict[str, Any]
    ) -> None:
        """
        Apply relationship insights (parent/child) to the command structure.
        """
        commands_by_name = {cmd.name: cmd for cmd in cli_tool.commands if hasattr(cmd, 'name')}

        for relation in relationships.get("parent_child", []):
            if not isinstance(relation, dict): continue
            parent_name = relation.get("parent")
            child_name = relation.get("child")

            if not parent_name or not child_name: continue
            if parent_name not in commands_by_name or child_name not in commands_by_name: continue

            parent_cmd = commands_by_name[parent_name]
            child_cmd = commands_by_name[child_name]

            # Update relationship if child is currently considered top-level or has wrong parent
            if not child_cmd.is_subcommand or child_cmd.parent_command_id != parent_cmd.id:
                logger.info(f"Applying relationship: Setting '{parent_name}' as parent of '{child_name}'.")
                child_cmd.is_subcommand = True
                child_cmd.parent_command_id = parent_cmd.id
                # ORM relationships might update automatically, or might need explicit add/remove
                # if hasattr(parent_cmd, 'subcommands') and child_cmd not in parent_cmd.subcommands:
                #     parent_cmd.subcommands.append(child_cmd)

    # --- Removed Private Methods (Moved to LLMAnalysisHelper) ---
    # _generate_command_help_with_llm
    # _enhance_description_with_llm
    # _extract_examples_with_llm
    # _analyze_command_semantics
    # _analyze_command_relationships
    # _extract_options_and_args_with_llm -> consolidated into _extract_structure_llm
    # _generate_help_text_with_llm
    # _extract_command_structure_with_llm -> consolidated into _extract_structure_llm
    # _analyze_tool_purpose
    # _analyze_subcommand_purpose

    # --- Removed Fallback Method ---
    # process_examples -> Logic handled by helper/result_processor
