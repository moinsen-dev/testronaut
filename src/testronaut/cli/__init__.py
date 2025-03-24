# testronaut.cli package

"""
Command-Line Interface for Testronaut.

This module defines the CLI commands and options for the Testronaut application.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Tuple, Union

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from testronaut import __version__
from testronaut.config import Settings, get_config_path, initialize_config, update_config
from testronaut.factory import registry
from testronaut.utils.errors import CommandExecutionError, ValidationError
from testronaut.utils.logging import configure_logging, get_logger

# Initialize console and logger
console = Console()
logger = get_logger(__name__)

# Create main app
app = typer.Typer(
    name="testronaut",
    help="Automated CLI Testing Framework",
    no_args_is_help=True,
)

# Create sub-commands
config_app = typer.Typer(help="Configuration management commands")
analyze_app = typer.Typer(help="Analyze CLI tools and generate test plans")
execute_app = typer.Typer(help="Execute tests from test plans")
verify_app = typer.Typer(help="Verify test results")

# Add sub-commands to main app
app.add_typer(config_app, name="config")
app.add_typer(analyze_app, name="analyze")
app.add_typer(execute_app, name="execute")
app.add_typer(verify_app, name="verify")


def version_callback(value: bool):
    """Print version information and exit."""
    if value:
        console.print(f"[bold green]Testronaut[/bold green] version: [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, help="Show version and exit"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Log to file"),
):
    """
    Testronaut: Automated CLI Testing Framework.

    Generate, execute, and verify tests for command-line tools using
    containerized environments and AI-assisted validation.
    """
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(level=log_level, log_file=log_file)


@config_app.command("init")
def config_init(
    config_dir: Optional[str] = typer.Option(
        None, "--config-dir", "-c", help="Configuration directory path"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force overwrite existing configuration"
    ),
):
    """Initialize Testronaut configuration."""
    try:
        result = initialize_config(config_dir, force=force)
        console.print(f"Configuration initialized at: [bold green]{result}[/bold green]")

        # Display config path information
        config_path = get_config_path()
        console.print(f"Config path set to: [bold]{config_path}[/bold]")

        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logger.exception("Failed to initialize configuration")
        return 1


@config_app.command("show")
def config_show():
    """Show current configuration."""
    try:
        settings = Settings()

        # Create a rich table for display
        table = Table(title="Testronaut Configuration", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Add settings to table
        table.add_row("App Name", settings.app_name)
        table.add_row("Debug Mode", str(settings.debug))
        table.add_row("Config Path", str(settings.config_path))

        # Database settings
        table.add_row("Database URL", str(settings.database.url))

        # Logging settings
        table.add_row("Log Level", settings.logging.level)
        table.add_row("Log Format", settings.logging.format)

        # LLM settings
        table.add_row("LLM Provider", settings.llm.provider)

        # Display available attributes instead of hardcoded ones that might not exist
        # Display LLM model if available
        if hasattr(settings.llm, "model_name"):
            table.add_row("LLM Model", settings.llm.model_name)

        # Display execution settings if available
        if hasattr(settings, "execution"):
            if hasattr(settings.execution, "default_image"):
                table.add_row("Default Image", settings.execution.default_image)
            if hasattr(settings.execution, "timeout_seconds"):
                table.add_row("Timeout", str(settings.execution.timeout_seconds))

        console.print(table)
        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logger.exception("Failed to show configuration")
        return 1


@analyze_app.command("tool")
def analyze_tool(
    tool_path: str = typer.Argument(..., help="Path to the CLI tool executable"),
    output_dir: str = typer.Option(
        "./testronaut_analysis", "--output", "-o", help="Directory to save analysis results"
    ),
    deep: bool = typer.Option(
        False, "--deep", "-d", help="Perform deep analysis (longer but more thorough)"
    ),
):
    """Analyze a CLI tool and generate a test plan."""
    console.print(f"Analyzing tool: [bold]{tool_path}[/bold]")

    try:
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get the analyzer factory
        analyzer_factory = registry.get_factory("cli_analyzer")
        if analyzer_factory is None:
            raise ValueError("CLI Analyzer factory not registered")

        # Create an analyzer (use LLM-enhanced if deep analysis requested)
        analyzer_type = "llm_enhanced" if deep else "standard"
        analyzer = analyzer_factory.create(analyzer_type)

        console.print(f"Using [bold]{analyzer_type}[/bold] analyzer for analysis")

        # Extract tool name from path
        tool_name = os.path.basename(tool_path)

        # Start the analysis
        with console.status(f"Analyzing {tool_name}...", spinner="dots"):
            cli_tool = analyzer.analyze_cli_tool(tool_path)

        # Report findings
        console.print(f"\nAnalysis of [bold]{tool_name}[/bold] completed")
        console.print(f"Found [bold]{len(cli_tool.commands)}[/bold] commands")

        # Save analysis results to JSON file
        output_file = output_path / f"{tool_name}_analysis.json"

        # Convert model to dictionary
        tool_dict = cli_tool.dict(exclude={"id"})

        # Replace command and option IDs with more readable identifiers
        for i, cmd in enumerate(tool_dict.get("commands", [])):
            cmd_id = cmd.pop("id", None)
            cmd["index"] = i

            # Process options
            for j, opt in enumerate(cmd.get("options", [])):
                opt_id = opt.pop("id", None)
                opt["index"] = j

            # Process arguments
            for j, arg in enumerate(cmd.get("arguments", [])):
                arg_id = arg.pop("id", None)
                arg["index"] = j

            # Process examples
            for j, ex in enumerate(cmd.get("examples", [])):
                ex_id = ex.pop("id", None)
                ex["index"] = j

        # Write to file
        with open(output_file, "w") as f:
            # Create a custom JSON encoder to handle datetime objects
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return super().default(obj)

            json.dump(tool_dict, f, indent=2, cls=DateTimeEncoder)

        console.print(f"Analysis results saved to: [bold]{output_file}[/bold]")
        return 0

    except CommandExecutionError as e:
        console.print(f"[bold red]Error executing command:[/bold red] {str(e)}")
        return 1
    except ValidationError as e:
        console.print(f"[bold red]Validation error:[/bold red] {str(e)}")
        return 1
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {str(e)}")
        logger.exception(f"Unexpected error during analysis: {str(e)}")
        return 1


@execute_app.command("plan")
def execute_plan(
    plan_path: str = typer.Argument(..., help="Path to the test plan file"),
    output_dir: str = typer.Option(
        "./testronaut_results", "--output", "-o", help="Directory to save test results"
    ),
):
    """Execute tests from a test plan."""
    console.print(f"Executing test plan: [bold]{plan_path}[/bold]")
    console.print("[yellow]This functionality is still being implemented[/yellow]")
    return 0


@verify_app.command("results")
def verify_results(
    results_dir: str = typer.Argument(..., help="Directory with test results"),
    report_format: str = typer.Option(
        "text", "--format", "-f", help="Report format (text, json, html)"
    ),
):
    """Verify test results and generate a report."""
    console.print(f"Verifying results in: [bold]{results_dir}[/bold]")
    console.print("[yellow]This functionality is still being implemented[/yellow]")
    return 0


if __name__ == "__main__":
    app()
