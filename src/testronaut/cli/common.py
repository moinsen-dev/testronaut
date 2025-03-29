"""
Common utilities and variables used across CLI commands.
"""

import typer
from rich.console import Console

from testronaut import __version__
from testronaut.utils.logging import get_logger

# Initialize console and logger
console = Console()
logger = get_logger(__name__)


def version_callback(value: bool) -> None:
    """Print version information and exit."""
    if value:
        console.print(f"[bold green]Testronaut[/bold green] version: [bold]{__version__}[/bold]")
        raise typer.Exit()
