# testronaut.cli package

"""
Command-Line Interface for Testronaut.

This module defines the CLI commands and options for the Testronaut application.
"""

import json
import logging
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
from sqlalchemy import func, select, text
from sqlmodel import Session, SQLModel

from testronaut import __version__
from testronaut.config import Settings, get_config_path, initialize_config, update_config
from testronaut.factory import registry
from testronaut.models.base import DATABASE_URL, create_db_and_tables, engine
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
db_app = typer.Typer(help="Database management commands")

# Add sub-commands to main app
app.add_typer(config_app, name="config")
app.add_typer(analyze_app, name="analyze")
app.add_typer(execute_app, name="execute")
app.add_typer(verify_app, name="verify")
app.add_typer(db_app, name="db")


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
    """
    Retrieve a specific CLI tool from the database and display details.
    """
    try:
        create_db_and_tables()

        console = Console()
        repo = CLIToolRepository()

        # Use get_by_name which already handles eager loading of relationships
        tool = repo.get_by_name(tool_name)

        if not tool:
            console.print(f"[red]CLI Tool '{tool_name}' not found in the database.[/red]")
            raise typer.Exit(1)

        # Print tool information
        console.print(f"[bold green]CLI Tool:[/bold green] {tool.name}")
        if tool.version:
            console.print(f"[bold]Version:[/bold] {tool.version}")
        console.print(f"[bold]Analyzed At:[/bold] {tool.created_at}")
        console.print(f"[bold]Total Commands:[/bold] {len(tool.commands)}")

        # Create tree for commands
        root = Tree(f"[bold]{tool.name}[/bold] Commands")

        # Build tree of commands
        def add_commands_to_tree(commands, parent):
            for cmd in commands:
                # Create command node
                cmd_node = parent.add(
                    f"[cyan]{cmd.name}[/cyan]" + (f": {cmd.description}" if cmd.description else "")
                )

                # Add options
                if cmd.options:
                    opt_node = cmd_node.add("[yellow]Options[/yellow]")
                    for opt in cmd.options:
                        name = opt.name
                        if opt.short_form:
                            name = f"{opt.short_form}, {name}"
                        opt_node.add(
                            f"[yellow]{name}[/yellow]"
                            + (f": {opt.description}" if opt.description else "")
                        )

                # Add arguments
                if cmd.arguments:
                    arg_node = cmd_node.add("[green]Arguments[/green]")
                    for arg in cmd.arguments:
                        arg_node.add(
                            f"[green]{arg.name}[/green]"
                            + (f": {arg.description}" if arg.description else "")
                        )

                # Recursively add subcommands
                if cmd.subcommands:
                    add_commands_to_tree(cmd.subcommands, cmd_node)

        # Build the command tree
        add_commands_to_tree(tool.commands, root)

        # Print the command tree
        console.print(root)

    except Exception as e:
        console = Console()
        console.print(f"[red]Error retrieving tool:[/red] {str(e)}")
        logger.exception(f"Error retrieving tool: {str(e)}")
        raise typer.Exit(1)


@analyze_app.command()
def browser(
    tool_name: Optional[str] = typer.Option(
        None, "--tool", "-t", help="Load a specific tool by name"
    ),
    quiet: bool = typer.Option(True, "--quiet/--no-quiet", "-q", help="Silence all logging output"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
) -> None:
    """
    Launch an interactive database browser for exploring analyzed CLI tools.
    """
    from rich.console import Console

    console = Console()

    try:
        # Configure logging based on the quiet and debug flags
        if debug:
            console.print("Debug mode enabled. Some log messages will be shown.")
            # Only adjust root logger if debug is enabled
            logging.getLogger().setLevel(logging.INFO)
            # Always set SQLAlchemy to WARNING to avoid overwhelming output
            logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
            # Set testronaut logger to DEBUG for detailed info
            testronaut_logger = logging.getLogger("testronaut")
            testronaut_logger.setLevel(logging.DEBUG)
            # Specifically set the UI logger to DEBUG
            ui_logger = logging.getLogger("testronaut.ui")
            ui_logger.setLevel(logging.DEBUG)
            # Add a console handler for direct output during debugging
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            ui_logger.addHandler(console_handler)
            ui_logger.debug("UI Debug logging enabled")
        elif quiet:
            # In quiet mode, suppress all logging
            logging.getLogger().setLevel(logging.ERROR)
            logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
            logging.getLogger("testronaut").setLevel(logging.ERROR)

        # Initialize database
        create_db_and_tables()

        tool_id = None
        if tool_name:
            # If a tool name was provided, find its ID
            repo = CLIToolRepository()
            tool = repo.get_by_name(tool_name)
            if tool:
                tool_id = str(tool.id)
                console.print(f"Loading tool: [bold]{tool_name}[/bold]")
            else:
                console.print(
                    f"[yellow]Warning:[/yellow] Tool '{tool_name}' not found in database."
                )

        # Import here to avoid circular imports
        from testronaut.ui.browser import run_browser

        # Run the browser (this will take over the terminal)
        run_browser(tool_id)

    except Exception as e:
        console.print(f"[red]Error launching browser: {str(e)}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1)


@db_app.command("reset")
def db_reset(
    force: bool = typer.Option(False, "--force", "-f", help="Force reset without confirmation"),
) -> None:
    """Reset the database by dropping and recreating all tables."""
    if not force:
        confirm = typer.confirm("This will delete all data in the database. Are you sure?")
        if not confirm:
            console.print("[yellow]Database reset cancelled.[/yellow]")
            return

    try:
        # Drop all tables
        SQLModel.metadata.drop_all(engine)
        console.print("[green]Successfully dropped all tables.[/green]")

        # Recreate tables
        create_db_and_tables()
        console.print("[green]Successfully recreated all tables.[/green]")

        console.print("[bold green]Database reset complete![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error resetting database:[/bold red] {str(e)}")
        logger.exception("Failed to reset database")
        raise typer.Exit(1)


@db_app.command("info")
def db_info() -> None:
    """Display information about the database."""
    try:
        with Session(engine) as session:
            # Get table information
            tables = SQLModel.metadata.tables
            console.print("\n[bold]Database Tables:[/bold]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Table Name")
            table.add_column("Row Count")

            for table_name in tables:
                # Get row count for each table using text
                result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                count = result if result is not None else 0
                table.add_row(str(table_name), str(count))

            console.print(table)

            # Show database file location
            db_path = DATABASE_URL.replace("sqlite:///", "")
            console.print(f"\n[bold]Database Location:[/bold] {db_path}")

            # Show database size
            if os.path.exists(db_path):
                size = os.path.getsize(db_path)
                console.print(f"[bold]Database Size:[/bold] {size / 1024:.2f} KB")

    except Exception as e:
        console.print(f"[bold red]Error getting database info:[/bold red] {str(e)}")
        logger.exception("Failed to get database info")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
