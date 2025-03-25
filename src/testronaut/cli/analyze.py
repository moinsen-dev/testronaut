"""
CLI command for analyzing tools.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
    interactive: bool = False,  # Interactive mode for selecting commands
    max_commands: Optional[int] = None,  # Maximum commands to analyze
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
        interactive: Whether to use interactive mode for selecting commands.
        max_commands: Maximum number of commands to analyze.
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

        # Initialize the appropriate analyzer
        command_runner = CommandRunner()
        # Use Union type to allow both analyzer types
        analyzer: Union[LLMEnhancedAnalyzer, StandardCLIAnalyzer]

        if enhanced:
            rprint("[cyan]Using llm_enhanced analyzer for analysis[/cyan]")
            analyzer = LLMEnhancedAnalyzer(command_runner=command_runner)
        else:
            rprint("[cyan]Using standard analyzer for analysis[/cyan]")
            analyzer = StandardCLIAnalyzer(command_runner=command_runner)

        # Handle interactive mode
        selected_commands = None
        if interactive:
            try:
                import questionary
                from rich.prompt import Confirm

                rprint("[cyan]Starting interactive command discovery mode...[/cyan]")

                # First, get the tool's help text to extract top-level commands
                help_text = analyzer.get_tool_help_text(tool_path)

                # Extract top-level commands - check if StandardCLIAnalyzer
                if isinstance(analyzer, StandardCLIAnalyzer) and hasattr(
                    analyzer, "extract_commands"
                ):
                    main_commands = analyzer.extract_commands(tool_path, help_text)
                elif isinstance(analyzer, LLMEnhancedAnalyzer) and hasattr(
                    analyzer, "standard_analyzer"
                ):
                    # Use standard_analyzer for LLMEnhancedAnalyzer
                    main_commands = analyzer.standard_analyzer.extract_commands(
                        tool_path, help_text
                    )
                else:
                    # Fallback if extract_commands isn't available
                    rprint(
                        "[yellow]Cannot extract commands in interactive mode with this analyzer[/yellow]"
                    )
                    main_commands = []

                if not main_commands:
                    rprint("[red]No commands found for this tool.[/red]")
                    return

                # Display the discovered commands for selection
                rprint(
                    f"\n[green]Discovered {len(main_commands)} main commands for {tool_path}:[/green]"
                )

                # Create list of command choices with descriptions
                choices = []
                for cmd in main_commands:
                    name = cmd.get("name", "")
                    desc = cmd.get("description", "No description")
                    if name:
                        display_text = f"{name} - {desc}"
                        choices.append(questionary.Choice(value=name, text=display_text))

                # Let user select which commands to analyze
                rprint(
                    "\n[cyan]Select commands to analyze (space to select, enter to confirm):[/cyan]"
                )
                selected_commands = questionary.checkbox(
                    "",
                    choices=choices,
                    validate=lambda selected: True
                    if selected
                    else "Please select at least one command",
                ).ask()

                if not selected_commands:
                    rprint("[yellow]No commands selected. Exiting.[/yellow]")
                    return

                # Ask if user wants to analyze subcommands
                analyze_subcommands = Confirm.ask(
                    "[cyan]Do you want to analyze subcommands of the selected commands?[/cyan]"
                )

                if analyze_subcommands:
                    max_depth = questionary.text(
                        "Maximum depth for subcommand discovery (1-10):",
                        default="3",
                        validate=lambda text: text.isdigit() and 1 <= int(text) <= 10,
                    ).ask()
                    max_depth = int(max_depth)
                else:
                    max_depth = 1  # Only top-level commands

                # Get maximum commands to discover if not specified
                if not max_commands:
                    max_commands_input = questionary.text(
                        "Maximum number of commands to analyze:",
                        default="30",
                        validate=lambda text: text.isdigit() and int(text) > 0,
                    ).ask()
                    max_commands = int(max_commands_input)

                rprint(
                    f"\n[green]Analyzing {len(selected_commands)} command(s) with max depth {max_depth} and max commands {max_commands}[/green]"
                )

                # Create a filtered analyzer that only processes selected commands
                # Handle both analyzer types differently
                if isinstance(analyzer, StandardCLIAnalyzer) and hasattr(
                    analyzer, "extract_commands"
                ):
                    original_extract_commands = analyzer.extract_commands

                    def filtered_extract_commands(
                        tool_name: str, help_text: str
                    ) -> List[Dict[str, Any]]:
                        commands = original_extract_commands(tool_name, help_text)
                        if tool_name == tool_path:  # Only filter at the top level
                            return [cmd for cmd in commands if cmd.get("name") in selected_commands]
                        return commands

                    # Apply the filter function temporarily
                    analyzer.extract_commands = filtered_extract_commands  # type: ignore
                elif isinstance(analyzer, LLMEnhancedAnalyzer) and hasattr(
                    analyzer, "standard_analyzer"
                ):
                    # For LLMEnhancedAnalyzer, work with its standard_analyzer
                    original_extract_commands = analyzer.standard_analyzer.extract_commands

                    def filtered_extract_commands(
                        tool_name: str, help_text: str
                    ) -> List[Dict[str, Any]]:
                        commands = original_extract_commands(tool_name, help_text)
                        if tool_name == tool_path:  # Only filter at the top level
                            return [cmd for cmd in commands if cmd.get("name") in selected_commands]
                        return commands

                    # Apply the filter function to the standard_analyzer
                    analyzer.standard_analyzer.extract_commands = filtered_extract_commands  # type: ignore

            except ImportError:
                rprint(
                    "[yellow]Interactive mode requires 'questionary' package. Falling back to standard analysis.[/yellow]"
                )
                interactive = False

        # Create a spinner to show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Start a task
            task_description = "Running CLI analysis..."
            if interactive and selected_commands:
                task_description = f"Analyzing {len(selected_commands)} command(s)..."
            task = progress.add_task(task_description, total=None)

            # Update progress description based on analyzer type
            if enhanced:
                progress.update(task, description="Running LLM-enhanced analysis...")
            else:
                progress.update(task, description="Running standard analysis...")

            # Analyze the tool
            cli_tool = analyzer.analyze_cli_tool(tool_path, max_commands=max_commands)

            # Restore original extract_commands if we modified it
            if interactive and selected_commands:
                if isinstance(analyzer, StandardCLIAnalyzer) and hasattr(
                    analyzer, "extract_commands"
                ):
                    analyzer.extract_commands = original_extract_commands  # type: ignore
                elif isinstance(analyzer, LLMEnhancedAnalyzer) and hasattr(
                    analyzer, "standard_analyzer"
                ):
                    analyzer.standard_analyzer.extract_commands = original_extract_commands  # type: ignore

            # Export results if output directory specified
            if output and output_file:
                progress.update(task, description="Exporting analysis results...")
                # Export to JSON
                export_to_json(cli_tool, output_file)

                # Export semantic analysis if enhanced
                if enhanced and hasattr(cli_tool, "metadata"):
                    metadata_dict = {}
                    metadata = getattr(cli_tool, "metadata", None)

                    # Handle metadata as a dict-like object or convert to dict if needed
                    if hasattr(metadata, "get") and callable(metadata.get):
                        # If it's dict-like, use get method
                        semantic_analysis = metadata.get("semantic_analysis", {})
                    elif hasattr(metadata, "__dict__"):
                        # If it has __dict__, convert to dict
                        metadata_dict = vars(metadata)
                        semantic_analysis = metadata_dict.get("semantic_analysis", {})
                    else:
                        # Default to empty dict
                        semantic_analysis = {}

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
                    if hasattr(cli_tool, "use_cases") and cli_tool.use_cases:
                        try:
                            if isinstance(cli_tool.use_cases, str):
                                use_cases = json.loads(cli_tool.use_cases)
                            else:
                                use_cases = cli_tool.use_cases
                        except:
                            pass

                    testing_considerations = []
                    if (
                        hasattr(cli_tool, "testing_considerations")
                        and cli_tool.testing_considerations
                    ):
                        try:
                            if isinstance(cli_tool.testing_considerations, str):
                                testing_considerations = json.loads(cli_tool.testing_considerations)
                            else:
                                testing_considerations = cli_tool.testing_considerations
                        except:
                            pass

                    tool_purpose_data = {
                        "name": cli_tool.name,
                        "purpose": getattr(cli_tool, "purpose", "") or "",
                        "background": getattr(cli_tool, "background", "") or "",
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
        # Count top-level commands vs subcommands
        top_level_count = sum(
            1 for cmd in cli_tool.commands if not getattr(cmd, "is_subcommand", False)
        )
        subcommand_count = command_count - top_level_count

        # Count commands with purpose
        purposes_count = 0
        for cmd in cli_tool.commands:
            if hasattr(cmd, "purpose") and getattr(cmd, "purpose", None):
                purposes_count += 1

        summary = [
            f"[bold green]Analysis of {tool_path} completed![/bold green]",
            f"Found {top_level_count} top-level commands and {subcommand_count} subcommands (total: {command_count}).",
        ]

        if enhanced:
            summary.append(
                f"Tool purpose: {getattr(cli_tool, 'purpose', '')[:100] + '...' if hasattr(cli_tool, 'purpose') and cli_tool.purpose and len(cli_tool.purpose) > 100 else getattr(cli_tool, 'purpose', '') or 'Not available'}"
            )
            summary.append(f"Commands with purpose information: {purposes_count}/{command_count}")

        rprint(Panel.fit("\n".join(summary)))

        if output_file:
            rprint(f"[bold]Results saved to:[/bold] {output_file}")

    except Exception as e:
        logger.exception(f"Failed to analyze tool: {str(e)}")
        rprint(f"[bold red]Error:[/bold red] {str(e)}")

        # If in interactive mode and we modified the extract_commands function, restore it
        if interactive and "analyzer" in locals() and "original_extract_commands" in locals():
            if isinstance(analyzer, StandardCLIAnalyzer) and hasattr(analyzer, "extract_commands"):
                analyzer.extract_commands = original_extract_commands  # type: ignore
            elif isinstance(analyzer, LLMEnhancedAnalyzer) and hasattr(
                analyzer, "standard_analyzer"
            ):
                analyzer.standard_analyzer.extract_commands = original_extract_commands  # type: ignore


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
