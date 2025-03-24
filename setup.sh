#!/bin/bash
set -e

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it first:"
    echo "curl -sSf https://install.python-poetry.org | python3 -"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -e ./src

# Install dev dependencies
echo "Installing development dependencies..."
uv pip install pytest pytest-cov mypy ruff pre-commit

# Set up pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install

echo "Setup complete! You can now activate the virtual environment with:"
echo "source .venv/bin/activate"