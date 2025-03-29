"""
Database management commands.
"""

import logging
import os
import shutil
from typing import Optional

import typer
from rich.table import Table
from sqlalchemy import text
from sqlmodel import Session, SQLModel

from testronaut.cli.common import console, logger
from testronaut.config import Settings
from testronaut.models.base import DATABASE_URL, create_db_and_tables, engine
from testronaut.repositories.cli_tool import CLIToolRepository

# Create db app
db_app = typer.Typer(help="Database management commands")


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
def db_info(
    sql_debug: bool = typer.Option(False, "--sql-debug", help="Enable detailed SQL query logging"),
    create_tables: bool = typer.Option(
        True, "--create-tables/--no-create-tables", help="Create tables if they don't exist"
    ),
) -> None:
    """Display information about the database."""
    try:
        # Configure SQL logging if requested
        if sql_debug:
            from testronaut.models.base import configure_sql_logging

            configure_sql_logging(debug=True)
            logger.debug("SQL debugging enabled")

        # Create database tables if requested
        if create_tables:
            create_db_and_tables()

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
            else:
                console.print(
                    f"[yellow]Warning:[/yellow] Database file does not exist at {db_path}"
                )

    except Exception as e:
        console.print(f"[bold red]Error getting database info:[/bold red] {str(e)}")
        logger.exception("Failed to get database info")
        raise typer.Exit(1)


@db_app.command("browser")
def db_browser(
    tool_name: Optional[str] = typer.Argument(None, help="Name of the tool to browse"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging for the browser"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all log messages"),
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
        from testronaut.models.base import configure_sql_logging

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


@db_app.command("migrate")
def db_migrate(
    source: str = typer.Argument(
        "testronaut.db", help="Source database file (default: testronaut.db in current directory)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite if target exists"),
) -> None:
    """
    Migrate a database file to the configuration directory.

    This will copy the database file to the user's configuration directory
    and update the settings to use the new location.
    """
    settings = Settings()

    # Make sure config directory exists
    config_dir = os.path.expanduser(settings.config_dir)
    os.makedirs(config_dir, exist_ok=True)

    # Determine source and target paths
    source_path = os.path.abspath(source)
    if not os.path.exists(source_path):
        console.print(f"[bold red]Error:[/bold red] Source database {source_path} does not exist.")
        raise typer.Exit(1)

    # Get the target path from settings
    target_url = settings.database.get_resolved_url(config_dir)
    target_path = target_url.replace("sqlite:///", "")

    # Check if target already exists
    if os.path.exists(target_path) and not force:
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Target database {target_path} already exists. "
            f"Use --force to overwrite."
        )
        raise typer.Exit(1)

    try:
        # Create parent directories for target if they don't exist
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        # Copy the database file
        console.print(
            f"Copying database from [bold]{source_path}[/bold] to [bold]{target_path}[/bold]..."
        )
        shutil.copy2(source_path, target_path)

        # Initialize the database with the new URL
        from testronaut.models.base import initialize_db

        initialize_db(target_url)

        console.print("[bold green]Database successfully migrated![/bold green]")
        console.print(f"Database now located at: [bold]{target_path}[/bold]")

        # Ask if user wants to remove the old database
        if typer.confirm("Do you want to remove the old database file?"):
            os.remove(source_path)
            console.print(f"[bold]Removed old database file: {source_path}[/bold]")

    except Exception as e:
        console.print(f"[bold red]Error migrating database:[/bold red] {str(e)}")
        logger.exception(f"Failed to migrate database: {str(e)}")
        raise typer.Exit(1)
