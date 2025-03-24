#!/usr/bin/env python
"""
AI-CLI-Testing - AI-assisted end-to-end CLI testing tool.

This module serves as the main entry point for the CLI application.
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich import print as rprint

from ai_cli_testing.cli import analyze, generate, verify, report

# Create Typer app
app = typer.Typer(
    name="ai-cli-test",
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
        Path("./ai-cli-test-output"),
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
    AI-CLI-Testing - AI-assisted end-to-end CLI testing tool.
    
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


# Add subcommands
app.add_typer(analyze.app, name="analyze", help="Analyze CLI tool and generate test plan")
app.add_typer(generate.app, name="generate", help="Execute tests and generate expected results")
app.add_typer(verify.app, name="verify", help="Execute tests and verify against expected results")
app.add_typer(report.app, name="report", help="Generate test report from results")


def print_banner():
    """Print application banner."""
    banner = """
    [bold blue]AI-CLI-Testing[/bold blue] - [italic]AI-assisted end-to-end CLI testing tool[/italic]
    Version 0.1.0
    Created by Ulrich Diedrichsen (uli@moinsen.dev)
    """
    rprint(banner)


if __name__ == "__main__":
    print_banner()
    app()
