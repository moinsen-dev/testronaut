"""
Display utilities for analyzers.

This module provides functions for displaying analyzer results.
"""

from rich.console import Console
from rich.table import Table

from testronaut.models.cli_tool import TokenUsage

# Initialize console
console = Console()


def display_token_usage(token_usage: TokenUsage) -> None:
    """
    Display token usage information.

    Args:
        token_usage: The token usage information.
    """
    console.print("\n[bold]Token Usage Information:[/bold]")

    # Create a table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    # Add rows
    table.add_row("Total API Calls", str(token_usage.api_calls))
    table.add_row("Total Tokens", str(token_usage.total_tokens))
    table.add_row("Prompt Tokens", str(token_usage.prompt_tokens))
    table.add_row("Completion Tokens", str(token_usage.completion_tokens))
    table.add_row("Estimated Cost", f"${token_usage.estimated_cost:.6f}")

    # Models used
    if token_usage.models_used:
        model_str = ", ".join(
            f"{model}: {count} tokens" for model, count in token_usage.models_used.items()
        )
        table.add_row("Models Used", model_str)

    console.print(table)
