"""
Commands for executing test plans.
"""

import typer

from testronaut.cli.common import console

# Create execute app
execute_app = typer.Typer(help="Execute tests from test plans")


@execute_app.command("plan")
def execute_plan(
    plan_path: str = typer.Argument(..., help="Path to the test plan file"),
    output_dir: str = typer.Option(
        "./testronaut_results", "--output", "-o", help="Directory to save test results"
    ),
) -> int:
    """Execute tests from a test plan."""
    console.print(f"Executing test plan: [bold]{plan_path}[/bold]")
    console.print("[yellow]This functionality is still being implemented[/yellow]")
    return 0
