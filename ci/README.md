# Testronaut CI/CD Testing Tools

This directory contains tools to test Testronaut's CI/CD workflows locally before pushing changes to GitHub. These tools help you validate that your changes will work in the CI environment.

## Available Tools

### 1. test-workflows.sh

A comprehensive tool that uses [Act](https://github.com/nektos/act) to run GitHub Actions workflows locally in Docker containers. Now includes a validation script to check GitHub Actions workflow YAML files.

```bash
# Make executable
chmod +x ci/test-workflows.sh

# Show usage
ci/test-workflows.sh --help

# List available workflows
ci/test-workflows.sh --list

# Run a specific workflow
ci/test-workflows.sh --workflow main.yml

# Run a specific job in a workflow
ci/test-workflows.sh --workflow main.yml --job test

# Validate GitHub Actions workflow files
ci/test-workflows.sh --validate
```

### 2. test-main.sh

Tests the main workflow components (testing, linting) locally without using Docker.

```bash
# Make executable
chmod +x ci/test-main.sh

# Run tests and linting
ci/test-main.sh

# Skip tests
ci/test-main.sh --skip-tests

# Skip linting
ci/test-main.sh --skip-lint

# Run with mypy type checking
ci/test-main.sh --mypy
```

### 3. test-security.sh

Runs the security scanning components (Safety, Bandit) locally in an isolated virtual environment.

```bash
# Make executable
chmod +x ci/test-security.sh

# Run security scans
ci/test-security.sh
```

### 4. test-docs.sh

Tests the documentation building process locally in an isolated virtual environment.

```bash
# Make executable
chmod +x ci/test-docs.sh

# Build and check documentation
ci/test-docs.sh

# Build and serve documentation locally
ci/test-docs.sh --serve
```

### 5. actions-validator.py

A Python script for validating GitHub Actions workflow YAML files. This tool is used by test-workflows.sh but can also be used standalone.

```bash
# Make executable
chmod +x ci/actions-validator.py

# Validate all workflow files
ci/actions-validator.py .github/workflows/*.yml
```

## Docker Workflow Testing

The `Dockerfile.workflows` file provides a Docker environment for testing GitHub Actions workflows using Act. It includes all the necessary tools and dependencies to simulate the GitHub Actions environment, including:

- Python 3.10 and required packages
- uv for dependency management (v0.6.6)
- GitHub Actions validator script
- Security scanning tools (Safety, Bandit)

## GitHub Actions Workflows

Testronaut uses the following GitHub Actions workflows:

1. **main.yml**: Testing and code quality checks
   - Uses actions/checkout@v4.2.2 and actions/setup-python@v5
   - Matrix testing with Python 3.10, 3.11, 3.12, 3.13
   - Uses astral-sh/setup-uv@v5 for dependency management

2. **docs.yml**: Documentation building and publishing
   - Uses Python 3.13 and MkDocs
   - Publishes to GitHub Pages

3. **release.yml**: Package building and publishing
   - Triggers on release creation
   - Publishes to PyPI

4. **security.yml**: Security scanning
   - Weekly scheduled runs
   - Safety and Bandit scanning
   - CodeQL analysis

## Usage Recommendations

1. **Before pushing changes:**
   - Run `ci/test-workflows.sh --validate` to check workflow syntax
   - Run `ci/test-main.sh` to ensure tests and linting pass
   - Run `ci/test-security.sh` if you've changed dependencies
   - Run `ci/test-docs.sh` if you've modified documentation

2. **For workflow changes:**
   - Validate workflow syntax with `ci/test-workflows.sh --validate`
   - Test specific workflows with `ci/test-workflows.sh --workflow <workflow-file>`

3. **For comprehensive testing:**
   - Use `ci/test-workflows.sh` to run full GitHub Actions workflows locally

## Requirements

- Docker installed and running (for `test-workflows.sh`)
- Python 3.10+ for local tools
- Bash shell
- Git

## Limitations

- Some GitHub-specific features like CodeQL might not work fully locally
- Secrets and environment variables need to be configured manually for local testing
- Act has limitations with certain GitHub Actions features

## Setting Up Act

The `test-workflows.sh` script will attempt to install Act if it's not found, but you can also install it manually:

- macOS: `brew install act`
- Linux: `curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash`

Refer to the [Act GitHub repository](https://github.com/nektos/act) for more details on configuration and usage.