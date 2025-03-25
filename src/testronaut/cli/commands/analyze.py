"""
Command module for analyzing CLI tools.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.console import Console
from rich.panel import Panel

# Import the original analyze functionality
from testronaut.cli.analyze import (
    analyze_tool,
    display_token_usage,
    save_user_preferences,
)

console = Console()
app = typer.Typer(name="analyze")


@app.command()
def tool(
    ctx: typer.Context,
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
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode for selecting commands to analyze"
    ),
) -> None:
    """
    Analyze a CLI tool.
    """
    # Get global options from context
    params: Dict[str, Any] = {}
    if ctx.parent is not None:
        params = ctx.parent.params or {}

    tool_path = tool or params.get("tool")

    if not tool_path:
        console.print("[bold red]Error:[/bold red] No CLI tool specified.")
        console.print("Use --tool option to specify a CLI tool to analyze.")
        raise typer.Exit(code=1)

    # If no output is specified, use the default location
    if not output:
        output_dir = params.get("output_dir")
        if output_dir:
            output = Path(output_dir)
        else:
            output = Path("./testronaut-output")
            output.mkdir(exist_ok=True, parents=True)

    # Show analysis options
    console.print(Panel(f"[bold]Analysis of {tool_path}[/bold]", expand=False))
    console.print(f"[bold]Depth:[/bold] {depth}")
    console.print(f"[bold]Enhanced Mode:[/bold] {'Enabled' if enhanced else 'Disabled'}")
    console.print(f"[bold]Interactive Mode:[/bold] {'Enabled' if interactive else 'Disabled'}")
    console.print(f"[bold]Output Location:[/bold] {output}")

    if interactive:
        console.print(
            "\n[bold yellow]Interactive Mode Enabled:[/bold yellow] You will be prompted to select commands to analyze."
        )

    # Run the original analyze_tool function with the appropriate parameters
    cli_tool = analyze_tool(
        tool_path=tool_path,
        output=output,
        deep=(depth > 1),
        enhanced=enhanced,
        interactive=interactive,  # Make sure interactive flag is passed
        verbose=params.get("verbose", False),
        max_commands=100 if depth > 1 else 20,
    )

    # Display analysis summary
    console.print(Panel(f"[bold]Analysis Results for {tool_path}[/bold]", expand=False))
    console.print(f"[bold]Name:[/bold] {cli_tool.name}")
    console.print(f"[bold]Version:[/bold] {cli_tool.version or 'Unknown'}")
    console.print(f"[bold]Description:[/bold] {cli_tool.description or 'None'}")

    # Display commands
    console.print(f"\n[bold]Commands:[/bold] {len(cli_tool.commands)}")

    for i, command in enumerate(cli_tool.commands, 1):
        if i > 10:
            console.print(f"... and {len(cli_tool.commands) - 10} more commands")
            break

        # Safely access command attributes
        cmd_name = getattr(command, "name", "Unknown")
        cmd_desc = getattr(command, "description", "No description")
        console.print(f"  [bold]{cmd_name}[/bold]: {cmd_desc}")

    # Display token usage if enhanced analysis was used
    if enhanced and cli_tool.meta_data and cli_tool.meta_data.llm_usage:
        display_token_usage(cli_tool.meta_data.llm_usage)

    console.print("[bold green]Analysis complete![/bold green]")

    # Save user preferences for this tool
    save_user_preferences(tool_path, enhanced)
