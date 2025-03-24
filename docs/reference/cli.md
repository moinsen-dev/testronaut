# CLI Reference

Testronaut provides a comprehensive command-line interface for analyzing CLI tools, generating test plans, and executing tests.

## Global Options

| Option | Description |
| ------ | ----------- |
| `--help` | Show the help message and exit |
| `--version` | Show the version and exit |
| `--verbose` | Enable verbose output |
| `--quiet` | Suppress non-error output |
| `--log-level [LEVEL]` | Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

## Commands

### analyze

Analyze a CLI tool and create an analysis file.

```bash
testronaut analyze [OPTIONS] TOOL_PATH
```

#### Options

| Option | Description |
| ------ | ----------- |
| `--output-dir PATH` | Directory to store the analysis output [default: current directory] |
| `--output-file TEXT` | Name of the output file [default: analysis.json] |
| `--skip-subcommands` | Skip analyzing subcommands |
| `--max-depth INTEGER` | Maximum depth for subcommand analysis [default: 3] |
| `--help` | Show the command help message and exit |

#### Examples

```bash
# Analyze a CLI tool
testronaut analyze /usr/bin/docker

# Analyze with custom output location
testronaut analyze /usr/bin/git --output-dir ./git-tests --output-file git-analysis.json

# Limit analysis depth
testronaut analyze /usr/bin/npm --max-depth 2
```

### generate

Generate a test plan from an analysis file.

```bash
testronaut generate [OPTIONS] ANALYSIS_PATH
```

#### Options

| Option | Description |
| ------ | ----------- |
| `--output-dir PATH` | Directory to store the test plan [default: current directory] |
| `--output-file TEXT` | Name of the output file [default: test_plan.json] |
| `--test-scope [basic\|comprehensive\|exhaustive]` | Scope of the test plan [default: comprehensive] |
| `--test-cases INTEGER` | Number of test cases to generate [default: 10] |
| `--enhance` | Use AI to enhance the test plan |
| `--help` | Show the command help message and exit |

#### Examples

```bash
# Generate a test plan from an analysis file
testronaut generate ./analysis.json

# Generate a comprehensive test plan with more test cases
testronaut generate ./docker-analysis.json --test-scope exhaustive --test-cases 20

# Generate a test plan with AI enhancements
testronaut generate ./npm-analysis.json --enhance
```

### execute

Execute a test plan against a CLI tool.

```bash
testronaut execute [OPTIONS] TEST_PLAN_PATH TOOL_PATH
```

#### Options

| Option | Description |
| ------ | ----------- |
| `--output-dir PATH` | Directory to store test results [default: current directory] |
| `--output-file TEXT` | Name of the output file [default: test_results.json] |
| `--docker` | Run tests in a Docker container |
| `--image TEXT` | Docker image to use for testing [default: ubuntu:latest] |
| `--help` | Show the command help message and exit |

#### Examples

```bash
# Execute a test plan
testronaut execute ./test_plan.json /usr/bin/docker

# Execute tests in a Docker container
testronaut execute ./git-test-plan.json /usr/bin/git --docker

# Execute with a specific Docker image
testronaut execute ./npm-test-plan.json /usr/bin/npm --docker --image node:16
```

### verify

Verify test results semantically using AI.

```bash
testronaut verify [OPTIONS] TEST_RESULTS_PATH
```

#### Options

| Option | Description |
| ------ | ----------- |
| `--output-dir PATH` | Directory to store verification results [default: current directory] |
| `--output-file TEXT` | Name of the output file [default: verification_results.json] |
| `--detailed` | Generate detailed verification reports |
| `--help` | Show the command help message and exit |

#### Examples

```bash
# Verify test results
testronaut verify ./test_results.json

# Verify with detailed reports
testronaut verify ./docker-test-results.json --detailed
```

### report

Generate reports from test results.

```bash
testronaut report [OPTIONS] TEST_RESULTS_PATH
```

#### Options

| Option | Description |
| ------ | ----------- |
| `--output-dir PATH` | Directory to store reports [default: current directory] |
| `--format [html\|json\|md\|pdf]` | Report format [default: html] |
| `--template PATH` | Custom report template |
| `--help` | Show the command help message and exit |

#### Examples

```bash
# Generate an HTML report
testronaut report ./test_results.json

# Generate a PDF report
testronaut report ./git-test-results.json --format pdf

# Use a custom template
testronaut report ./npm-test-results.json --template ./my-template.html
```

### workflow

Run a complete analysis, generation, execution, and reporting workflow.

```bash
testronaut workflow [OPTIONS] TOOL_PATH
```

#### Options

| Option | Description |
| ------ | ----------- |
| `--output-dir PATH` | Directory to store all outputs [default: current directory] |
| `--test-scope [basic\|comprehensive\|exhaustive]` | Scope of the test plan [default: comprehensive] |
| `--docker` | Run tests in a Docker container |
| `--image TEXT` | Docker image to use for testing [default: ubuntu:latest] |
| `--report-format [html\|json\|md\|pdf]` | Report format [default: html] |
| `--help` | Show the command help message and exit |

#### Examples

```bash
# Run a complete workflow
testronaut workflow /usr/bin/docker

# Run a comprehensive workflow with Docker
testronaut workflow /usr/bin/git --test-scope exhaustive --docker

# Generate a PDF report
testronaut workflow /usr/bin/npm --report-format pdf
```