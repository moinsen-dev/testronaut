# Contributing to Testronaut

Thank you for your interest in contributing to Testronaut! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please be respectful and considerate of others.

## Development Environment Setup

### Prerequisites

- Python 3.13 or later
- [uv](https://github.com/astral-sh/uv) for package management

### Setup Steps

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/yourusername/testronaut.git
   cd testronaut
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

   This will:
   - Create a virtual environment
   - Install all dependencies using uv
   - Configure pre-commit hooks

3. **Alternatively, set up manually with uv**:
   ```bash
   # Create virtual environment
   uv venv

   # Install package in development mode
   uv pip install -e ./src

   # Install development dependencies
   uv pip install pytest pytest-cov mypy ruff pre-commit

   # Set up pre-commit hooks
   pre-commit install
   ```

4. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate  # On Unix/macOS
   .venv\Scripts\activate     # On Windows
   ```

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards described below.

3. **Run tests** to ensure your changes don't break existing functionality:
   ```bash
   uv run pytest
   ```

4. **Check code coverage**:
   ```bash
   uv run pytest --cov=src/testronaut
   ```

5. **Ensure code quality with pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

6. **Commit your changes** with a descriptive commit message:
   ```bash
   git commit -m "Add feature: your feature description"
   ```

7. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request** against the main repository.

## Coding Standards

### Python Code

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for all function parameters and return values
- Document all public functions, classes, and methods with docstrings
- Keep lines to a maximum of 88 characters (configured in `pyproject.toml`)
- Use [ruff](https://github.com/charliermarsh/ruff) for linting and formatting

### Test-Driven Development

We follow a test-driven development approach:

1. Write tests before implementation
2. Implement the minimal code to make tests pass
3. Refactor for clarity and maintainability

### Project Structure

The project follows domain-driven design principles:

- Core business logic is separated from infrastructure concerns
- Each module has a clear responsibility
- Follow the repository pattern for data access
- Use dependency injection for component integration

## Pull Request Process

1. **Update documentation** if necessary
2. **Add tests** for new functionality
3. **Ensure all tests pass** and code coverage is maintained
4. **Update the CHANGELOG.md** with details of your changes
5. **Request review** from maintainers

## Issue Reporting

When reporting an issue, please include:

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Environment details (Python version, OS, etc.)
- Any relevant logs or screenshots

## Feature Requests

For feature requests, please provide:

- A clear and descriptive title
- Detailed description of the proposed feature
- Why this feature would be useful
- Any implementation ideas you have

## Release Process

Project maintainers will handle the release process, which includes:

1. Updating version numbers in relevant files
2. Updating the CHANGELOG.md
3. Creating a new GitHub release
4. Publishing to PyPI

## Questions?

If you have any questions or need clarification, please open an issue with the label "question".