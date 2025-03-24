# API Overview

Testronaut provides a comprehensive Python API that can be used programmatically in your applications and workflows. This document provides an overview of the main API components.

## Core Modules

Testronaut's API is organized into several key modules:

- **Core**: Contains the main business logic components
- **CLI**: Command-line interface components
- **Models**: Data models for test plans and analysis
- **Utils**: Utility functions and helpers

## Getting Started

To use Testronaut in your Python code, start by importing the relevant modules:

```python
from testronaut.core.analyzer import CLIAnalyzer
from testronaut.core.generator import TestPlanGenerator
from testronaut.core.executor import TestExecutor
from testronaut.core.models.test_plan import TPTestPlan, TPTestCase
```

## Basic Usage

Here's a simple example that demonstrates how to use the Testronaut API to analyze a CLI tool and generate a test plan:

```python
from testronaut.core.analyzer import CLIAnalyzer
from testronaut.core.generator import TestPlanGenerator

# Analyze a CLI tool
analyzer = CLIAnalyzer(tool_path="/usr/bin/git")
analysis_result = analyzer.analyze()

# Generate a test plan
generator = TestPlanGenerator(analysis=analysis_result)
test_plan = generator.generate()

# Save the test plan to a file
test_plan.save("git_test_plan.json")

# Load a test plan from a file
from testronaut.core.models.test_plan import TPTestPlan
loaded_test_plan = TPTestPlan.load("git_test_plan.json")

# Execute the test plan
from testronaut.core.executor import TestExecutor
executor = TestExecutor(test_plan=loaded_test_plan, tool_path="/usr/bin/git")
results = executor.execute()

# Generate a report
from testronaut.core.reporting import ReportGenerator
reporter = ReportGenerator(results=results)
reporter.generate_report(format="html", output_path="git_test_report.html")
```

## Main Components

### CLIAnalyzer

The `CLIAnalyzer` class is responsible for analyzing command-line tools to understand their structure, commands, and options.

```python
from testronaut.core.analyzer import CLIAnalyzer

analyzer = CLIAnalyzer(
    tool_path="/usr/bin/docker",
    max_depth=3,
    skip_subcommands=False,
    timeout=30
)
analysis = analyzer.analyze()
analysis.save("docker_analysis.json")
```

### TestPlanGenerator

The `TestPlanGenerator` class creates test plans based on CLI analysis results.

```python
from testronaut.core.generator import TestPlanGenerator
from testronaut.core.models.cli_tool import CLITool

# Create from an analysis result
generator = TestPlanGenerator(analysis=analysis_result)

# Or directly from a CLI tool model
cli_tool = CLITool.load("docker_analysis.json")
generator = TestPlanGenerator(cli_tool=cli_tool)

# Generate a test plan
test_plan = generator.generate(
    test_scope="comprehensive",
    test_cases=10,
    enhance=True
)
```

### TestExecutor

The `TestExecutor` class runs test plans against CLI tools.

```python
from testronaut.core.executor import TestExecutor
from testronaut.core.models.test_plan import TPTestPlan

# Load a test plan
test_plan = TPTestPlan.load("docker_test_plan.json")

# Create an executor
executor = TestExecutor(
    test_plan=test_plan,
    tool_path="/usr/bin/docker",
    use_docker=True,
    docker_image="ubuntu:latest"
)

# Execute the tests
results = executor.execute()
```

### TPTestPlan and TPTestCase

The `TPTestPlan` and `TPTestCase` classes represent test plans and test cases, respectively.

```python
from testronaut.core.models.test_plan import TPTestPlan, TPTestCase, TestStep, TestStepType

# Create a test step
step = TestStep(
    type=TestStepType.COMMAND,
    command="git init",
    expected_output="Initialized empty Git repository",
    expected_exit_code=0
)

# Create a test case
test_case = TPTestCase(
    name="Test Git Init",
    description="Test the git init command",
    steps=[step]
)

# Create a test plan
test_plan = TPTestPlan(
    name="Git Test Plan",
    description="Test plan for Git",
    target="git",
    test_cases=[test_case]
)

# Save the test plan
test_plan.save("git_test_plan.json")
```

## Error Handling

Testronaut provides several exception classes for handling errors:

```python
from testronaut.core.exceptions import (
    TestronaughtError,
    AnalysisError,
    GenerationError,
    ExecutionError,
    ValidationError
)

try:
    analysis = analyzer.analyze()
except AnalysisError as e:
    print(f"Analysis failed: {e}")
```

## Advanced Usage

### Custom Test Plan Enhancement

You can use the AI enhancement capabilities to improve test plans:

```python
from testronaut.core.enhancer import TestPlanEnhancer

enhancer = TestPlanEnhancer(
    provider="openai",
    model="gpt-4"
)

enhanced_plan = enhancer.enhance(test_plan)
```

### Docker Integration

For isolated test execution, you can use Docker:

```python
from testronaut.core.executor import DockerExecutor

docker_executor = DockerExecutor(
    test_plan=test_plan,
    tool_path="/usr/bin/npm",
    image="node:16",
    timeout=60
)

results = docker_executor.execute()
```

## Next Steps

- Explore the [Core API](core.md) for detailed information on analyzer and generator classes
- Check the [CLI API](cli.md) to understand how the command-line interface is implemented
- Review the [Models API](models.md) for details on data structures