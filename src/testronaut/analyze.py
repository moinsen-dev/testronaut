"""
CLI tool analyzer module.

This module provides functionality to analyze CLI tools and save the results.
"""

import json
import logging
import os
from typing import List, Optional, Union, cast

from testronaut.analyzers.llm_enhanced_analyzer import LLMEnhancedAnalyzer
from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.models.cli_tool import CLITool, Command
from testronaut.utils.json_encoder import CLIToolJSONEncoder
from testronaut.utils.logging import configure_logging

# Configure logger
logger = logging.getLogger(__name__)


def display_token_usage(cli_tool: CLITool) -> None:
    """Display token usage information."""
    token_usage = cli_tool.get_token_usage()
    if not token_usage:
        logger.info("No token usage information available")
        return

    logger.info("Token Usage Summary:")
    logger.info(f"Total tokens: {token_usage.total_tokens:,}")
    logger.info(f"Prompt tokens: {token_usage.prompt_tokens:,}")
    logger.info(f"Completion tokens: {token_usage.completion_tokens:,}")
    logger.info(f"API calls: {token_usage.api_calls}")
    logger.info(f"Estimated cost: ${token_usage.estimated_cost:.4f}")

    if token_usage.models_used:
        logger.info("\nToken usage by model:")
        for model, tokens in token_usage.models_used.items():
            logger.info(f"{model}: {tokens:,} tokens")


def analyze_tool(
    tool_name: str,
    output_dir: str = ".",
    max_commands: Optional[int] = None,
    analyzer_type: str = "standard",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """
    Analyze a CLI tool and save the results.

    Args:
        tool_name: Name of the CLI tool to analyze
        output_dir: Directory to save analysis results
        max_commands: Maximum number of commands to analyze
        analyzer_type: Type of analyzer to use ('standard' or 'llm')
        log_level: Logging level
        log_file: Optional log file path
    """
    # Configure logging
    configure_logging(log_level, log_file)

    # Create analyzer instance
    analyzer: Union[StandardCLIAnalyzer, LLMEnhancedAnalyzer]
    if analyzer_type.lower() == "llm":
        analyzer = LLMEnhancedAnalyzer()
    else:
        analyzer = StandardCLIAnalyzer()

    try:
        # Analyze the tool
        cli_tool = analyzer.analyze_cli_tool(tool_name, max_commands=max_commands)
        if not cli_tool:
            logger.error(f"Failed to analyze {tool_name}")
            return

        # Display token usage if available
        display_token_usage(cli_tool)

        # Prepare output path
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "testronaut_analysis.json")

        # Convert to dict and save
        tool_dict = cli_tool.model_dump(exclude_none=True)

        # Ensure commands are properly serialized
        if cli_tool.commands:
            # Cast the commands to the correct type
            commands = cast(List[Command], cli_tool.commands)
            tool_dict["commands"] = [command.model_dump(exclude_none=True) for command in commands]

        with open(output_file, "w") as f:
            json.dump(tool_dict, f, indent=2, cls=CLIToolJSONEncoder)

        logger.info(f"Analysis saved to {output_file}")

    except Exception as e:
        logger.error(f"Error analyzing {tool_name}: {e}")
        raise
