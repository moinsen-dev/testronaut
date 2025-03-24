# Data Model Diagram

```mermaid
erDiagram
    CLITool ||--o{ Command : has
    Command ||--o{ Option : has
    Command ||--o{ Argument : has
    Command ||--o{ Example : has
    
    CLITool ||--o{ TestPlan : has
    TestPlan ||--o{ TestCase : contains
    TestCase ||--o{ TestResult : produces
    TestCase }|--|| Command : tests
    
    TestCase ||--o{ Dependency : has
    Dependency }|--|| TestCase : references
    
    TestPlan ||--o{ TestReport : generates
    TestResult }|--o{ TestReport : includes

    CLITool {
        string id PK
        string name
        string version
        string install_command
        string help_text
        string description
        datetime created_at
        datetime updated_at
    }
    
    Command {
        string id PK
        string cli_tool_id FK
        string name
        string description
        string syntax
        string help_text
        boolean is_subcommand
        string parent_command_id FK
        datetime created_at
    }
    
    Option {
        string id PK
        string command_id FK
        string name
        string short_form
        string long_form
        string description
        boolean required
        string default_value
        string value_type
        datetime created_at
    }
    
    Argument {
        string id PK
        string command_id FK
        string name
        string description
        boolean required
        string default_value
        string value_type
        int position
        datetime created_at
    }
    
    Example {
        string id PK
        string command_id FK
        string description
        string command_line
        string expected_output
        datetime created_at
    }
    
    TestPlan {
        string id PK
        string cli_tool_id FK
        string name
        string description
        string generation_prompt
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    
    TestCase {
        string id PK
        string test_plan_id FK
        string command_id FK
        string name
        string description
        string command_line
        int execution_order
        string expected_exit_code
        string expected_stdout
        string expected_stderr
        string expected_files
        boolean should_fail
        datetime created_at
    }
    
    Dependency {
        string id PK
        string test_case_id FK
        string depends_on_test_case_id FK
        string variable_name
        string extraction_pattern
        datetime created_at
    }
    
    TestResult {
        string id PK
        string test_case_id FK
        string actual_exit_code
        string actual_stdout
        string actual_stderr
        string actual_files
        boolean passed
        string comparison_details
        datetime execution_time
        string docker_container_id
        string environment_details
        datetime created_at
    }
    
    TestReport {
        string id PK
        string test_plan_id FK
        string name
        string description
        int total_tests
        int passed_tests
        int failed_tests
        int skipped_tests
        float execution_time
        string summary
        string recommendations
        datetime created_at
    }
```

This entity-relationship diagram shows the data model for the AI-CLI-Testing tool:

1. **CLITool**: Represents the command-line tool being tested, with its metadata
2. **Command**: Individual commands provided by the CLI tool
3. **Option**: Command-line options for commands (e.g., --verbose, -f)
4. **Argument**: Positional arguments for commands
5. **Example**: Example usages of commands with expected outputs
6. **TestPlan**: Collection of test cases for a CLI tool
7. **TestCase**: Individual test scenario with command line and expected outputs
8. **Dependency**: Relationship between test cases (e.g., one test depends on another)
9. **TestResult**: Actual outputs and comparison results from test execution
10. **TestReport**: Summary of test execution results with insights

The relationships show how these entities are connected, such as:
- A CLI tool has many commands
- Commands have options and arguments
- Test plans contain test cases
- Test cases produce test results
- Test cases can depend on other test cases
- Test reports summarize test results

This model supports the full workflow from CLI analysis to test execution and reporting.