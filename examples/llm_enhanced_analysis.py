#!/usr/bin/env python3
"""
LLM Enhanced Analysis Example.

This script demonstrates how to use the LLM-enhanced analyzer to analyze CLI tools.
"""

import sys
from pathlib import Path
from typing import Optional

from testronaut.analyzers import LLMEnhancedAnalyzer
from testronaut.models import CLITool
from testronaut.models.cli_tool import get_relationship_analysis, get_semantic_analysis


def analyze_tool(tool_name: str, output_dir: Optional[Path] = None) -> CLITool:
    """
    Analyze a CLI tool with LLM-enhanced analyzer.

    Args:
        tool_name: Name of the CLI tool to analyze.
        output_dir: Optional directory to save analysis results.

    Returns:
        The analyzed CLI tool object.
    """
    # Initialize the LLM-enhanced analyzer
    analyzer = LLMEnhancedAnalyzer()

    # Analyze the tool
    print(f"Analyzing tool: {tool_name}...")
    cli_tool = analyzer.analyze_cli_tool(tool_name)
    print(f"Analysis complete: Found {len(cli_tool.commands)} commands")

    # Save results if output directory is provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save the basic analysis
        output_file = output_dir / f"{tool_name}_analysis.json"
        with open(output_file, "w") as f:
            json_str = cli_tool.model_dump_json(indent=2)
            f.write(json_str)
        print(f"Basic analysis saved to: {output_file}")

        # Extract and save semantic analysis for each command
        semantic_dir = output_dir / "semantic"
        semantic_dir.mkdir(exist_ok=True)

        for command in cli_tool.commands:
            semantic_analysis = get_semantic_analysis(command)
            if semantic_analysis:
                semantic_file = semantic_dir / f"{tool_name}_{command.name}_semantic.json"
                with open(semantic_file, "w") as f:
                    f.write(semantic_analysis.json(indent=2))
                print(f"Semantic analysis for '{command.name}' saved to: {semantic_file}")

        # Extract and save relationship analysis
        relationships = get_relationship_analysis(cli_tool)
        if relationships:
            rel_file = output_dir / f"{tool_name}_relationships.json"
            with open(rel_file, "w") as f:
                f.write(relationships.json(indent=2))
            print(f"Relationship analysis saved to: {rel_file}")

    return cli_tool


def main():
    """Run the example script."""
    # Get the tool name from command line arguments or use a default
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]
    else:
        tool_name = "git"  # Default tool to analyze

    # Get output directory from command line arguments or use a default
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = Path("./analysis_results")

    # Analyze the tool and print a summary
    cli_tool = analyze_tool(tool_name, output_dir)

    # Print a summary of the analyzed tool
    print("\nAnalysis Summary:")
    print(f"  Tool: {cli_tool.name}")
    print(f"  Description: {cli_tool.description}")
    print(f"  Commands: {len(cli_tool.commands)}")

    # List commands with semantic insights
    print("\nCommands with Semantic Analysis:")
    for command in cli_tool.commands:
        semantic = get_semantic_analysis(command)
        if semantic:
            print(f"  {command.name}: {semantic.primary_function}")
            print(f"    Risk Level: {semantic.risk_level}")
            if semantic.common_use_cases:
                print(f"    Common Use Cases: {', '.join(semantic.common_use_cases[:2])}")

    # Show relationship insights
    relationships = get_relationship_analysis(cli_tool)
    if relationships and relationships.parent_child:
        print("\nCommand Relationships:")
        for rel in relationships.parent_child:
            print(f"  {rel.parent} -> {rel.child}")

    if relationships and relationships.workflows:
        print("\nCommon Workflows:")
        for wf in relationships.workflows:
            print(f"  {wf.name}: {' -> '.join(wf.steps)}")

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
