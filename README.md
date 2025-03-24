# Testronaut - testronauting

Testronaut is an AI-powered, containerized framework for end-to-end testing of CLI tools. It analyzes commands, generates test plans, verifies outputs semantically with LLMs, and runs everything safely in Docker.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/your-username/testronaut)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/your-username/testronaut/issues)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/your-username/testronaut/graphs/commit-activity)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://github.com/your-username/testronaut/discussions)

# testronauting

An intelligent, AI-driven framework for automating end-to-end testing of command-line interface (CLI) tools.

## Overview

testronauting replaces traditional, brittle test scripts with an AI-powered system that:

1. **Analyzes CLI tools** to understand their structure and capabilities
2. **Generates comprehensive test plans** covering various use cases and edge conditions
3. **Executes tests in isolated Docker containers** for safety and reproducibility
4. **Verifies results using semantic comparison** rather than exact string matching

This approach dramatically reduces the effort required to create and maintain CLI tests while providing more robust coverage.

## Key Features

- **AI-Based Command Analysis**: Automatically understand CLI structure from help text
- **Intelligent Test Generation**: Create comprehensive test plans with minimal input
- **Containerized Execution**: Run tests in isolated Docker environments
- **Semantic Result Verification**: Compare outputs based on meaning, not exact matches
- **Model Flexibility**: Support for both cloud and local LLMs for cost efficiency

## Getting Started

### Installation

```bash
# Install from PyPI
pip install testronauting

# Or install with local model support
pip install testronauting[local]
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

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Author**: Ulrich Diedrichsen
- **Email**: uli@moinsen.dev
- **Website**: www.moinsen.dev
