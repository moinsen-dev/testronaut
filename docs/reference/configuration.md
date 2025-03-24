# Configuration

Testronaut can be configured through various methods to customize its behavior. This document details the available configuration options and how to set them.

## Configuration Methods

Testronaut supports multiple configuration methods, with the following precedence (highest to lowest):

1. Command-line arguments
2. Environment variables
3. Configuration file
4. Default values

## Configuration File

Testronaut looks for a configuration file in the following locations:

1. Path specified by the `--config` command-line option
2. `.testronaut.yml` or `.testronaut.yaml` in the current directory
3. `testronaut.yml` or `testronaut.yaml` in the current directory
4. `~/.config/testronaut/config.yml`

### Example Configuration File

```yaml
# Basic configuration
output_dir: ./testronaut-output
log_level: INFO
verbose: false

# Analysis configuration
analyzer:
  max_depth: 3
  skip_subcommands: false
  timeout: 30  # seconds
  analyze_help_text: true

# Test generation configuration
generator:
  test_scope: comprehensive  # basic, comprehensive, exhaustive
  test_cases: 10
  enhance: true
  include_edge_cases: true
  prioritize_commands: ["init", "add", "commit", "push"]

# Test execution configuration
executor:
  use_docker: true
  docker_image: ubuntu:latest
  timeout: 60  # seconds
  capture_stderr: true
  capture_stdout: true
  retry_count: 2

# AI configuration
ai:
  provider: openai  # openai, anthropic, local
  model: gpt-4
  temperature: 0.2
  max_tokens: 1000
  anthropic_model: claude-3-opus

# Reporting configuration
reporting:
  format: html  # html, json, md, pdf
  include_logs: true
  include_screenshots: true
  include_test_steps: true
  include_command_output: true
```

## Environment Variables

All configuration options can be set through environment variables with the prefix `TESTRONAUT_`. Nested options use underscores to separate levels.

Examples:

```bash
# Basic configuration
export TESTRONAUT_OUTPUT_DIR=./testronaut-output
export TESTRONAUT_LOG_LEVEL=INFO
export TESTRONAUT_VERBOSE=false

# Analysis configuration
export TESTRONAUT_ANALYZER_MAX_DEPTH=3
export TESTRONAUT_ANALYZER_SKIP_SUBCOMMANDS=false

# Test generation configuration
export TESTRONAUT_GENERATOR_TEST_SCOPE=comprehensive
export TESTRONAUT_GENERATOR_TEST_CASES=10

# AI configuration
export TESTRONAUT_AI_PROVIDER=openai
export TESTRONAUT_AI_MODEL=gpt-4
```

## Configuration Reference

### Basic Configuration

| Option | Description | Default | CLI Flag | Environment Variable |
| ------ | ----------- | ------- | -------- | ------------------- |
| `output_dir` | Directory for output files | `./` | `--output-dir` | `TESTRONAUT_OUTPUT_DIR` |
| `log_level` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` | `--log-level` | `TESTRONAUT_LOG_LEVEL` |
| `verbose` | Enable verbose output | `false` | `--verbose` | `TESTRONAUT_VERBOSE` |
| `quiet` | Suppress non-error output | `false` | `--quiet` | `TESTRONAUT_QUIET` |

### Analyzer Configuration

| Option | Description | Default | CLI Flag | Environment Variable |
| ------ | ----------- | ------- | -------- | ------------------- |
| `analyzer.max_depth` | Maximum depth for subcommand analysis | `3` | `--max-depth` | `TESTRONAUT_ANALYZER_MAX_DEPTH` |
| `analyzer.skip_subcommands` | Skip analyzing subcommands | `false` | `--skip-subcommands` | `TESTRONAUT_ANALYZER_SKIP_SUBCOMMANDS` |
| `analyzer.timeout` | Timeout for command analysis in seconds | `30` | `--timeout` | `TESTRONAUT_ANALYZER_TIMEOUT` |
| `analyzer.analyze_help_text` | Analyze command help text | `true` | `--skip-help-text` | `TESTRONAUT_ANALYZER_ANALYZE_HELP_TEXT` |

### Generator Configuration

| Option | Description | Default | CLI Flag | Environment Variable |
| ------ | ----------- | ------- | -------- | ------------------- |
| `generator.test_scope` | Scope of test generation (basic, comprehensive, exhaustive) | `comprehensive` | `--test-scope` | `TESTRONAUT_GENERATOR_TEST_SCOPE` |
| `generator.test_cases` | Number of test cases to generate | `10` | `--test-cases` | `TESTRONAUT_GENERATOR_TEST_CASES` |
| `generator.enhance` | Use AI to enhance test plans | `false` | `--enhance` | `TESTRONAUT_GENERATOR_ENHANCE` |
| `generator.include_edge_cases` | Include edge cases in test plan | `true` | `--skip-edge-cases` | `TESTRONAUT_GENERATOR_INCLUDE_EDGE_CASES` |
| `generator.prioritize_commands` | List of commands to prioritize in testing | `[]` | `--prioritize` | `TESTRONAUT_GENERATOR_PRIORITIZE_COMMANDS` |

### Executor Configuration

| Option | Description | Default | CLI Flag | Environment Variable |
| ------ | ----------- | ------- | -------- | ------------------- |
| `executor.use_docker` | Run tests in Docker container | `false` | `--docker` | `TESTRONAUT_EXECUTOR_USE_DOCKER` |
| `executor.docker_image` | Docker image to use for testing | `ubuntu:latest` | `--image` | `TESTRONAUT_EXECUTOR_DOCKER_IMAGE` |
| `executor.timeout` | Timeout for test execution in seconds | `60` | `--exec-timeout` | `TESTRONAUT_EXECUTOR_TIMEOUT` |
| `executor.capture_stderr` | Capture standard error output | `true` | `--no-stderr` | `TESTRONAUT_EXECUTOR_CAPTURE_STDERR` |
| `executor.capture_stdout` | Capture standard output | `true` | `--no-stdout` | `TESTRONAUT_EXECUTOR_CAPTURE_STDOUT` |
| `executor.retry_count` | Number of retries for failed tests | `0` | `--retry` | `TESTRONAUT_EXECUTOR_RETRY_COUNT` |

### AI Configuration

| Option | Description | Default | CLI Flag | Environment Variable |
| ------ | ----------- | ------- | -------- | ------------------- |
| `ai.provider` | AI provider (openai, anthropic, local) | `openai` | `--ai-provider` | `TESTRONAUT_AI_PROVIDER` |
| `ai.model` | Model name for OpenAI | `gpt-4` | `--ai-model` | `TESTRONAUT_AI_MODEL` |
| `ai.temperature` | Temperature for AI generation | `0.2` | `--ai-temperature` | `TESTRONAUT_AI_TEMPERATURE` |
| `ai.max_tokens` | Maximum tokens for AI generation | `1000` | `--ai-max-tokens` | `TESTRONAUT_AI_MAX_TOKENS` |
| `ai.anthropic_model` | Model name for Anthropic | `claude-3-opus` | `--anthropic-model` | `TESTRONAUT_AI_ANTHROPIC_MODEL` |

### Reporting Configuration

| Option | Description | Default | CLI Flag | Environment Variable |
| ------ | ----------- | ------- | -------- | ------------------- |
| `reporting.format` | Report format (html, json, md, pdf) | `html` | `--format` | `TESTRONAUT_REPORTING_FORMAT` |
| `reporting.include_logs` | Include logs in report | `true` | `--no-logs` | `TESTRONAUT_REPORTING_INCLUDE_LOGS` |
| `reporting.include_screenshots` | Include screenshots in report | `true` | `--no-screenshots` | `TESTRONAUT_REPORTING_INCLUDE_SCREENSHOTS` |
| `reporting.include_test_steps` | Include test steps in report | `true` | `--no-steps` | `TESTRONAUT_REPORTING_INCLUDE_TEST_STEPS` |
| `reporting.include_command_output` | Include command output in report | `true` | `--no-output` | `TESTRONAUT_REPORTING_INCLUDE_COMMAND_OUTPUT` |
