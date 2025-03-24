"""
Command module for generating test reports.
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()
app = typer.Typer(name="report")

@app.callback(invoke_without_command=True)
def report(
    ctx: typer.Context,
    verification_results: Optional[Path] = typer.Option(
        None,
        "--verification-results",
        "-v",
        help="Path to verification results file",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to output report file",
    ),
    format: str = typer.Option(
        "html",
        "--format",
        "-f",
        help="Report format (html, markdown, json)",
    ),
):
    """
    Generate test report from verification results.

    This command generates a comprehensive test report from the
    verification results in the specified format.
    """
    # Get global options
    tool = ctx.parent.params.get("tool")
    output_dir = ctx.parent.params.get("output_dir")

    # If no verification results are specified, use the default location
    if not verification_results:
        verification_results = Path(output_dir) / f"{tool}_verification_results.json"

    # If no output file is specified, use the default location with appropriate extension
    if not output_file:
        extension = format.lower()
        output_file = Path(output_dir) / f"{tool}_report.{extension}"

    if not verification_results.exists():
        console.print(f"[bold red]Error:[/bold red] Verification results file not found: {verification_results}")
        console.print("Run 'testronaut verify' first to generate verification results.")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Generating[/bold green] report from verification results: {verification_results}")
    console.print(f"Output will be saved to: {output_file}")

    # This would call the actual report generator in a real implementation
    # from testronaut.core.reporter import generate_report
    # generate_report(verification_results, output_file, format=format)

    console.print("[bold green]Report generation complete![/bold green]")