"""
CLI command for analyzing tools.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import questionary
import typer
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner

from testronaut.utils.logging import configure_logging, get_logger

# Initialize logger
logger = get_logger(__name__)
console = Console()


def analyze_tool(
    ctx: typer.Context,
    tool_path: str,
    output: Optional[Path] = None,
    deep: bool = False,
    enhanced: bool = False,
    verbose: bool = False,
    sql_debug: bool = False,
    interactive: bool = False,
    max_commands: Optional[int] = None,
) -> None:
    """
    Analyze a CLI tool and generate a report of its commands, options, and arguments.

    Args:
        ctx: Typer context.
        tool_path: Path to the CLI tool to analyze.
        output: Directory to output the analysis as JSON files.
        deep: Whether to perform a deep analysis of options and arguments.
        enhanced: Whether to use LLM-enhanced analysis for better descriptions.
        verbose: Whether to print verbose output.
        sql_debug: Whether to log SQL queries.
        interactive: Whether to run in interactive mode to select commands for analysis.
        max_commands: Maximum number of commands to analyze.
    """
    # Configure logging
    configure_logging(verbose=verbose, sql_debug=sql_debug)

    # Notify user about what's happening
    tool_name = os.path.basename(tool_path)
    logger.info(f"Analyzing tool: {tool_name}")

    # Create progress spinner
    spinner = Spinner()

    try:
        # Start analysis
        with spinner(f"Analyzing {tool_name}..."):
            # Get the appropriate analyzer
            analyzer = get_analyzer(enhanced)
            logger.info(f"Using {analyzer.__class__.__name__.lower()} for analysis")

            # Extract main and subcommand information
            if interactive:
                # For interactive mode, extract commands first without full analysis
                spinner.text = f"Discovering commands for {tool_name}..."
                cli_tool = analyzer.standard_analyzer.analyze_cli_tool(
                    tool_path, max_commands=max_commands or 100
                )

                # Stop spinner temporarily
                spinner.stop()

                # Display commands to the user
                command_choices = [cmd.name for cmd in cli_tool.commands if not cmd.is_subcommand]
                if not command_choices:
                    console.print("[red]No commands found for this tool.[/red]")
                    return

                # Use questionary to select commands
                selected_commands = questionary.checkbox(
                    "Select commands to analyze:", choices=command_choices
                ).ask()

                if not selected_commands:
                    console.print("[yellow]No commands selected, exiting.[/yellow]")
                    return

                # Ask for discovery parameters
                discovery_depth = questionary.select(
                    "Select subcommand discovery depth:",
                    choices=["1 (shallow)", "3 (moderate)", "5 (deep)", "10 (very deep)"],
                    default="3 (moderate)",
                ).ask()
                depth = int(discovery_depth.split()[0])

                # Ask for max_commands limit
                max_commands_str = questionary.select(
                    "Select maximum number of commands to analyze:",
                    choices=[
                        "10 (minimal)",
                        "50 (basic)",
                        "100 (moderate)",
                        "200 (comprehensive)",
                        "No limit",
                    ],
                    default="50 (basic)",
                ).ask()
                if max_commands_str != "No limit":
                    max_commands = int(max_commands_str.split()[0])

                # Restart spinner
                spinner.start("Running CLI analysis...")

                # Create a new analyzer to run with selected commands
                if enhanced:
                    # Filter commands to just the selected ones
                    filtered_commands = [
                        cmd for cmd in cli_tool.commands if cmd.name in selected_commands
                    ]
                    cli_tool.commands = filtered_commands

                    # Restore original command extraction if it was modified
                    cli_tool = analyzer.analyze_cli_tool(tool_path, max_commands=max_commands)
                else:
                    # For standard analyzer, just run with the selected settings
                    cli_tool = analyzer.analyze_cli_tool(
                        tool_path, max_depth=depth, max_commands=max_commands
                    )
            else:
                # Regular non-interactive analysis
                spinner.text = "Running CLI analysis..."
                cli_tool = analyzer.analyze_cli_tool(tool_path, max_commands=max_commands)

        # Process results
        if output:
            # Ensure output directory exists
            output.mkdir(exist_ok=True, parents=True)

            # Generate output file path
            output_file = output / f"{tool_name}_analysis.json"

            # Export to JSON - handling fields that may cause Pydantic serialization warnings
            # Ensure string fields are actually strings
            if hasattr(cli_tool, "purpose") and isinstance(cli_tool.purpose, list):
                cli_tool.purpose = " ".join(cli_tool.purpose)

            if hasattr(cli_tool, "background") and isinstance(cli_tool.background, list):
                cli_tool.background = " ".join(cli_tool.background)

            # Clean up any fields that might cause serialization issues for each command
            if hasattr(cli_tool, "commands"):
                for cmd in cli_tool.commands:
                    if hasattr(cmd, "purpose") and isinstance(cmd.purpose, list):
                        cmd.purpose = " ".join(cmd.purpose)

                    # Ensure examples are properly formatted
                    if hasattr(cmd, "examples"):
                        for i, example in enumerate(cmd.examples):
                            if isinstance(example, str):
                                # Convert string examples to proper Example objects
                                cmd.examples[i] = {"command_line": example, "description": ""}

            # Export to JSON
            try:
                with open(output_file, "w") as f:
                    # Handle conversion for JSONEncoder
                    cli_tool_dict = cli_tool.model_dump()
                    json.dump(cli_tool_dict, f, indent=2, cls=CLIToolJSONEncoder)
                logger.info(f"Exported analysis to {output_file}")
            except Exception as e:
                logger.error(f"Failed to export analysis: {str(e)}")

        # Display token usage if available from LLM-enhanced analysis
        if enhanced and hasattr(cli_tool, "metadata") and "llm_usage" in cli_tool.metadata:
            usage = cli_tool.metadata["llm_usage"]
            token_count = usage.get("total_tokens", 0)
            api_calls = usage.get("api_calls", 0)
            cost = usage.get("estimated_cost", 0.0)

            console.print(
                f"[blue]LLM Usage: {token_count} tokens in {api_calls} API calls "
                f"(estimated cost: ${cost:.4f})[/blue]"
            )

        # Display summary
        with spinner("Analysis complete!"):
            # Calculate command stats
            top_level_count = 0
            subcommand_count = 0

            for cmd in cli_tool.commands:
                if not getattr(cmd, "is_subcommand", False):
                    top_level_count += 1
                else:
                    subcommand_count += 1

            # Purpose for output
            purpose = getattr(cli_tool, "purpose", "")
            if purpose and len(purpose) > 100:
                purpose = purpose[:97] + "..."

            purpose_count = sum(
                1 for cmd in cli_tool.commands if hasattr(cmd, "purpose") and cmd.purpose
            )

            # Create a panel with results
            panel_content = [
                f"Analysis of {tool_name} completed!",
                f"Found {top_level_count} top-level commands and {subcommand_count} subcommands (total: {len(cli_tool.commands)}).",
            ]

            if purpose:
                panel_content.append(f"Tool purpose: {purpose}")

            panel_content.append(
                f"Commands with purpose information: {purpose_count}/{len(cli_tool.commands)}"
            )

            if output:
                panel_content.append(f"Results saved to: {output_file}")

            console.print(Panel("\n".join(panel_content), expand=False))

        # Short version in case the panel is too large for some terminals
        console.print(
            Panel(
                "\n".join(
                    [
                        f"Analysis of {tool_name} completed!",
                        f"Found {top_level_count} top-level commands.",
                        f"Results saved to: {output}" if output else "",
                    ]
                ),
                expand=False,
            )
        )

    except Exception as e:
        spinner.stop()
        console.print(f"[red]Error analyzing tool: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def export_to_json(cli_tool: Any, output_file: Path) -> None:
    """
    Export CLI tool to JSON file.

    Args:
        cli_tool: The CLI tool object to export.
        output_file: The output file path.
    """
    try:
        # Check if the object has dict method
        if hasattr(cli_tool, "dict") and callable(cli_tool.dict):
            # Convert to dictionary
            data = cli_tool.dict()
        else:
            # Use vars if dict method not available
            data = vars(cli_tool)

        # Handle datetime objects before serialization
        def convert_datetime(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return obj

        # Ensure all new fields are included
        if hasattr(cli_tool, "purpose"):
            data["purpose"] = getattr(cli_tool, "purpose", "")
        if hasattr(cli_tool, "background"):
            data["background"] = getattr(cli_tool, "background", "")

        # Handle JSON string fields that should be lists
        if hasattr(cli_tool, "use_cases"):
            if getattr(cli_tool, "use_cases", None):
                try:
                    # If it's a JSON string, parse it
                    if isinstance(cli_tool.use_cases, str):
                        data["use_cases"] = json.loads(cli_tool.use_cases)
                    else:
                        data["use_cases"] = cli_tool.use_cases
                except:
                    data["use_cases"] = []
            else:
                data["use_cases"] = []

        if hasattr(cli_tool, "testing_considerations"):
            if getattr(cli_tool, "testing_considerations", None):
                try:
                    # If it's a JSON string, parse it
                    if isinstance(cli_tool.testing_considerations, str):
                        data["testing_considerations"] = json.loads(cli_tool.testing_considerations)
                    else:
                        data["testing_considerations"] = cli_tool.testing_considerations
                except:
                    data["testing_considerations"] = []
            else:
                data["testing_considerations"] = []

        # Include command purpose information
        if "commands" in data and isinstance(data["commands"], list):
            for i, cmd in enumerate(cli_tool.commands):
                if (
                    hasattr(cmd, "purpose")
                    and getattr(cmd, "purpose", None)
                    and i < len(data["commands"])
                ):
                    data["commands"][i]["purpose"] = cmd.purpose

        # Write to file with datetime handling
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2, default=convert_datetime)
        logger.info(f"Exported analysis to {output_file}")
    except Exception as e:
        logger.error(f"Failed to export analysis: {str(e)}")


def export_dict_to_json(data: Dict[str, Any], output_file: Path) -> None:
    """
    Export dictionary to JSON file.

    Args:
        data: The dictionary to export.
        output_file: The output file path.
    """
    try:
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Exported data to {output_file}")
    except Exception as e:
        logger.error(f"Failed to export data: {str(e)}")
