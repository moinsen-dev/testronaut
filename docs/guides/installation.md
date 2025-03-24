# Installation Guide

Testronaut is a Python package that can be installed using pip or other package managers.

## Requirements

- Python 3.10 or higher
- pip or another Python package manager

## Installation Methods

### Using pip

The simplest way to install Testronaut is via pip:

```bash
pip install testronaut
```

### Using uv (Recommended)

For faster installation, you can use [uv](https://github.com/astral-sh/uv):

```bash
uv pip install testronaut
```

### Development Installation

If you want to contribute to Testronaut or need the latest features, you can install directly from GitHub:

```bash
git clone https://github.com/yourusername/testronaut.git
cd testronaut
pip install -e ".[dev]"
```

## Verifying Installation

After installation, you can verify that Testronaut was installed correctly by running:

```bash
testronaut --version
```

This should display the version number of the installed package.

## Updating Testronaut

To update Testronaut to the latest version:

```bash
pip install --upgrade testronaut
```

## Dependencies

Testronaut depends on the following key packages:

- **typer**: For building the command-line interface
- **rich**: For enhanced terminal output
- **pydantic**: For data validation and settings management

These dependencies will be automatically installed when you install Testronaut.

## Troubleshooting

If you encounter issues during installation:

1. Make sure you're using Python 3.10 or higher: `python --version`
2. Ensure pip is up to date: `pip install --upgrade pip`
3. Check for any error messages in the installation output
4. Try installing with the verbose flag: `pip install -v testronaut`

If problems persist, please [open an issue](https://github.com/yourusername/testronaut/issues) on the GitHub repository.