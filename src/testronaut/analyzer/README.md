# CLI Analysis Engine

This module provides the core functionality for analyzing command-line interfaces (CLIs). It can extract and structure information about commands, options, arguments, and their relationships.

## Features

- **Command Execution**: Run CLI tools and capture their help output
- **Help Text Parsing**: Extract structured data from CLI help text
- **Relationship Detection**: Identify command hierarchies and relationships
- **LLM Enhancement**: Use large language models to improve analysis results
- **Database Storage**: Save analysis results to a SQLite database
- **Interactive Browser**: Explore CLI tools with a text-based UI

## Usage

The CLI Analysis Engine can be used both programmatically and via the command line.

### Command Line Interface

#### Analyze a CLI Tool

```bash
python -m testronaut analyze tool <tool_name> [--save-to-db] [--verbose]
```

Options:
- `--save-to-db`: Save the analysis to the database
- `--verbose`: Show detailed output during analysis

#### List Tools in Database

```bash
python -m testronaut analyze list-db
```

#### Get Detailed Tool Information

```bash
python -m testronaut analyze get-db <tool_name>
```

#### Save Analysis to JSON File

```bash
python -m testronaut analyze tool <tool_name> --save <output_file.json>
```

#### Launch Database Browser

```bash
python -m testronaut analyze browser [--tool <tool_name>]
```

### Programmatic Usage

```python
from testronaut.analyzer import CLIToolAnalyzer
from testronaut.models.cli_tool import CLITool
from testronaut.repositories.cli_tool import CLIToolRepository

# Create an analyzer
analyzer = CLIToolAnalyzer("my-cli-tool")

# Run the analysis
result = analyzer.analyze()

# Get the structured data
cli_tool: CLITool = result.cli_tool

# Save to database
repo = CLIToolRepository()
saved_tool = repo.save_analysis_results(cli_tool)
```

## Architecture

The CLI Analysis Engine consists of several components:

1. **Analyzer**: Core logic for executing commands and parsing output
2. **Parser**: Converts raw help text into structured data
3. **Enhancer**: Uses LLMs to improve parsing results
4. **Repository**: Handles database storage and retrieval
5. **UI**: Provides interfaces for interacting with analysis results

## Extending the Analyzer

You can extend the analyzer to support more CLI formats by creating custom parsers. Implement the `CLIParser` interface and register your parser with the analyzer.

```python
from testronaut.analyzer.parsers import CLIParser

class MyCustomParser(CLIParser):
    def can_parse(self, help_text: str) -> bool:
        # Determine if this parser can handle the format
        return "My CLI Tool" in help_text

    def parse(self, help_text: str) -> Dict:
        # Parse the help text and return a structured representation
        # ...
```

## Database Browser UI

The database browser is a text-based user interface built with [Textual](https://textual.io/) that allows you to:

- Browse all analyzed CLI tools
- Explore command hierarchies
- View detailed command information
- Search for specific commands

The browser UI is composed of three main panels:
- Left: Tools table listing all analyzed CLI tools
- Middle: Command tree showing the command hierarchy
- Right: Detail panel showing information about the selected command or tool