"""
Helper class for LLM interactions within the CLI analysis process.

Encapsulates specific LLM calls, prompt generation, schema definitions,
and basic result processing related to analyzing CLI tools.
"""

import time
from typing import Any, Dict, List, Optional, cast

from testronaut.models import CLITool, Command, Example, Option, Argument # Import models used
from testronaut.utils.errors import CommandExecutionError, LLMServiceError, ValidationError
from testronaut.utils.llm import LLMService
from testronaut.utils.llm.prompts import CLIAnalysisPrompts
from testronaut.utils.llm.result_processor import LLMResultProcessor
from testronaut.utils.logging import get_logger

logger = get_logger(__name__)


class LLMAnalysisHelper:
    """Provides methods for specific LLM-based analysis tasks."""

    def __init__(self, llm_service: LLMService, result_processor: LLMResultProcessor):
        self.llm_service = llm_service
        self.result_processor = result_processor
        # Note: Token tracking happens in the main analyzer class

    def generate_command_help_with_llm(
        self, tool_name: str, command_name: str, parent_path: str, error_message: str, tool_help: str
    ) -> str:
        """
        Generate synthetic help text for a command using LLM when conventional methods fail.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            parent_path: The parent command path (if this is a subcommand).
            error_message: The error message from the conventional method.
            tool_help: Help text of the main tool for context.

        Returns:
            Synthetic help text as a string.

        Raises:
            CommandExecutionError: If the LLM generation fails.
        """
        # Build the full command path
        if parent_path:
            full_cmd = f"{tool_name} {parent_path} {command_name}"
            tool_arg = tool_name # Pass base tool name to prompt
            cmd_arg = f"{parent_path} {command_name}" # Pass subcommand path
        else:
            full_cmd = f"{tool_name} {command_name}"
            tool_arg = full_cmd # Pass full command if no parent
            cmd_arg = ""

        # Use the specialized prompt for command structure inference
        prompt = CLIAnalysisPrompts.command_structure_inference(
            tool_name=tool_arg,
            command_name=cmd_arg,
            tool_help_text=tool_help,
            error_context=error_message,
        )

        try:
            # Generate synthetic help text
            synthetic_help = self.llm_service.generate_text(prompt)
            logger.info(f"Generated synthetic help text for {full_cmd} using LLM")
            # Note: Token tracking is done by the caller (_track_llm_usage)
            return synthetic_help
        except LLMServiceError as e:
            logger.error(f"LLM generation failed for {full_cmd}: {str(e)}")
            raise CommandExecutionError(
                f"Failed to get help text for command {full_cmd} (LLM fallback failed)",
                details={"error": str(e), "original_error": error_message},
            )

    def enhance_description_with_llm(self, description: Optional[str], help_text: str, command_name: str = "tool") -> str:
        """
        Enhance a tool or command description using the LLM.

        Args:
            description: The original description.
            help_text: The full help text to analyze.
            command_name: Name of the command or tool for the prompt.

        Returns:
            Enhanced description as a string.
        """
        # Only enhance if description is missing or very short
        if not description or len(description.strip()) < 10:
            prompt = CLIAnalysisPrompts.command_purpose_analysis(command_name, help_text, description)
            try:
                response = self.llm_service.generate_text(prompt)
                # Note: Token tracking is done by the caller (_track_llm_usage)
                processed_description = self.result_processor.process_command_purpose(response)
                return processed_description
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to enhance description for '{command_name}' with LLM: {str(e)}")
                return description or "" # Return original or empty string
        return description # Return original if it was sufficient

    def extract_examples_with_llm(
        self, tool_name: str, command_name: str, help_text: str
    ) -> List[Dict[str, str]]:
        """
        Extract usage examples for a command using LLM.

        Args:
            tool_name: CLI tool name.
            command_name: Command name.
            help_text: Command help text.

        Returns:
            List of examples (dictionaries with 'command_line' and 'description').
        """
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "command_line": {"type": "string", "description": "The example command line"},
                    "description": {
                        "type": "string",
                        "description": "Brief description of what the example does",
                    },
                },
                "required": ["command_line"],
            },
        }
        # Corrected method name
        prompt = CLIAnalysisPrompts.command_examples_extraction(tool_name, command_name, help_text)

        try:
            examples_data = self.llm_service.generate_json(prompt, schema)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            logger.debug(f"Generated {len(examples_data)} examples with LLM for {command_name}")
            # Ensure the result is a list of dicts
            if isinstance(examples_data, list):
                 return [ex for ex in examples_data if isinstance(ex, dict)]
            else:
                 logger.warning(f"LLM returned non-list for examples: {type(examples_data)}")
                 return []
        except LLMServiceError:
             logger.warning(f"JSON generation failed for examples of {command_name}, falling back to text.")
             try:
                 response = self.llm_service.generate_text(prompt)
                 # Note: Token tracking is done by the caller (_track_llm_usage)
                 # Use result processor to extract JSON from text
                 extracted_json = self.result_processor.extract_json_from_text(response)
                 if isinstance(extracted_json, list):
                     return [ex for ex in extracted_json if isinstance(ex, dict)]
                 elif isinstance(extracted_json, dict) and "examples" in extracted_json and isinstance(extracted_json["examples"], list):
                     return [ex for ex in extracted_json["examples"] if isinstance(ex, dict)]
                 else:
                     logger.warning(f"Could not extract structured examples from text fallback for {command_name}")
                     return []
             except (LLMServiceError, ValidationError) as e:
                 logger.warning(f"Failed to process examples from LLM text fallback for {command_name}: {str(e)}")
                 return []
        except Exception as e:
            logger.warning(f"Failed to generate examples for {command_name} with LLM: {str(e)}")
            return []

    def analyze_command_semantics(self, tool_name: str, command_name: str, help_text: str) -> Dict[str, Any]:
        """
        Perform semantic analysis of a command using LLM.

        Args:
            tool_name: Name of the CLI tool.
            command_name: Name of the command.
            help_text: Help text of the command.

        Returns:
            Dictionary with semantic analysis information.
        """
        if not help_text:
            return {}

        prompt = CLIAnalysisPrompts.command_semantic_analysis(tool_name, command_name, help_text)
        schema = {
            "type": "object",
            "properties": {
                "primary_function": {"type": "string", "description": "The main purpose or action of the command"},
                "common_use_cases": {"type": "array", "items": {"type": "string"}, "description": "Typical scenarios where this command is used"},
                "key_options": {"type": "array", "items": {"type": "string"}, "description": "List the most important or frequently used options/flags"},
                "output_description": {"type": "string", "description": "Briefly describe the typical output of the command"},
                "risk_level": {"type": "string", "enum": ["low", "medium", "high", "unknown"], "description": "Potential risk (e.g., data modification, system changes)"},
                "related_commands": {"type": "array", "items": {"type": "string"}, "description": "Other commands often used with or related to this one"},
            },
            "required": ["primary_function", "risk_level"],
        }

        try:
            analysis = self.llm_service.generate_json(prompt, schema)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            logger.debug(f"Generated semantic analysis for command: {command_name}")
            return cast(Dict[str, Any], analysis)
        except LLMServiceError:
            logger.warning(f"JSON generation failed for semantics of {command_name}, falling back to text.")
            try:
                response = self.llm_service.generate_text(prompt)
                # Note: Token tracking is done by the caller (_track_llm_usage)
                analysis = self.result_processor.process_semantic_analysis(response) # Assumes processor handles text
                return analysis
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze command semantics for {command_name} via text fallback: {str(e)}")
                return {}
        except Exception as e:
             logger.warning(f"Unexpected error analyzing command semantics for {command_name}: {str(e)}")
             return {}

    def analyze_command_relationships(self, tool_name: str, commands: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze relationships between commands using LLM.

        Args:
            tool_name: The name of the CLI tool.
            commands: List of command dictionaries with 'name' and 'description'.

        Returns:
            Dictionary with relationship information (parent_child, workflows, dependencies).
        """
        if not commands:
            return {"parent_child": [], "workflows": [], "dependencies": []}

        prompt = CLIAnalysisPrompts.command_relationships_analysis(tool_name, commands)
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
                    "description": "Pairs of parent and child commands.",
                },
                "workflows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the workflow"},
                            "steps": {"type": "array", "items": {"type": "string"}, "description": "Sequence of command names in the workflow"},
                        },
                        "required": ["name", "steps"],
                    },
                    "description": "Common sequences or workflows involving multiple commands.",
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
                     "description": "Commands that depend on the prior execution or state set by another command.",
                },
            },
        }

        try:
            relationships = self.llm_service.generate_json(prompt, schema)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            logger.debug(f"Generated relationship analysis for tool: {tool_name}")
            return cast(Dict[str, Any], relationships)
        except LLMServiceError:
            logger.warning(f"JSON generation failed for relationships of {tool_name}, falling back to text.")
            try:
                response = self.llm_service.generate_text(prompt)
                # Note: Token tracking is done by the caller (_track_llm_usage)
                relationships = self.result_processor.process_relationships(response) # Assumes processor handles text
                return relationships
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze command relationships for {tool_name} via text fallback: {str(e)}")
                return {"parent_child": [], "workflows": [], "dependencies": []}
        except Exception as e:
             logger.warning(f"Unexpected error analyzing command relationships for {tool_name}: {str(e)}")
             return {"parent_child": [], "workflows": [], "dependencies": []}

    def extract_structure_with_llm(
        self, tool_name: str, command_name: str, help_text: str
    ) -> Dict[str, Any]:
        """
        Extract command structure (options, args, examples, subcommands) using LLM.
        Consolidates logic from _extract_options_and_args_with_llm and _extract_command_structure_with_llm.

        Args:
            tool_name: The name of the CLI tool.
            command_name: The name of the command.
            help_text: The help text to analyze.

        Returns:
            Dictionary with command structure information.
        """
        logger.info(f"Extracting command structure for '{command_name}' using LLM...")
        start_time = time.time()

        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Concise description of the command's purpose"},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Primary identifier for the option (e.g., '--verbose', '-f')"},
                            "short_form": {"type": "string", "nullable": True, "description": "Short form flag (e.g., '-v')"},
                            "long_form": {"type": "string", "nullable": True, "description": "Long form flag (e.g., '--verbose')"},
                            "description": {"type": "string", "description": "Explanation of what the option does"},
                            "required": {"type": "boolean", "description": "Is this option mandatory?"},
                            "takes_value": {"type": "boolean", "description": "Does this option expect a value?"},
                        },
                        "required": ["name", "description"],
                    },
                    "description": "List of command-line options/flags.",
                },
                "arguments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name or placeholder for the argument (e.g., '<file>', 'hostname')"},
                            "description": {"type": "string", "description": "Explanation of what the argument represents"},
                            "required": {"type": "boolean", "description": "Is this argument mandatory?"},
                        },
                        "required": ["name"],
                    },
                    "description": "List of positional or named arguments.",
                },
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "command_line": {"type": "string", "description": "The full example command line"},
                            "description": {"type": "string", "nullable": True, "description": "Explanation of the example"},
                        },
                        "required": ["command_line"],
                    },
                    "description": "Usage examples.",
                },
                "subcommands": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the subcommand"},
                            "description": {"type": "string", "nullable": True, "description": "Description of the subcommand"},
                        },
                        "required": ["name"],
                    },
                    "description": "List of subcommands, if any.",
                },
            },
            "required": ["description"], # Only description is strictly required at the top level
        }
        prompt = CLIAnalysisPrompts.command_structure_inference(tool_name, command_name, help_text, error_context=None) # Use inference prompt

        try:
            result = self.llm_service.generate_json(prompt, schema)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            elapsed_time = time.time() - start_time
            logger.info(
                f"Extracted command structure for '{command_name}' in {elapsed_time:.2f} seconds"
            )
            return cast(Dict[str, Any], result)
        except LLMServiceError:
            logger.warning(f"JSON generation failed for structure of {command_name}, falling back to text.")
            try:
                response = self.llm_service.generate_text(prompt)
                # Note: Token tracking is done by the caller (_track_llm_usage)
                result = self.result_processor.extract_json_from_text(response) # Assumes processor handles text
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Extracted command structure for '{command_name}' via text fallback in {elapsed_time:.2f} seconds"
                )
                # Basic validation: ensure it's a dict
                return result if isinstance(result, dict) else {}
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to extract command structure for {command_name} via text fallback: {str(e)}")
                return {}
        except Exception as e:
             logger.warning(f"Unexpected error extracting command structure for {command_name}: {str(e)}")
             return {}

    def generate_help_text_with_llm(self, tool_name: str, command_name: str, description: Optional[str], purpose: Optional[str]) -> str:
        """
        Generate help text for a command using LLM when standard methods fail.

        Args:
            tool_name: Name of the CLI tool.
            command_name: Name of the command.
            description: Optional existing description.
            purpose: Optional existing purpose analysis.

        Returns:
            Generated help text.
        """
        prompt = f"""
        Create realistic help text for the command '{command_name}' from the CLI tool '{tool_name}'.

        I don't have access to the actual help text, so I need you to generate it based on the following information:

        Command name: {command_name}
        Description: {description or 'Not available'}
        Purpose: {purpose or 'Not available'}

        The help text should include:
        1. A description of what the command does (use provided description/purpose if available)
        2. The command syntax (e.g., {tool_name} {command_name} [OPTIONS] [ARGUMENTS])
        3. Plausible options and flags based on the command's likely function (e.g., --input <file>, --verbose, --force)
        4. Plausible required or optional arguments
        5. At least one example usage

        Format it to look like standard CLI help text, using appropriate spacing and formatting.
        Make educated guesses based on common CLI patterns for a command like '{command_name}'.
        """

        try:
            help_text = self.llm_service.generate_text(prompt)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            logger.info(f"Generated synthetic help text for {command_name} via LLM.")
            return help_text
        except Exception as e:
            logger.error(f"Failed to generate help text for {command_name} with LLM: {str(e)}")
            return f"Help text for {command_name} (LLM generation failed)"

    def analyze_tool_purpose(self, tool_name: str, help_text: str) -> Dict[str, Any]:
        """
        Analyze the overall purpose, background, use cases, and testing considerations of a CLI tool.

        Args:
            tool_name: Name of the CLI tool.
            help_text: Help text of the tool.

        Returns:
            Dictionary with purpose analysis information.
        """
        if not help_text:
            return {}

        prompt = CLIAnalysisPrompts.tool_purpose_analysis(tool_name, help_text)
        schema = {
            "type": "object",
            "properties": {
                "purpose": {"type": "string", "description": "The main purpose of the tool"},
                "background": {"type": "string", "description": "Technical context for understanding the tool"},
                "use_cases": {"type": "array", "items": {"type": "string"}, "description": "Common use cases for the tool"},
                "testing_considerations": {"type": "array", "items": {"type": "string"}, "description": "Special considerations for testing"},
            },
            "required": ["purpose"],
        }

        try:
            analysis = self.llm_service.generate_json(prompt, schema)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            logger.debug(f"Generated purpose analysis for tool: {tool_name}")
            return cast(Dict[str, Any], analysis)
        except LLMServiceError:
            logger.warning(f"JSON generation failed for tool purpose {tool_name}, falling back to text.")
            try:
                response = self.llm_service.generate_text(prompt)
                # Note: Token tracking is done by the caller (_track_llm_usage)
                analysis = self.result_processor.process_tool_purpose_analysis(response) # Assumes processor handles text
                return analysis
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze tool purpose for {tool_name} via text fallback: {str(e)}")
                return {}
        except Exception as e:
             logger.warning(f"Unexpected error analyzing tool purpose for {tool_name}: {str(e)}")
             return {}

    def analyze_subcommand_purpose(self, tool_name: str, command_name: str, help_text: str) -> str:
        """
        Analyze the purpose of a specific subcommand using LLM.

        Args:
            tool_name: Name of the CLI tool.
            command_name: Name of the command.
            help_text: Help text of the command.

        Returns:
            String with the command's purpose, or empty string if failed.
        """
        if not help_text:
            return ""

        prompt = CLIAnalysisPrompts.subcommand_purpose_analysis(tool_name, command_name, help_text)
        schema = { # Although asking for just purpose, using schema helps consistency
            "type": "object",
            "properties": {
                "purpose": {"type": "string", "description": "The specific purpose of this command"},
            },
            "required": ["purpose"],
        }

        try:
            analysis = self.llm_service.generate_json(prompt, schema)
            # Note: Token tracking is done by the caller (_track_llm_usage)
            logger.debug(f"Generated purpose analysis for command: {command_name}")
            return cast(Dict[str, Any], analysis).get("purpose", "")
        except LLMServiceError:
            logger.warning(f"JSON generation failed for subcommand purpose {command_name}, falling back to text.")
            try:
                response = self.llm_service.generate_text(prompt)
                # Note: Token tracking is done by the caller (_track_llm_usage)
                return self.result_processor.extract_purpose(response) # Assumes processor handles text
            except (LLMServiceError, ValidationError) as e:
                logger.warning(f"Failed to analyze command purpose for {command_name} via text fallback: {str(e)}")
                return ""
        except Exception as e:
             logger.warning(f"Unexpected error analyzing command purpose for {command_name}: {str(e)}")
             return ""
