"""
CLI command for analyzing tools.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

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
    enhanced: bool = False,
    verbose: bool = False,
):
    """
    Analyze a CLI tool.

    Args:
        tool_path: Path to the CLI tool executable.
        output: Directory to save analysis results.
        deep: Whether to perform a deeper analysis.
        enhanced: Whether to use the LLM-enhanced analyzer.
        verbose: Whether to show verbose logging.
    """
    # Configure logging based on verbosity
    if verbose:
        configure_logging(log_level="DEBUG")
        logger.debug("Verbose logging enabled")

    try:
        # Show status in console
        rprint(f"[bold blue]Analyzing {tool_path}...[/bold blue]")

        # Create output directory if specified
        output_file = None
        semantic_dir = None
        if output:
            output.mkdir(parents=True, exist_ok=True)
            output_file = output / f"{Path(tool_path).name}_analysis.json"
            semantic_dir = output / "semantic"
            semantic_dir.mkdir(exist_ok=True)

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

            if enhanced:
                progress.update(task, description="Running LLM-enhanced analysis...")
                analyzer = LLMEnhancedAnalyzer(command_runner=command_runner)
            else:
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
                            if hasattr(command, "id"):
                                cmd_id = command.id
                                if cmd_id in semantic_analysis:
                                    semantic_file = semantic_dir / f"{command.name}.json"
                                    export_dict_to_json(
                                        semantic_analysis[cmd_id],
                                        semantic_file,
                                    )

            # Complete task
            progress.update(task, description="Analysis complete!", completed=True)

        # Print summary
        rprint(
            Panel.fit(
                f"[bold green]Analysis of {tool_path} completed![/bold green]\n"
                f"Found {len(cli_tool.commands)} top-level commands."
            )
        )

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
