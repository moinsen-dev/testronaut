# Technical Context

## Technology Stack

Testronaut relies on the following key technologies:

### Core Technologies
- **Python 3.13+**: Main programming language for the application
- **SQLite**: Lightweight database for storing metadata, test plans, and results
- **Docker**: Container platform for isolated test execution
- **Large Language Models**: AI models for analysis, generation, and verification

### Libraries & Frameworks
- **Typer**: Modern CLI framework for Python with type hints
- **LangChain**: Framework for LLM integration and orchestration
- **FastAPI**: API framework for potential future web interface
- **SQLAlchemy**: ORM for database interactions
- **Docker SDK for Python**: Python library for Docker integration
- **Pydantic**: Data validation and settings management
- **Rich**: Terminal formatting and visualization
- **llama-cpp-python**: Python bindings for llama.cpp (for local GGUF models) [Optional Dependency]
- **questionary**: Interactive prompts for CLI
- **huggingface-hub**: Utilities for interacting with Hugging Face Hub (model downloads)

### Development Tools
- **uv**: Primary Python package manager for the project - chosen for its speed and reliability
- **pyproject.toml**: Project metadata and dependency specification
- **pytest**: Testing framework for Python
- **MkDocs**: Documentation generator
- **Black**: Code formatter
- **isort**: Import sorter
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality checks

## Project Structure

The project follows a modular architecture with clear separation of concerns:

```
testronaut/
├── cli/                # Command-line interface
│   ├── __init__.py
│   ├── commands/       # CLI command implementations
│   ├── utils/          # CLI utilities
│   └── main.py         # Entry point
├── core/               # Core business logic
│   ├── __init__.py
│   ├── analyzer/       # CLI tool analysis
│   ├── generator/      # Test plan generation
│   ├── executor/       # Test execution
│   ├── verifier/       # Result verification
│   └── models/         # Data models
├── db/                 # Database management
│   ├── __init__.py
│   ├── models/         # SQLAlchemy models
│   ├── migrations/     # Database migrations
│   └── repositories/   # Data access layer
├── llm/                # LLM integration
│   ├── __init__.py
│   ├── providers/      # LLM provider implementations
│   ├── prompts/        # Prompt templates
│   └── utils/          # LLM utilities
├── docker/             # Docker integration
│   ├── __init__.py
│   ├── containers/     # Container management
│   ├── images/         # Docker image management
│   └── utils/          # Docker utilities
├── utils/              # General utilities
│   ├── __init__.py
│   ├── logging/        # Logging configuration
│   └── config/         # Configuration management
├── tests/              # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test fixtures
└── docs/               # Documentation
```

## Development Environment

### Requirements
- Python 3.13 or higher
- Docker Desktop or Docker Engine
- Git

### Setup Guide
1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment
4. Install development dependencies: `uv pip install -e ".[dev]"`
5. Set up pre-commit hooks: `pre-commit install`
6. Configure your IDE for black, isort, and mypy

### Configuration
The application uses a layered configuration approach:
1. Default configuration values
2. Configuration file overrides
3. Environment variable overrides
4. Command-line argument overrides

Configuration is managed through Pydantic settings classes for validation and type safety.

## Data Model

The core data model consists of these primary entities:

### CLITool
Represents a command-line tool being tested:
- ID, name, version, install command
- Collection of commands
- Help text and description

### Command
Represents a command provided by a CLI tool:
- ID, name, description, syntax
- Collection of options and arguments
- Parent command (for subcommands)

### Option
Represents a command-line option:
- ID, name, short/long forms
- Description, required flag, default value
- Value type (string, int, boolean, etc.)

### Argument
Represents a positional argument:
- ID, name, description
- Required flag, default value, position
- Value type (string, int, boolean, etc.)

### TestPlan
Represents a collection of test cases:
- ID, name, description
- Associated CLI tool
- Collection of test cases

### TestCase
Represents a single test scenario:
- ID, name, description
- Command line to execute
- Expected outputs and exit code
- Dependencies on other test cases

### TestResult
Represents the result of executing a test case:
- ID, associated test case
- Actual outputs and exit code
- Pass/fail status
- Comparison details

## Integration Points

### LLM Integration
- **LLM Manager**: Central component (`DefaultLLMManager`) coordinating providers.
- **Cloud Providers**: OpenAI API, Anthropic API (planned).
- **Local Provider**: `llama-cpp-python` for GGUF models (`LlamaCppProvider`).
- **Mock Provider**: For testing and default initialization (`MockProvider`).
- **Configuration**: Managed via `LLMSettings` in `config.yaml`, including provider selection and specific settings (API keys, model paths).
- **CLI Management**: `testronaut config llm` commands for managing local models.

### Docker Integration
- **Docker SDK**: For container management
- **Docker API**: For direct Docker operations

### File System Integration
- **Test Artifacts**: For storing test outputs
- **Configuration Files**: For storing user settings
- **Database Files**: For SQLite database

## Security Considerations

1. **Containerization**: All test execution occurs in isolated Docker containers
2. **Minimal Permissions**: Containers run with minimal required permissions
3. **Local Model Support**: Option to use local LLMs for sensitive environments
4. **No Sensitive Data**: Avoid sending sensitive data to cloud LLMs
5. **Resource Limitations**: Container resource limits to prevent DoS
