"""
Main entry point for Testronaut CLI.

This module allows the package to be run as a script with `python -m testronaut`.
"""

import sys
from typing import List, Optional

from rich import print as rprint

from testronaut.cli import app


def main(argv: Optional[List[str]] = None) -> int:
    """Run Testronaut command-line interface."""
    try:
        # Check if we're doing a direct analyze command
        if (
            len(argv or sys.argv) >= 3
            and argv
            and argv[1] == "analyze"
            and argv[2] != "tool"
            and argv[2] != "list"
            and argv[2] != "list-db"
            and argv[2] != "show"
            and argv[2] != "get-db"
            and argv[2] != "browser"
            and not argv[2].startswith("-")
        ):
            # Convert 'analyze <tool>' to 'analyze direct <tool>'
            tool_name = argv[2]
            original_args = argv.copy()
            argv[2] = "direct"
            argv.insert(3, tool_name)
            try:
                app(argv)
                return 0  # Return 0 for success
            except SystemExit:
                # If it fails with direct, try original format
                try:
                    app(original_args)
                    return 0  # Return 0 for success
                except SystemExit as e:
                    return e.code if isinstance(e.code, int) else 1
        else:
            try:
                app(argv)
                return 0  # Return 0 for success
            except SystemExit as e:
                return e.code if isinstance(e.code, int) else 1
    except Exception as e:
        rprint(f"[bold red]Error:[/bold red] {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
