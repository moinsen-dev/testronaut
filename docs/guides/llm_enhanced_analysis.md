# LLM-Enhanced CLI Analysis

The Testronaut framework includes an LLM-enhanced analyzer that uses large language models to provide deeper insights into CLI tools and commands. This guide covers how to use the enhanced analyzer and the benefits it provides over the standard analyzer.

## Overview

The LLM-enhanced analyzer extends the standard CLI analyzer by adding semantic analysis and relationship detection using large language models. This provides richer information about:

- Command purposes and descriptions
- Semantic relationships between commands
- Usage patterns and workflows
- Risk levels and common use cases
- Improved examples

## Usage

### Basic Usage

To use the LLM-enhanced analyzer:

```python
from testronaut.analyzers import LLMEnhancedAnalyzer

# Initialize the analyzer
analyzer = LLMEnhancedAnalyzer()

# Analyze a CLI tool
cli_tool = analyzer.analyze_cli_tool("git")

# Access commands, options, and arguments
for command in cli_tool.commands:
    print(f"Command: {command.name}")
    print(f"Description: {command.description}")
```

### Accessing Semantic Analysis

The LLM-enhanced analyzer adds semantic information to commands:

```python
from testronaut.models.cli_tool import get_semantic_analysis

# Analyze a CLI tool
cli_tool = analyzer.analyze_cli_tool("git")

# For a specific command
command = cli_tool.commands[0]
semantic = get_semantic_analysis(command)

if semantic:
    print(f"Primary function: {semantic.primary_function}")
    print(f"Risk level: {semantic.risk_level}")
    print(f"Common use cases:")
    for use_case in semantic.common_use_cases:
        print(f"  - {use_case}")
```

### Accessing Command Relationships

The analyzer also detects relationships between commands:

```python
from testronaut.models.cli_tool import get_relationship_analysis

# Analyze a CLI tool
cli_tool = analyzer.analyze_cli_tool("git")

# Get relationship analysis
relationships = get_relationship_analysis(cli_tool)

if relationships:
    # Parent-child relationships (e.g., command and subcommands)
    print("Command hierarchies:")
    for rel in relationships.parent_child:
        print(f"  {rel.parent} -> {rel.child}")

    # Common workflows
    print("Common workflows:")
    for workflow in relationships.workflows:
        print(f"  {workflow.name}: {' -> '.join(workflow.steps)}")
```

## Configuration

The LLM-enhanced analyzer uses your configured LLM service. Make sure you have properly configured the LLM service in your `config.toml` file:

```toml
[llm]
provider = "openai"  # or "anthropic", "mock", etc.
model = "gpt-4"      # or appropriate model for your provider

[llm.openai]
api_key = "your-api-key"
```

## Benefits of LLM Enhancement

Compared to the standard analyzer, the LLM-enhanced analyzer provides:

1. **More accurate command descriptions**: The LLM can provide clear, concise descriptions even when the CLI help text is minimal or unclear.

2. **Semantic understanding**: The analyzer understands what commands do, not just their syntax.

3. **Relationship detection**: The analyzer can identify parent-child relationships and common workflows.

4. **Risk assessment**: Each command is assessed for its risk level, helping identify potentially destructive commands.

5. **Use case identification**: The analyzer identifies common use cases for each command.

6. **Better examples**: When native examples are missing, the LLM can generate realistic examples.

## Example Script

Check out the `examples/llm_enhanced_analysis.py` script for a complete example of using the LLM-enhanced analyzer:

```
python examples/llm_enhanced_analysis.py git ./analysis_results
```

This will analyze the `git` CLI tool and save the results to the `analysis_results` directory.

## Limitations

- The LLM-enhanced analyzer requires internet connectivity to access LLM services.
- Analysis with LLM enhancement is slower than the standard analyzer.
- The quality of the enhancement depends on the quality of the LLM and the prompts used.
- There may be rate limiting or cost considerations depending on your LLM provider.

## Best Practices

- Use the standard analyzer for quick analysis during development.
- Use the LLM-enhanced analyzer for final analysis or when generating comprehensive test plans.
- Cache analysis results to avoid repeated API calls to LLM services.
- Review and validate LLM-generated insights, especially for critical commands.