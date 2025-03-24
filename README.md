[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/your-username/testronaut)
[![Code Coverage](https://img.shields.io/badge/coverage-48%25-orange.svg)](https://github.com/your-username/testronaut)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/your-username/testronaut/issues)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/your-username/testronaut/graphs/commit-activity)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/your-username/testronaut/discussions)

# Testronaut - testronauting

<div align="center">
  <img src="images/testronaut-logo.png" alt="Testronaut Logo" width="300"/>
  <p><em>AI-powered testing for CLI tools</em></p>
</div>

Testronaut is an AI-powered, containerized framework for end-to-end testing of CLI tools. It analyzes commands, generates test plans, verifies outputs semantically with LLMs, and runs everything safely in Docker.


# testronauting

An intelligent, AI-driven framework for automating end-to-end testing of command-line interface (CLI) tools.

## Overview

testronauting replaces traditional, brittle test scripts with an AI-powered system that:

1. **Analyzes CLI tools** to understand their structure and capabilities
2. **Generates comprehensive test plans** covering various use cases and edge conditions
3. **Executes tests in isolated Docker containers** for safety and reproducibility
4. **Verifies results using semantic comparison** rather than exact string matching

This approach dramatically reduces the effort required to create and maintain CLI tests while providing more robust coverage.

<div align="center">
  <img src="images/testronaut-workflow.png" alt="Testronaut Workflow" width="700"/>
  <p><em>Testronaut's end-to-end testing workflow</em></p>
</div>

## Key Features

- **AI-Based Command Analysis**: Automatically understand CLI structure from help text
- **Intelligent Test Generation**: Create comprehensive test plans with minimal input
- **Containerized Execution**: Run tests in isolated Docker environments
- **Semantic Result Verification**: Compare outputs based on meaning, not exact matches
- **Model Flexibility**: Support for both cloud and local LLMs for cost efficiency

## Getting Started

### Development Setup

We use [uv](https://github.com/astral-sh/uv) for fast, reliable Python packaging. Make sure it's installed first:

```bash
# Install uv
curl -L --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh
```

Then set up the project:

```bash
# Clone the repository
git clone https://github.com/yourusername/testronaut.git
cd testronaut

# Run the setup script (creates venv and installs dependencies with uv)
./setup.sh

# Activate the virtual environment
source .venv/bin/activate
```

Alternatively, set up manually with uv:

```bash
# Create virtual environment
uv venv

# Install the package in development mode
uv pip install -e ./src

# Install development dependencies
uv pip install pytest pytest-cov mypy ruff pre-commit
```

### Installation for Users

```bash
# Install from PyPI using uv (recommended)
uv pip install testronauting

# Or install with pip
pip install testronauting

# For local model support
uv pip install "testronauting[local]"
```

### Running Tests

Use uv to run tests for better performance:

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/testronaut
```

### Basic Usage

```bash
# Analyze a CLI tool and generate a test plan
testronaut analyze --tool my-cli-tool

# Generate expected results (baseline)
testronaut generate --plan my-test-plan

# Verify against expected results
testronaut verify --plan my-test-plan

# Generate a test report
testronaut report --plan my-test-plan
```

## Use Cases

testronauting is ideal for:

- **CLI Tool Developers**: Ensure your tools work as expected across environments
- **DevOps Engineers**: Validate CLI tools in CI/CD pipelines
- **QA Engineers**: Automate testing of command-line interfaces
- **Open Source Maintainers**: Scale testing of CLI projects with minimal effort

## Technical Architecture

<div align="center">
  <img src="images/testronaut-architecture.png" alt="Testronaut Architecture" width="700"/>
  <p><em>Testronaut's component architecture</em></p>
</div>

The system consists of five main components:

1. **CLI Analyzer**: Parses and understands command structure
2. **Test Generator**: Creates comprehensive test plans
3. **Test Executor**: Runs tests in Docker containers
4. **Result Verifier**: Compares expected vs. actual results
5. **LLM Integration**: Powers the AI capabilities

## Roadmap

Check our [CHANGELOG.md](CHANGELOG.md) for recent updates and our project board for upcoming features.

## Support

If you're having issues or have questions, please:

- Check the [documentation](https://github.com/your-username/testronaut/wiki)
- Open an [issue](https://github.com/your-username/testronaut/issues/new/choose)
- Join our [discussions](https://github.com/your-username/testronaut/discussions)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to Testronaut.

Key points:
- We use [uv](https://github.com/astral-sh/uv) for package management
- Follow test-driven development principles
- Use pre-commit hooks for code quality
- Maintain code coverage above our current baseline

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Author**: Ulrich Diedrichsen
- **Email**: uli@moinsen.dev
- **Website**: www.moinsen.dev
