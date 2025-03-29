u"""
CLI commands for analyzing tools.

This module provides the CLI interface for analyzing CLI tools.

Note: This module imports from testronaut.analyzers and serves as a
backward compatibility layer to maintain existing imports.
Most functionality has been moved to the analyzers package.
"""

import warnings
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from testronaut.analyzers import (
    Spinner,
    analyze_tool,
    display_token_usage,
    get_analyzer,
    load_user_preferences,
    save_analysis_data,
    save_user_preferences,
    validate_cli_tool_data,
)
from testronaut.utils.logging import get_logger

# Show deprecation warning
warnings.warn(
    "The testronaut.cli.analyze module is deprecated. Use testronaut.analyzers instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Initialize logger and console
logger = get_logger(__name__)
console = Console()

# Re-export all imported functions and classes for backward compatibility
__all__ = [
    "analyze_tool",
    "display_token_usage",
    "get_analyzer",
    "load_user_preferences",
    "save_analysis_data",
    "save_user_preferences",
    "validate_cli_tool_data",
    "Spinner",
    "app",
]

# Typer app for CLI interface
# Note: invoke_without_command is removed as we now define a default command.
app = typer.Typer(
    help="Analyze CLI tool structure and generate initial test plan.",
)


# Define the main analysis logic as the default command for the 'analyze' subcommand.
# Typer uses the function name if no command name is provided in the decorator.
# We make this the primary way to run analysis.
@app.command(name="run", help="Run analysis on a specified CLI tool.", hidden=True) # Hidden for cleaner --help, but still callable
def run_analysis(
    tool: str = typer.Argument(
        ..., help="Name or path of the CLI tool to analyze (must be in PATH or valid path)"
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
    Analyze a CLI tool by parsing its help text and command structure.
    This is the primary analysis command.
    """
    # Run analysis
    logger.info(f"Starting analysis for tool: {tool}", tool=tool, depth=depth, enhanced=enhanced)
    try:
        cli_tool = analyze_tool(
            tool_path=tool,
            output=output,
            deep=(depth > 1),
            enhanced=enhanced,
            interactive=interactive,
            max_commands=100 if depth > 1 else 20,
            # TODO: Pass skip_cache if needed by analyze_tool
        )

        if not cli_tool:
            console.print(f"[bold red]Error:[/bold red] Analysis failed for tool '{tool}'. No analysis data returned.")
            raise typer.Exit(code=1)

        # Display analysis summary
        console.print(Panel(f"[bold]Analysis of {tool}[/bold]", expand=False))
        console.print(f"[bold]Name:[/bold] {cli_tool.name}")
        console.print(f"[bold]Version:[/bold] {cli_tool.version or 'Unknown'}")
        console.print(f"[bold]Description:[/bold] {cli_tool.description or 'None'}")

        # Display commands
        console.print(f"\n[bold]Commands:[/bold] {len(cli_tool.commands)}")

        # Limit displayed commands for brevity
        display_limit = 10
        for i, command in enumerate(cli_tool.commands):
            if i >= display_limit:
                console.print(f"... and {len(cli_tool.commands) - display_limit} more commands")
                break
            console.print(f"  [bold]{command.name}[/bold]: {command.description or 'No description'}")

        # Display token usage if enhanced analysis was used
        if enhanced and cli_tool.meta_data and cli_tool.meta_data.llm_usage:
            display_token_usage(cli_tool.meta_data.llm_usage)

        logger.info(f"Analysis completed successfully for tool: {tool}", tool=tool)

    except Exception as e:
        logger.error(f"Analysis failed for tool '{tool}': {e}", exc_info=True)
        console.print(f"[bold red]Error during analysis:[/bold red] {e}")
        raise typer.Exit(code=1)

# Note: The if __name__ == "__main__": block is removed as this module
# should now only be imported and used via the main CLI entry point.
