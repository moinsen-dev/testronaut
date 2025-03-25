"""
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
