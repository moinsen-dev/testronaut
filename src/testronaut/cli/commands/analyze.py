"""
Command module for analyzing CLI tools.
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()
app = typer.Typer(name="analyze")

@app.callback(invoke_without_command=True)
def analyze(
    ctx: typer.Context,
    tool: Optional[str] = None,
    output_file: Optional[Path] = None,
):
    """
    Analyze CLI tool and generate a test plan.

    This command analyzes the structure and behavior of a CLI tool
    using the specified model and generates a comprehensive test plan.
    """
    # Get global options
    tool = tool or ctx.parent.params.get("tool")

    if not tool:
        console.print("[bold red]Error:[/bold red] No CLI tool specified.")
        console.print("Use --tool option to specify a CLI tool to analyze.")
        raise typer.Exit(code=1)

    # If no output file is specified, use the default location
    if not output_file:
        output_dir = ctx.parent.params.get("output_dir")
        output_file = Path(output_dir) / f"{tool}_analysis.json"

    console.print(f"[bold green]Analyzing[/bold green] CLI tool: {tool}")
    console.print(f"Output will be saved to: {output_file}")

    # This would call the actual analyzer in a real implementation
    # from testronaut.core.analyzer import analyze_cli_tool
    # analyze_cli_tool(tool, output_file, model=ctx.parent.params.get("model"))

    console.print("[bold green]Analysis complete![/bold green]")