"""
Commands for analyzing CLI tools.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import typer
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.tree import Tree

# Import from the new location
from testronaut.analyzers import (
    analyze_tool as run_analysis,
)
from testronaut.analyzers import (
    display_token_usage,
    save_user_preferences,
)
from testronaut.cli.common import console, logger
from testronaut.factory import registry
from testronaut.models.base import configure_sql_logging, create_db_and_tables
from testronaut.repositories.cli_tool import CLIToolRepository

# Create analyze app
analyze_app = typer.Typer(help="Analyze CLI tools and generate test plans")


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
    sql_debug: bool = typer.Option(False, "--sql-debug", help="Enable detailed SQL query logging"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode for selecting commands to analyze"
    ),
    max_commands: Optional[int] = typer.Option(
        None,
        "--max-commands",
        help="Maximum number of commands to analyze (default: auto-determined)",
    ),
) -> int:
    """Analyze a CLI tool and generate a test plan."""
    console.print(f"Analyzing tool: [bold]{tool_path}[/bold]")

    # Configure verbose logging if requested
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure SQL logging if requested
    if sql_debug:
        configure_sql_logging(debug=True)
        logger.debug("SQL debugging enabled")

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
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Start a task
            task = progress.add_task(f"Analyzing {tool_name}...", total=None)

            # Call the analyze_tool function from the CLI module
            cli_tool = run_analysis(
                tool_path=tool_path,
                output=output_path,
                deep=deep,
                enhanced=enhanced,
                verbose=verbose,
                sql_debug=sql_debug,
                interactive=interactive,
                max_commands=max_commands,
            )

            # Complete the task
            progress.update(task, description="Analysis complete!", completed=True)

        # Export semantic analysis for LLM-enhanced analyzer
        semantic_analysis = None
        if enhanced or deep:
            # Create semantic analysis directory
            semantic_path = output_path / "semantic"
            semantic_path.mkdir(exist_ok=True)

            # Check for analyzer's metadata
            if hasattr(analyzer, "metadata"):
                analyzer_metadata = getattr(analyzer, "metadata", {})

                # Handle metadata properly
                if hasattr(analyzer_metadata, "get") and callable(analyzer_metadata.get):
                    semantic_analysis = analyzer_metadata.get("semantic_analysis", {})
                elif hasattr(analyzer_metadata, "__dict__"):
                    analyzer_metadata_dict = vars(analyzer_metadata)
                    semantic_analysis = analyzer_metadata_dict.get("semantic_analysis", {})

            # Get commands from cli_tool instead of analyzer
            if semantic_analysis and hasattr(cli_tool, "commands"):
                for cmd in cli_tool.commands:
                    if hasattr(cmd, "id") and cmd.id in semantic_analysis:
                        semantic_file = semantic_path / f"{cmd.name}.json"
                        with open(semantic_file, "w") as f:
                            json.dump(semantic_analysis[cmd.id], f, indent=2)

        # Save to database if requested
        if save_to_db:
            progress_status = console.status(
                "[bold blue]Saving analysis results to database...[/bold blue]"
            )
            progress_status.start()

            try:
                # Create a repository
                repository = CLIToolRepository()

                # Save the analysis results using the cli_tool from the run_analysis function
                repository.save_analysis_results(cli_tool, semantic_analysis)

                progress_status.stop()
                console.print("[bold green]Analysis results saved to database.[/bold green]")
            except Exception as db_error:
                progress_status.stop()
                console.print(f"[bold red]Error saving to database:[/bold red] {str(db_error)}")
                if verbose:
                    import traceback

                    console.print(f"[red]{traceback.format_exc()}[/red]")
                logger.exception(f"Failed to save to database: {str(db_error)}")

        # Get command count from cli_tool
        command_count = len(cli_tool.commands) if hasattr(cli_tool, "commands") else 0

        # Report findings
        console.print(
            Panel.fit(
                f"[bold green]Analysis of {tool_name} completed![/bold green]\n"
                f"Found {command_count} top-level commands.\n"
                f"Results saved to: {output_path}"
                + ("\nResults saved to database." if save_to_db else "")
            )
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

        # Save user preferences for this tool
        save_user_preferences(tool_name, enhanced)

        return 0
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[red]{traceback.format_exc()}[/red]")
        logger.exception(f"Failed to analyze tool: {str(e)}")
        return 1


# Legacy command for compatibility with main.py
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
    cli_tool = run_analysis(
        tool_path=tool_path,
        output=output,
        deep=(depth > 1),
        enhanced=enhanced,
        interactive=interactive,
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


@analyze_app.command("list-db")
def list_analyzed_tools() -> int:
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


@analyze_app.command("get-db")
def get_analyzed_tool(
    tool_name: str = typer.Argument(..., help="Name of the CLI tool to retrieve"),
) -> None:
    """
    Retrieve a specific CLI tool from the database and display details.
    """
    try:
        create_db_and_tables()

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
        def add_commands_to_tree(commands, parent) -> None:
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
    sql_debug: bool = typer.Option(False, "--sql-debug", help="Enable detailed SQL query logging"),
) -> None:
    """
    Launch an interactive database browser for exploring analyzed CLI tools.
    """
    try:
        # Configure logging based on the quiet and debug flags
        if debug:
            console.print("Debug mode enabled. Some log messages will be shown.")
            # Only adjust root logger if debug is enabled
            logging.getLogger().setLevel(logging.INFO)

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
            logging.getLogger("testronaut").setLevel(logging.ERROR)

        # Configure SQL logging if requested
        configure_sql_logging(debug=sql_debug)

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
