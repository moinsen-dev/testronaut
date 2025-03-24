# Quick Start Guide

This guide will help you get started with Testronaut by walking through a basic workflow for testing a command-line application.

## Prerequisites

- Testronaut [installed](installation.md)
- A command-line application you want to test

## Basic Workflow

### 1. Analyze Your CLI Tool

First, analyze your command-line tool to understand its structure:

```bash
testronaut analyze --tool /path/to/your/cli-tool
```

This will generate an analysis file (default: `analysis.json`) containing information about the tool's commands, options, and arguments.

### 2. Generate a Test Plan

Next, generate a test plan based on the analysis:

```bash
testronaut generate --analysis-file analysis.json --output test-plan.json
```

The test plan will contain test cases for each command detected in your CLI tool.

### 3. Verify the Tests

Run the tests defined in your test plan:

```bash
testronaut verify --test-plan test-plan.json
```

This will execute each test case and record the results.

### 4. Generate a Report

Finally, generate a report of the test results:

```bash
testronaut report --verification-results verification-results.json --format html
```

This will create a detailed report showing which tests passed and failed.

## Complete Example

Here's a complete example testing a hypothetical CLI tool called `demo-cli`:

```bash
# Analyze the CLI tool
testronaut analyze --tool /usr/local/bin/demo-cli

# Generate a test plan
testronaut generate --analysis-file analysis.json --output test-plan.json

# Optionally, review and modify the test plan
# edit test-plan.json

# Verify the tests
testronaut verify --test-plan test-plan.json

# Generate an HTML report
testronaut report --verification-results verification-results.json --format html
```

## Next Steps

- Learn about [core concepts](concepts.md) to understand how Testronaut works
- Explore the [CLI reference](../reference/cli.md) for detailed command options
- See how to [customize test plans](../guides/customizing-tests.md) for more complex testing scenarios