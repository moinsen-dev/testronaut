#!/usr/bin/env python
"""
Testronaut - AI-assisted end-to-end CLI testing tool.

This module serves as the main entry point for the CLI application.
"""

from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console

# Import the specific app instances from the command modules
from testronaut.cli.commands.analyze_commands import analyze_app
from testronaut.cli.commands.generate import app as generate_app # Renaming import
from testronaut.cli.commands.report import app as report_app # Renaming import
from testronaut.cli.commands.verify import verify_app

# Create Typer app
app = typer.Typer(
    name="testronaut",
    help="AI-assisted end-to-end CLI testing tool",
    add_completion=True,
)

# Global options
console = Console()


@app.callback()
def callback(
    ctx: typer.Context,
    tool: Optional[str] = typer.Option(
        None,
        "--tool",
        "-t",
        help="CLI tool to test (name or path)",
    ),
    install_cmd: Optional[str] = typer.Option(
        None,
        "--install-cmd",
        "-i",
        help="Command to install the tool",
    ),
    model: str = typer.Option(
        "openai",
        "--model",
        "-m",
        help="LLM to use (openai, anthropic, or local model path)",
    ),
    output_dir: Path = typer.Option(
        Path("./testronaut-output"),
        "--output-dir",
        "-o",
        help="Directory to store results",
    ),
    docker_image: Optional[str] = typer.Option(
        None,
        "--docker-image",
        "-d",
        help="Custom Docker image to use",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
):
    """
    Testronaut - AI-assisted end-to-end CLI testing tool.

    This tool uses AI to analyze CLI applications, generate test plans,
    execute tests in isolated Docker containers, and verify results.
    """
    # Store global options in context
    ctx.obj = {
        "tool": tool,
        "install_cmd": install_cmd,
        "model": model,
        "output_dir": output_dir,
        "docker_image": docker_image,
        "verbose": verbose,
    }

    # Create output directory if it doesn't exist
    if not output_dir.exists():
        output_dir.mkdir(parents=True)


# Add subcommands using the imported app instances
app.add_typer(analyze_app, name="analyze", help="Analyze CLI tool and generate test plan")
app.add_typer(generate_app, name="generate", help="Execute tests and generate expected results")
app.add_typer(verify_app, name="verify", help="Execute tests and verify against expected results")
app.add_typer(report_app, name="report", help="Generate test report from results")


def print_banner():
    """Print application banner."""
    banner = """
    [bold blue]Testronaut[/bold blue] - [italic]AI-assisted end-to-end CLI testing tool[/italic]
    Version 0.4.0
    Created by Ulrich Diedrichsen (uli@moinsen.dev)
    """
    rprint(banner)


if __name__ == "__main__":
    print_banner()
    app()
