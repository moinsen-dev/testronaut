"""
Command-Line Interface for Testronaut.

This module defines the CLI commands and options for the Testronaut application.
"""

from typing import Optional

import typer

# Import command groups
from testronaut.cli.commands.analyze_commands import analyze_app
from testronaut.cli.commands.config import config_app
from testronaut.cli.commands.db import db_app
from testronaut.cli.commands.execute import execute_app
from testronaut.cli.commands.verify import verify_app
from testronaut.cli.common import console, logger, version_callback
from testronaut.models.base import configure_sql_logging
from testronaut.utils.logging import configure_logging

# Create main app
app = typer.Typer(
    name="testronaut",
    help="Automated CLI Testing Framework",
    no_args_is_help=True,
)

# Add sub-commands to main app
app.add_typer(config_app, name="config")
app.add_typer(analyze_app, name="analyze")
app.add_typer(execute_app, name="execute")
app.add_typer(verify_app, name="verify")
app.add_typer(db_app, name="db")


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, help="Show version and exit"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Log to file"),
    sql_debug: bool = typer.Option(False, "--sql-debug", help="Enable detailed SQL query logging"),
) -> None:
    """
    Testronaut: Automated CLI Testing Framework.

    Generate, execute, and verify tests for command-line tools using
    containerized environments and AI-assisted validation.
    """
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    configure_logging(level=log_level, log_file=log_file)

    # Configure SQL logging if requested
    configure_sql_logging(debug=sql_debug)


if __name__ == "__main__":
    app()
