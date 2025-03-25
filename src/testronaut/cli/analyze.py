"""
CLI command for analyzing tools.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from testronaut.analyzers.llm_enhanced_analyzer import LLMEnhancedAnalyzer
from testronaut.analyzers.standard_analyzer import StandardCLIAnalyzer
from testronaut.utils.command import CommandRunner
from testronaut.utils.logging import configure_logging, get_logger

# Initialize logger
logger = get_logger(__name__)
console = Console()


def analyze_tool(
    tool_path: str,
    output: Optional[Path] = None,
    deep: bool = False,
    enhanced: bool = True,  # Default to enhanced analysis
    verbose: bool = False,
    sql_debug: bool = False,  # Add SQL debug option
) -> None:
    """
    Analyze a CLI tool.

    Args:
        tool_path: Path to the CLI tool executable.
        output: Directory to save analysis results.
        deep: Whether to perform a deeper analysis.
        enhanced: Whether to use the LLM-enhanced analyzer.
        verbose: Whether to show verbose logging.
        sql_debug: Whether to enable detailed SQL query logging.
    """
    # Configure logging based on verbosity
    if verbose:
        configure_logging(level="DEBUG")
        logger.debug("Verbose logging enabled")

    # Configure SQL debugging if requested
    if sql_debug:
        from testronaut.models.base import configure_sql_logging

        configure_sql_logging(debug=True)
        logger.debug("SQL debugging enabled")

    try:
        # Show status in console
        rprint(f"[bold blue]Analyzing {tool_path}...[/bold blue]")

        # Create output directory if specified
        output_file = None
        semantic_dir = None
        purpose_dir = None
        if output:
            output.mkdir(parents=True, exist_ok=True)
            output_file = output / f"{Path(tool_path).name}_analysis.json"
            semantic_dir = output / "semantic"
            semantic_dir.mkdir(exist_ok=True)
            purpose_dir = output / "purpose"
            purpose_dir.mkdir(exist_ok=True)

        # Create a spinner to show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Start a task
            task = progress.add_task("Running CLI analysis...", total=None)

            # Initialize the appropriate analyzer
            command_runner = CommandRunner()
            # Use Union type to allow both analyzer types
            analyzer: Union[LLMEnhancedAnalyzer, StandardCLIAnalyzer]

            if enhanced:
                progress.update(task, description="Running LLM-enhanced analysis...")
                analyzer = LLMEnhancedAnalyzer(command_runner=command_runner)
            else:
                progress.update(task, description="Running standard analysis...")
                analyzer = StandardCLIAnalyzer(command_runner=command_runner)

            # Analyze the tool
            cli_tool = analyzer.analyze_cli_tool(tool_path)

            # Export results if output directory specified
            if output and output_file:
                progress.update(task, description="Exporting analysis results...")
                # Export to JSON
                export_to_json(cli_tool, output_file)

                # Export semantic analysis if enhanced
                if enhanced and hasattr(cli_tool, "metadata"):
                    metadata = getattr(cli_tool, "metadata", {})
                    semantic_analysis = metadata.get("semantic_analysis", {})

                    if semantic_analysis and semantic_dir:
                        for command in cli_tool.commands:
                            # Check if command has the attributes we need
                            if hasattr(command, "id") and hasattr(command, "name"):
                                cmd_id = command.id  # type: ignore
                                if cmd_id in semantic_analysis:
                                    semantic_file = semantic_dir / f"{command.name}.json"  # type: ignore
                                    export_dict_to_json(
                                        semantic_analysis[cmd_id],
                                        semantic_file,
                                    )

                # Export purpose information
                if enhanced and purpose_dir:
                    # Parse JSON fields if needed
                    use_cases = []
                    if cli_tool.use_cases:
                        try:
                            if isinstance(cli_tool.use_cases, str):
                                use_cases = json.loads(cli_tool.use_cases)
                            else:
                                use_cases = cli_tool.use_cases
                        except:
                            pass

                    testing_considerations = []
                    if cli_tool.testing_considerations:
                        try:
                            if isinstance(cli_tool.testing_considerations, str):
                                testing_considerations = json.loads(cli_tool.testing_considerations)
                            else:
                                testing_considerations = cli_tool.testing_considerations
                        except:
                            pass

                    tool_purpose_data = {
                        "name": cli_tool.name,
                        "purpose": cli_tool.purpose or "",
                        "background": cli_tool.background or "",
                        "use_cases": use_cases,
                        "testing_considerations": testing_considerations,
                    }
                    export_dict_to_json(
                        tool_purpose_data,
                        purpose_dir / "tool_purpose.json",
                    )

                    # Export command purposes
                    command_purposes = {}
                    for command in cli_tool.commands:
                        # Check if command has the attributes we need
                        if (
                            hasattr(command, "name")
                            and hasattr(command, "purpose")
                            and hasattr(command, "description")
                        ):
                            command_purposes[command.name] = {  # type: ignore
                                "name": command.name,  # type: ignore
                                "purpose": command.purpose or "",  # type: ignore
                                "description": command.description or "",  # type: ignore
                            }
                    export_dict_to_json(
                        command_purposes,
                        purpose_dir / "command_purposes.json",
                    )

            # Complete task
            progress.update(task, description="Analysis complete!", completed=True)

        # Print summary
        command_count = len(cli_tool.commands)
        # Count commands with purpose
        purposes_count = 0
        for cmd in cli_tool.commands:
            if hasattr(cmd, "purpose") and getattr(cmd, "purpose", None):
                purposes_count += 1

        summary = [
            f"[bold green]Analysis of {tool_path} completed![/bold green]",
            f"Found {command_count} top-level commands.",
        ]

        if enhanced:
            summary.append(
                f"Tool purpose: {cli_tool.purpose[:100] + '...' if cli_tool.purpose and len(cli_tool.purpose) > 100 else cli_tool.purpose or 'Not available'}"
            )
            summary.append(f"Commands with purpose information: {purposes_count}/{command_count}")

        rprint(Panel.fit("\n".join(summary)))

        if output_file:
            rprint(f"[bold]Results saved to:[/bold] {output_file}")

    except Exception as e:
        logger.exception(f"Failed to analyze tool: {str(e)}")
        rprint(f"[bold red]Error:[/bold red] {str(e)}")


def export_to_json(cli_tool: Any, output_file: Path) -> None:
    """
    Export CLI tool to JSON file.

    Args:
        cli_tool: The CLI tool object to export.
        output_file: The output file path.
    """
    try:
        # Convert to dictionary
        data = cli_tool.dict()

        # Ensure all new fields are included
        if hasattr(cli_tool, "purpose") and cli_tool.purpose:
            data["purpose"] = cli_tool.purpose
        if hasattr(cli_tool, "background") and cli_tool.background:
            data["background"] = cli_tool.background

        # Handle JSON string fields that should be lists
        if hasattr(cli_tool, "use_cases"):
            if cli_tool.use_cases:
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
            if cli_tool.testing_considerations:
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
                if hasattr(cmd, "purpose") and cmd.purpose and i < len(data["commands"]):
                    data["commands"][i]["purpose"] = cmd.purpose

        # Write to file
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
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
