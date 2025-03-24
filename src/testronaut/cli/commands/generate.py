"""
Command module for generating test plans.
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()
app = typer.Typer(name="generate")

@app.callback(invoke_without_command=True)
def generate(
    ctx: typer.Context,
    analysis_file: Optional[Path] = typer.Option(
        None,
        "--analysis",
        "-a",
        help="Path to analysis file",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to output test plan file",
    ),
):
    """
    Generate test plan from CLI analysis.

    This command uses the analysis of a CLI tool to generate
    a comprehensive test plan, including test cases and expected results.
    """
    # Get global options
    tool = ctx.parent.params.get("tool")
    output_dir = ctx.parent.params.get("output_dir")

    # If no analysis file is specified, use the default location
    if not analysis_file:
        analysis_file = Path(output_dir) / f"{tool}_analysis.json"

    # If no output file is specified, use the default location
    if not output_file:
        output_file = Path(output_dir) / f"{tool}_test_plan.json"

    if not analysis_file.exists():
        console.print(f"[bold red]Error:[/bold red] Analysis file not found: {analysis_file}")
        console.print("Run 'testronaut analyze' first to generate an analysis file.")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Generating[/bold green] test plan from analysis: {analysis_file}")
    console.print(f"Output will be saved to: {output_file}")

    # This would call the actual generator in a real implementation
    # from testronaut.core.generator import generate_test_plan
    # generate_test_plan(analysis_file, output_file, model=ctx.parent.params.get("model"))

    console.print("[bold green]Test plan generation complete![/bold green]")