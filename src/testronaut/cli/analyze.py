"""
CLI commands for analyzing tools.

This module provides the CLI interface for analyzing CLI tools.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

try:
    import questionary

    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from testronaut.analyzers.llm_enhanced_analyzer import LLMEnhancedAnalyzer
from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.config import Settings
from testronaut.models.cli_tool import CLITool, TokenUsage
from testronaut.utils.command import CommandRunner
from testronaut.utils.json_encoder import CLIToolJSONEncoder
from testronaut.utils.logging import configure_logging, get_logger

# Initialize logger and console
logger = get_logger(__name__)
console = Console()


class Spinner:
    """
    Context manager for displaying a spinner during long-running operations.
    """

    def __init__(self, text: str = "Processing...") -> None:
        self.text = text
        self.progress: Optional[Progress] = None

    def __enter__(self) -> "Spinner":
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


def save_user_preferences(tool_name: str, enhanced: bool = False) -> None:
    """
    Save user preferences for a specific tool.

    Args:
        tool_name: The name of the tool.
        enhanced: Whether to use enhanced analysis.
    """
    # Use the config directory from settings
    settings = Settings()
    config_dir = Path(settings.config_dir)
    config_dir.mkdir(exist_ok=True, parents=True)
    preferences_file = config_dir / "tool_preferences.json"

    # Load existing preferences or create new
    if preferences_file.exists():
        try:
            with open(preferences_file, "r") as f:
                preferences = json.load(f)
        except json.JSONDecodeError:
            preferences = {}
    else:
        preferences = {}

    # Update preferences
    preferences[tool_name] = {"enhanced": enhanced}

    # Save preferences
    with open(preferences_file, "w") as f:
        json.dump(preferences, f)


def load_user_preferences(tool_name: str) -> Dict[str, Any]:
    """
    Load user preferences for a specific tool.

    Args:
        tool_name: The name of the tool.

    Returns:
        The preferences for the tool.
    """
    # Use the config directory from settings
    settings = Settings()
    config_dir = Path(settings.config_dir)
    preferences_file = config_dir / "tool_preferences.json"

    # Load existing preferences or create new
    if preferences_file.exists():
        try:
            with open(preferences_file, "r") as f:
                preferences = json.load(f)
                if tool_name in preferences:
                    return preferences[tool_name]
        except json.JSONDecodeError:
            pass

    return {}


def display_token_usage(token_usage: TokenUsage) -> None:
    """
    Display token usage information.

    Args:
        token_usage: The token usage information.
    """
    console.print("\n[bold]Token Usage Information:[/bold]")

    # Create a table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    # Add rows
    table.add_row("Total API Calls", str(token_usage.api_calls))
    table.add_row("Total Tokens", str(token_usage.total_tokens))
    table.add_row("Prompt Tokens", str(token_usage.prompt_tokens))
    table.add_row("Completion Tokens", str(token_usage.completion_tokens))
    table.add_row("Estimated Cost", f"${token_usage.estimated_cost:.6f}")

    # Models used
    if token_usage.models_used:
        model_str = ", ".join(
            f"{model}: {count} tokens" for model, count in token_usage.models_used.items()
        )
        table.add_row("Models Used", model_str)

    console.print(table)


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


# Typer app for CLI interface
app = typer.Typer()


@app.command()
def tool(
    tool: Optional[str] = typer.Argument(
        None, help="Name of the CLI tool to analyze (must be in PATH)"
    ),
    depth: int = typer.Option(
        1, "--depth", "-d", help="Depth of analysis (1-3, higher is more detailed)"
    ),
    enhanced: bool = typer.Option(
        False, "--enhanced", "-e", help="Use LLM-enhanced analysis (requires API key)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Directory to save output JSON"
    ),
    skip_cache: bool = typer.Option(False, "--skip-cache", help="Skip the command cache"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
) -> None:
    """
    Analyze a CLI tool.
    """
    if not tool:
        console.print("[bold red]Error:[/bold red] No tool specified.")
        return

    # Run analysis
    cli_tool = analyze_tool(
        tool_path=tool,
        output=output,
        deep=(depth > 1),
        enhanced=enhanced,
        interactive=interactive,
        max_commands=100 if depth > 1 else 20,
    )

    # Display analysis summary
    console.print(Panel(f"[bold]Analysis of {tool}[/bold]", expand=False))
    console.print(f"[bold]Name:[/bold] {cli_tool.name}")
    console.print(f"[bold]Version:[/bold] {cli_tool.version or 'Unknown'}")
    console.print(f"[bold]Description:[/bold] {cli_tool.description or 'None'}")

    # Display commands
    console.print(f"\n[bold]Commands:[/bold] {len(cli_tool.commands)}")

    for i, command in enumerate(cli_tool.commands, 1):
        if i > 10:
            console.print(f"... and {len(cli_tool.commands) - 10} more commands")
            break

        console.print(f"  [bold]{command.name}[/bold]: {command.description or 'No description'}")

    # Display token usage if enhanced analysis was used
    if enhanced and cli_tool.meta_data and cli_tool.meta_data.llm_usage:
        display_token_usage(cli_tool.meta_data.llm_usage)


if __name__ == "__main__":
    app()
