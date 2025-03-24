#!/usr/bin/env python
"""
Simple demonstration of the LLM-enhanced analyzer with a mock CLI tool.
This example doesn't require an actual CLI tool to be installed.
"""

import sys
from pathlib import Path

from testronaut.analyzers import LLMEnhancedAnalyzer
from testronaut.models.cli_tool import CLITool, Command, CommandOption, get_semantic_analysis


def create_mock_cli_tool() -> CLITool:
    """
    Create a mock CLI tool for demonstration purposes

    Returns:
        Mock CLI tool with predefined commands
    """
    # Create the root command
    root_cmd = Command(
        name="mock-tool",
        description="A demonstration CLI tool for testing",
        created_at="2025-03-24T00:00:00Z",
        help_text="mock-tool - A tool for demonstrating Testronaut's LLM-enhanced analyzer",
        options=[
            CommandOption(
                name="--verbose",
                short_name="-v",
                description="Enable verbose output",
                required=False,
            ),
            CommandOption(
                name="--config",
                short_name="-c",
                description="Specify a config file",
                required=False,
                takes_value=True,
            ),
        ],
    )

    # Create some subcommands
    init_cmd = Command(
        name="init",
        description="Initialize a new project",
        created_at="2025-03-24T00:00:00Z",
        help_text="mock-tool init - Initialize a new project in the current directory",
        parent_command_id=root_cmd.id,
        options=[
            CommandOption(
                name="--force",
                short_name="-f",
                description="Force initialization even if project exists",
                required=False,
            ),
        ],
        examples=[
            "mock-tool init",
            "mock-tool init --force",
        ],
    )

    build_cmd = Command(
        name="build",
        description="Build the project",
        created_at="2025-03-24T00:00:00Z",
        help_text="mock-tool build - Build the project with specified options",
        parent_command_id=root_cmd.id,
        options=[
            CommandOption(
                name="--target",
                short_name="-t",
                description="Specify build target",
                required=False,
                takes_value=True,
            ),
            CommandOption(
                name="--release",
                short_name="-r",
                description="Build in release mode",
                required=False,
            ),
        ],
        examples=[
            "mock-tool build",
            "mock-tool build --release",
            "mock-tool build --target web",
        ],
    )

    test_cmd = Command(
        name="test",
        description="Run tests",
        created_at="2025-03-24T00:00:00Z",
        help_text="mock-tool test - Run tests for the project",
        parent_command_id=root_cmd.id,
        options=[
            CommandOption(
                name="--filter",
                short_name="-f",
                description="Filter tests by name",
                required=False,
                takes_value=True,
            ),
            CommandOption(
                name="--all",
                short_name="-a",
                description="Run all tests",
                required=False,
            ),
        ],
        examples=[
            "mock-tool test",
            "mock-tool test --all",
            "mock-tool test --filter integration",
        ],
    )

    # Add all commands to the CLI tool
    return CLITool(
        name="mock-tool",
        version="1.0.0",
        description="A demonstration CLI tool for testing Testronaut",
        commands=[root_cmd, init_cmd, build_cmd, test_cmd],
    )


def enhance_with_llm(cli_tool: CLITool) -> CLITool:
    """
    Enhance a CLI tool with LLM-generated semantic analysis

    Args:
        cli_tool: CLI tool to enhance

    Returns:
        Enhanced CLI tool with semantic analysis
    """
    analyzer = LLMEnhancedAnalyzer()

    # Copy the CLI tool to avoid modifying the original
    enhanced_tool = cli_tool.model_copy(deep=True)

    # Perform semantic analysis on the CLI tool
    analyzer._enhance_with_semantic_analysis(enhanced_tool)

    # Detect relationships between commands
    analyzer._enhance_with_relationship_analysis(enhanced_tool)

    return enhanced_tool


def display_semantic_analysis(cli_tool: CLITool):
    """
    Display semantic analysis information for all commands

    Args:
        cli_tool: CLI tool with semantic analysis
    """
    print("\nSemantic Analysis Results:")
    print("=========================")

    for command in cli_tool.commands:
        semantic = get_semantic_analysis(command)
        if semantic:
            print(f"\nCommand: {command.name}")
            print(f"  Primary function: {semantic.primary_function}")
            print(f"  Risk level: {semantic.risk_level}")
            print("  Common use cases:")
            for use_case in semantic.common_use_cases:
                print(f"    - {use_case}")


def save_results(cli_tool: CLITool, output_dir: Path):
    """
    Save analysis results to a file

    Args:
        cli_tool: Analyzed CLI tool
        output_dir: Directory to save results
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / "mock_tool_analysis.json"

    with open(output_file, "w") as f:
        json_str = cli_tool.model_dump_json(indent=2)
        f.write(json_str)

    print(f"\nAnalysis saved to: {output_file}")


def main():
    # Parse command-line arguments
    output_dir = Path("./analysis_results")
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])

    # Create a mock CLI tool
    print("Creating mock CLI tool...")
    cli_tool = create_mock_cli_tool()

    # Enhance with LLM
    print("Enhancing with LLM analysis...")
    enhanced_tool = enhance_with_llm(cli_tool)

    # Display results
    print("\nAnalysis complete!")
    print(f"Tool: {enhanced_tool.name}")
    print(f"Description: {enhanced_tool.description}")
    print(f"Version: {enhanced_tool.version}")
    print(f"Commands: {len(enhanced_tool.commands)}")

    # Display semantic analysis
    display_semantic_analysis(enhanced_tool)

    # Save results
    save_results(enhanced_tool, output_dir)


if __name__ == "__main__":
    main()
