# Advanced CLI Analysis Techniques

The Testronaut framework includes sophisticated analysis techniques to handle complex CLI tools with deep command hierarchies. This guide explains two key features: two-phase analysis and cycle detection.

## Two-Phase Analysis

The CLI analyzer uses a two-phase approach to analyze complex command-line tools:

### Phase 1: Command Discovery

In the first phase, the analyzer focuses on building a complete command tree structure without performing detailed analysis:

1. The analyzer starts by extracting the top-level commands from the main help text
2. For each command, it retrieves the help text and extracts its immediate subcommands
3. This process continues recursively to discover the entire command hierarchy
4. Command relationships (parent-child) are established during this phase
5. The analyzer tracks processed commands to avoid re-analyzing the same command

This approach allows the analyzer to quickly build a comprehensive view of the command structure before diving into detailed analysis.

### Phase 2: Detailed Analysis

Once the command tree is built, the analyzer proceeds to the second phase:

1. Each command is analyzed individually in a sequential manner
2. The analyzer extracts detailed information such as:
   - Command descriptions
   - Available options (flags)
   - Required and optional arguments
   - Usage examples
   - Syntax patterns
3. The analyzer enriches each command with this detailed information
4. Progress is reported for each command being analyzed

This separation ensures that even complex CLI tools with hundreds of commands can be analyzed efficiently and without encountering infinite loops.

## Cycle Detection

CLI tools often have command structures that can create cycles in the command graph, which can lead to infinite loops during analysis. Testronaut implements robust cycle detection:

### Types of Cycles

1. **Self-references**: Commands that appear to reference themselves (e.g., "show" command having a "Show" subcommand)
2. **Parent-child cycles**: Subcommands that reference their parent commands
3. **Deep cycles**: Complex relationships where a command eventually references itself through multiple levels

### Cycle Detection Approach

The analyzer implements cycle detection through:

1. **Command ID tracking**: Each command gets a unique identifier
2. **Processed command set**: A set of command IDs that have already been processed is maintained
3. **Cycle detection**: Before processing a command, the analyzer checks if it's already in the processed set
4. **Warning logs**: When a potential cycle is detected, a warning is logged for transparency
5. **Cycle breaking**: The analyzer skips processing commands that would create cycles

### Example

Consider a CLI tool with commands like:

```
tool command subcommand
tool command subcommand Command
```

Without cycle detection, the analyzer might enter an infinite loop when it encounters "Command" as both a parent and a child. The cycle detection mechanism identifies this pattern and prevents the loop.

## Detailed Progress Reporting

To provide transparency during analysis, the analyzer implements detailed progress reporting:

1. **Step-by-step logging**: Each phase and step is logged with timestamps
2. **Command counting**: The total number of commands discovered is reported
3. **Progress indicators**: Visual indicators show which command is being analyzed
4. **Cycle warnings**: Warnings are issued when cycles are detected and broken
5. **Performance metrics**: The time taken for analysis is tracked and reported

## Usage Example

To leverage these advanced features:

```python
from testronaut.analyzers import StandardAnalyzer

# Initialize the analyzer
analyzer = StandardAnalyzer()

# Enable verbose mode for detailed progress reporting
analyzer.verbose = True

# Analyze a complex CLI tool
cli_tool = analyzer.analyze_cli_tool("complex-cli")

# Access the complete command hierarchy
print(f"Discovered {len(cli_tool.commands)} commands")
```

## CLI Usage

From the command line:

```bash
testronaut analyze tool complex-cli --verbose
```

The `--verbose` flag enables detailed progress reporting, showing each phase of the analysis process.

## Best Practices

- Use the `--verbose` flag when analyzing complex CLI tools to monitor progress
- Check the logs for cycle detection warnings, which might indicate unusual command structures
- For very complex CLI tools, consider analyzing subsets of commands rather than the entire tool
- Cache analysis results to avoid repeated analysis of the same tool