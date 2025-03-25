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
from typing import Any, Dict, List, Optional, Tuple

import structlog
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from testronaut import __version__
from testronaut.config import Settings, get_config_path, initialize_config, update_config
from testronaut.factory import registry
from testronaut.models.base import create_db_and_tables
from testronaut.repositories.cli_tool import CLIToolRepository
from testronaut.utils.errors import CommandExecutionError, ValidationError
from testronaut.utils.llm import LLMService
from testronaut.utils.logging import configure_logging, get_logger
from testronaut.utils.text_utils import clean_help_text

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

        # Create a rich table
        table = Table(title="Testronaut Configuration", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        # Add general settings
        table.add_row("App Name", settings.app_name)
        table.add_row("Debug Mode", str(settings.debug))
        table.add_row("Config Path", str(settings.config_path))

        # Add database settings
        table.add_row("Database URL", settings.database.url)

        # Add logging settings
        table.add_row("Log Level", settings.logging.level)
        table.add_row("Log Format", settings.logging.format)

        # Add LLM settings
        table.add_row("LLM Provider", settings.llm.provider)

        # Get the current provider settings
        provider_settings = settings.llm.current_provider_settings
        models = provider_settings.get("models", {})

        # Add model information if available
        if "default" in models:
            table.add_row("LLM Default Model", models["default"])
        else:
            table.add_row("LLM Model", settings.llm.model)

        # Show API key status (but not the actual key)
        api_key_status = "Configured" if provider_settings.get("api_key") else "Not configured"
        table.add_row("LLM API Key", api_key_status)

        # Show task-specific models if configured
        for task, model in models.items():
            if task != "default":
                table.add_row(f"LLM {task.capitalize()} Model", model)

        # Add execution settings if they exist and have values
        if hasattr(settings, "execution"):
            execution = settings.execution
            if hasattr(execution, "docker_image"):
                table.add_row("Default Docker Image", execution.docker_image)
            if hasattr(execution, "timeout"):
                table.add_row("Default Timeout", f"{execution.timeout} seconds")

        # Print the table
        console.print(table)

        return 0
    except Exception as e:
        console.print(f"[bold red]Error showing configuration:[/bold red] {str(e)}")
        logger.exception(f"Error showing configuration: {str(e)}")
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
    enhanced: bool = typer.Option(
        False, "--enhanced", "-e", help="Use LLM-enhanced analyzer (more detailed analysis)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed progress logs during analysis"
    ),
    save_to_db: bool = typer.Option(
        False, "--save-to-db", "-s", help="Save analysis results to database"
    ),
):
    """Analyze a CLI tool and generate a test plan."""
    console.print(f"Analyzing tool: [bold]{tool_path}[/bold]")

    # Configure verbose logging if requested
    if verbose:
        configure_logging(level="DEBUG")
        logger.debug("Verbose logging enabled")

    try:
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize database if saving to DB
        if save_to_db:
            logger.debug("Initializing database")
            create_db_and_tables()

        # Get the analyzer factory
        analyzer_factory = registry.get_factory("cli_analyzer")
        if analyzer_factory is None:
            raise ValueError("CLI Analyzer factory not registered")

        # Create an analyzer
        analyzer_type = "standard"
        if enhanced or deep:  # If either enhanced or deep is specified, use LLM-enhanced
            analyzer_type = "llm_enhanced"

        analyzer = analyzer_factory.create(analyzer_type)

        console.print(f"Using [bold]{analyzer_type}[/bold] analyzer for analysis")

        # Extract tool name from path
        tool_name = os.path.basename(tool_path)

        # Create a detailed progress display
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Start a task
            task = progress.add_task(f"Analyzing {tool_name}...", total=None)

            # Run the analysis
            cli_tool = analyzer.analyze_cli_tool(tool_path)

            # Update task for export phase
            progress.update(task, description="Exporting analysis results...")

            # Save analysis results to JSON file
            output_file = output_path / f"{tool_name}_analysis.json"

            # Convert model to dictionary
            tool_dict = cli_tool.dict(exclude={"id"})

            # Clean up help text for more compact and readable output
            if "help_text" in tool_dict and tool_dict["help_text"]:
                cleaned_text = clean_help_text(tool_dict["help_text"])
                if cleaned_text is not None:
                    tool_dict["help_text"] = cleaned_text

            # Add commands as a top-level list
            commands_list = []
            for cmd in cli_tool.commands:
                cmd_dict = cmd.dict(exclude={"cli_tool", "cli_tool_id"})

                # Clean command help text
                if "help_text" in cmd_dict and cmd_dict["help_text"]:
                    cleaned_text = clean_help_text(cmd_dict["help_text"])
                    if cleaned_text is not None:
                        cmd_dict["help_text"] = cleaned_text

                # Process options
                options_list = []
                for opt in cmd.options:
                    opt_dict = opt.dict(exclude={"command", "command_id"})
                    options_list.append(opt_dict)
                cmd_dict["options"] = options_list

                # Process arguments
                args_list = []
                for arg in cmd.arguments:
                    arg_dict = arg.dict(exclude={"command", "command_id"})
                    args_list.append(arg_dict)
                cmd_dict["arguments"] = args_list

                # Process examples
                examples_list = []
                for ex in cmd.examples:
                    ex_dict = ex.dict(exclude={"command", "command_id"})
                    examples_list.append(ex_dict)
                cmd_dict["examples"] = examples_list

                commands_list.append(cmd_dict)

            tool_dict["commands"] = commands_list

            # Write to file
            with open(output_file, "w") as f:
                # Create a custom JSON encoder to handle datetime objects
                class DateTimeEncoder(json.JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        return super().default(obj)

                json.dump(tool_dict, f, indent=2, cls=DateTimeEncoder)

            # Complete the task
            progress.update(task, description="Analysis complete!", completed=True)

        # Export semantic analysis for LLM-enhanced analyzer
        semantic_analysis = None
        if enhanced or deep:
            # Create semantic analysis directory
            semantic_path = output_path / "semantic"
            semantic_path.mkdir(exist_ok=True)

            # Save semantic analysis for each command
            if hasattr(cli_tool, "metadata") and getattr(cli_tool, "metadata", {}).get(
                "semantic_analysis"
            ):
                console.print("\nExporting semantic analysis...")

                # Extract semantic analysis
                semantic_analysis = cli_tool.metadata["semantic_analysis"]

                # Save for each command
                for cmd in cli_tool.commands:
                    if cmd.id in semantic_analysis:
                        semantic_file = semantic_path / f"{cmd.name}.json"
                        with open(semantic_file, "w") as f:
                            json.dump(semantic_analysis[cmd.id], f, indent=2)

        # Save to database if requested
        if save_to_db:
            progress = console.status(
                "[bold blue]Saving analysis results to database...[/bold blue]"
            )
            progress.start()

            try:
                # Create a repository
                repository = CLIToolRepository()

                # Save the analysis results
                repository.save_analysis_results(cli_tool, semantic_analysis)

                progress.stop()
                console.print("[bold green]Analysis results saved to database.[/bold green]")
            except Exception as db_error:
                progress.stop()
                console.print(f"[bold red]Error saving to database:[/bold red] {str(db_error)}")
                if verbose:
                    import traceback

                    console.print(f"[red]{traceback.format_exc()}[/red]")
                logger.exception(f"Failed to save to database: {str(db_error)}")

        # Report findings
        console.print(
            Panel.fit(
                f"[bold green]Analysis of {tool_name} completed![/bold green]\n"
                f"Found {len(cli_tool.commands)} top-level commands.\n"
                f"Results saved to: {output_file}"
                + ("\nResults saved to database." if save_to_db else "")
            )
        )

        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[red]{traceback.format_exc()}[/red]")
        logger.exception(f"Failed to analyze tool: {str(e)}")
        return 1


@analyze_app.command("list-db")
def list_analyzed_tools():
    """List CLI tools that have been analyzed and stored in the database."""
    try:
        # Initialize database
        create_db_and_tables()

        # Create repository
        repository = CLIToolRepository()

        # Get all tools
        tools = repository.list()

        if not tools:
            console.print("[yellow]No analyzed tools found in the database.[/yellow]")
            return 0

        # Create a table to display tool information
        from rich.table import Table

        table = Table(title="Analyzed CLI Tools")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Commands", style="blue")
        table.add_column("Analyzed At", style="magenta")

        for tool in tools:
            table.add_row(
                tool.name,
                tool.version or "Unknown",
                str(len(tool.commands)),
                tool.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[bold red]Error listing tools:[/bold red] {str(e)}")
        logger.exception(f"Error listing tools: {str(e)}")
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


@config_app.command("test-llm")
def test_llm():
    """Test the LLM service configuration."""
    try:
        # Create the LLM service
        service = LLMService()

        # Get provider information
        provider_name = service.provider_name
        model = service.settings.llm.get_model_for_task("chat")

        console.print(
            f"Testing LLM service with provider: [bold]{provider_name}[/bold], model: [bold]{model}[/bold]"
        )

        # Generate a simple response
        prompt = (
            "Generate a short test message to verify that the LLM service is working correctly."
        )

        with console.status("Generating response...", spinner="dots"):
            response = service.generate_text(prompt, max_tokens=100)

        # Display the response
        console.print(
            "\n[bold green]═══════════════════════ LLM Response ═══════════════════════[/bold green]"
        )
        console.print(response)
        console.print(f"[dim]Provider: {provider_name}, Model: {model}[/dim]")
        console.print(
            "[bold green]═══════════════════════════════════════════════════════════[/bold green]\n"
        )

        console.print("[bold green]LLM service test successful![/bold green]")
        return 0

    except Exception as e:
        console.print(f"[bold red]Error testing LLM service:[/bold red] {str(e)}")
        logger.exception(f"Error testing LLM service: {str(e)}")
        return 1


@analyze_app.command("get-db")
def get_analyzed_tool(
    tool_name: str = typer.Argument(..., help="Name of the CLI tool to retrieve"),
):
    """Retrieve a specific CLI tool from the database and display its details."""
    try:
        # Initialize database
        create_db_and_tables()

        # Create console for output
        console = Console()

        # Create repository and get tool
        repo = CLIToolRepository()
        tool = repo.get_by_name(tool_name)

        if not tool:
            console.print(f"[yellow]Tool '{tool_name}' not found in the database.[/yellow]")
            return 1

        console.print(f"[bold green]CLI Tool:[/bold green] {tool.name}")
        console.print(f"[bold green]Version:[/bold green] {tool.version}")
        console.print(f"[bold green]Analyzed At:[/bold green] {tool.created_at}")
        console.print(f"[bold green]Total Commands:[/bold green] {len(tool.commands)}")
        console.print()

        # Build a rich tree to display the commands
        root = Tree(f"[bold blue]{tool.name}[/bold blue]")

        # Function to recursively add commands to the tree
        def add_commands_to_tree(commands, parent_node):
            for cmd in commands:
                # Create a node for the command
                cmd_node = parent_node.add(
                    f"[bold cyan]{cmd.name}[/bold cyan]: {cmd.description or ''}"
                )

                # Add options if any
                if cmd.options:
                    options_node = cmd_node.add("[bold yellow]Options:[/bold yellow]")
                    for opt in cmd.options:
                        options_node.add(f"{opt.name}: {opt.description or ''}")

                # Add arguments if any
                if cmd.arguments:
                    args_node = cmd_node.add("[bold magenta]Arguments:[/bold magenta]")
                    for arg in cmd.arguments:
                        args_node.add(f"{arg.name}: {arg.description or ''}")

                # Recursively add subcommands
                if cmd.subcommands:
                    add_commands_to_tree(cmd.subcommands, cmd_node)

        # Add top-level commands to the tree
        add_commands_to_tree(tool.commands, root)

        # Display the tree
        console.print(root)

        return 0
    except Exception as e:
        console = Console()
        console.print(f"[bold red]Error retrieving tool:[/bold red] {str(e)}")
        logger.exception(f"Error retrieving tool: {str(e)}")
        return 1


if __name__ == "__main__":
    app()
