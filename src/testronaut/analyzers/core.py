"""
Core analyzer functionality.

This module provides core functions for analyzing CLI tools and saving results.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Union, cast

from testronaut.analyzers.llm_enhanced_analyzer import LLMEnhancedAnalyzer
from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.models.cli_tool import CLITool
from testronaut.utils.command import CommandRunner
from testronaut.utils.json_encoder import CLIToolJSONEncoder
from testronaut.utils.logging import configure_logging, get_logger

# Initialize logger
logger = get_logger(__name__)


class Spinner:
    """
    Context manager for displaying a spinner during long-running operations.

    This is a utility class used to show progress during analysis.
    """

    def __init__(self, text: str = "Processing...") -> None:
        """Initialize with optional custom text."""
        self.text = text
        self.progress: Optional[Any] = None

    def __enter__(self) -> "Spinner":
        """Set up and start the progress spinner."""
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        )
        if self.progress:
            self.task_id = self.progress.add_task(self.text, total=None)
            self.progress.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clean up by stopping the progress spinner."""
        if self.progress:
            self.progress.stop()


def get_analyzer(
    enhanced: bool = False,
) -> Union[LLMEnhancedAnalyzer, StandardCLIAnalyzer]:
    """
    Get the appropriate analyzer based on the enhanced flag.

    Args:
        enhanced: Whether to use the LLM-enhanced analyzer.

    Returns:
        The analyzer instance.
    """
    # Create a command runner
    runner = CommandRunner()

    if enhanced:
        return LLMEnhancedAnalyzer(command_runner=runner)
    else:
        return StandardCLIAnalyzer(command_runner=runner)


def validate_cli_tool_data(cli_tool: CLITool) -> bool:
    """
    Validate that all essential data is present in the CLI tool object.

    Args:
        cli_tool: The CLI tool object to validate.

    Returns:
        bool: True if validation passes, False otherwise.
    """
    if not cli_tool.name:
        logger.warning("CLI tool name is missing")
        return False

    if not cli_tool.commands:
        logger.warning("No commands found in CLI tool")
        return False

    for cmd in cli_tool.commands:
        if not cmd.name:
            logger.warning(f"Command name is missing in command {id(cmd)}")
            return False

    logger.debug(f"Found {len(cli_tool.commands)} commands in {cli_tool.name}")
    return True


def save_analysis_data(cli_tool: CLITool, output_file: Path) -> None:
    """
    Save analysis data with validation and debug information.

    Args:
        cli_tool: The CLI tool object to save.
        output_file: The path to save the data to.
    """
    # Validate data before saving
    if not validate_cli_tool_data(cli_tool):
        logger.warning("Data validation failed, saving may result in incomplete data")

    # Save raw data for debugging if verbose logging is enabled
    if logger.isEnabledFor(10):  # DEBUG level
        debug_file = output_file.with_suffix(".debug.json")
        with open(debug_file, "w") as f:
            json.dump(cli_tool.model_dump(mode="json"), f, indent=2)
            logger.debug(f"Debug data saved to {debug_file}")

    # Save the main analysis data
    try:
        data = cli_tool.model_dump(mode="json")
        with open(output_file, "w") as f:
            json.dump(data, f, cls=CLIToolJSONEncoder, indent=2)
            logger.info(f"Analysis saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving analysis data: {e}")
        raise


def analyze_tool(
    tool_path: str,
    output: Optional[Path] = None,
    deep: bool = False,
    enhanced: bool = False,
    verbose: bool = False,
    sql_debug: bool = False,
    interactive: bool = False,
    max_commands: Optional[int] = None,
) -> CLITool:
    """
    Analyze a CLI tool and generate a report of its commands, options, and arguments.

    Args:
        tool_path: Path to the CLI tool to analyze.
        output: Directory to output the analysis as JSON files.
        deep: Whether to perform a deep analysis of options and arguments.
        enhanced: Whether to use LLM-enhanced analysis for better descriptions.
        verbose: Whether to enable verbose logging.
        sql_debug: Whether to enable SQL debug logging.
        interactive: Whether to run in interactive mode to select commands for analysis.
        max_commands: Maximum number of commands to analyze.

    Returns:
        The analyzed CLI tool object.
    """
    # Initialize logger with user settings
    configure_logging(level="DEBUG" if verbose else "INFO", json_output=sql_debug)

    # Extract tool name from path
    tool_name = os.path.basename(tool_path)

    # Initialize the analyzer
    analyzer = get_analyzer(enhanced=enhanced)

    # Analyze the tool based on the analyzer type
    if enhanced:
        # LLMEnhancedAnalyzer has a different interface
        cli_tool = analyzer.analyze_cli_tool(tool_name=tool_path, max_commands=max_commands)
    else:
        # StandardCLIAnalyzer supports discovery_timeout and max_depth
        std_analyzer = cast(StandardCLIAnalyzer, analyzer)
        cli_tool = std_analyzer.analyze_cli_tool(
            tool_name=tool_path,
            max_depth=5 if deep else 1,
            discovery_timeout=300,
            max_commands=max_commands if max_commands is not None else (100 if deep else 20),
        )

    # Save the result if output is specified
    if output:
        output_dir = Path(output)
        output_dir.mkdir(exist_ok=True, parents=True)
        output_file = output_dir / f"{tool_name}_analysis.json"
        save_analysis_data(cli_tool, output_file)

    return cli_tool
