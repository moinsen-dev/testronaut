# Active Context

## Current Focus
We are primarily focused on Phase 5: Test Plan Generator. However, due to the need to manage LLM costs, we have also prioritized and started implementing foundational support for local LLMs (originally planned for Phase 8).

Current work streams:
1.  **Phase 5: Test Plan Generator**: Building the component that creates test plans from CLI analysis results.
2.  **LLM Management & Local Provider**: Implementing the core `LLMManager` and adding support for `llama-cpp-python` to enable local model usage.

## Most Recent Phase Completion

### Phase 4: CLI Analysis Engine - Completed
We've successfully implemented the CLI Analysis Engine, which can:
- Extract commands, subcommands, options, and arguments from CLI tools
- Build command hierarchies and maintain proper relationships
- Handle various help text formats and patterns
- Generate structured output for use in test generation
- Process complex command hierarchies using two-phase analysis and cycle detection
- Provide detailed progress reporting through verbose logging
- Fall back to LLM-based analysis for challenging CLI formats

The analyzer provides a solid foundation for the test plan generator we're now building.

## Current Technical Challenges

1. **Test Plan Structure**: Designing a flexible yet structured model for test plans
2. **Test Case Generation**: Using LLMs to generate meaningful test cases for different command types
3. **Expected Output Prediction**: Accurately predicting command outputs in various scenarios
4. **Coverage Optimization**: Ensuring generated test plans achieve good coverage of CLI functionality

## Current Component Development

We are developing the following components:

1. **TestPlan Model**: Data structure to represent comprehensive test plans
2. **TestCase Model**: Representation of individual test cases with expected outcomes
3. **TestGenerator Interface**: Abstract definition of test generation capabilities
4. **StandardTestGenerator**: Concrete implementation using LLM services
5. **CLI Integration**: Command-line interface for test plan generation

## Implementation Progress

- Core architecture is implemented.
- CLI analyzer is complete.
- **Discovered LLM Manager implementation was missing.**
- **Implemented foundational LLM Manager (`DefaultLLMManager`).**
- **Implemented basic `LlamaCppProvider` for local models.**
- **Configured `llama-cpp-python` as an optional dependency.**
- Beginning work on Phase 5 (Test Plan Generator) models and interfaces.

## Next Immediate Steps

1.  **Phase 5:** Define `TestPlan`/`TestCase` models, `TestGenerator` interface.
2.  **LLM:** Complete implementation of `DefaultLLMManager` methods (delegation, prompting).
3.  **LLM:** Complete implementation of `LlamaCppProvider` methods.
4.  **LLM:** Add configuration handling for passing settings to the provider.
5.  **Phase 5:** Implement `StandardTestGenerator` (depends on LLM Manager).
6.  **Phase 5:** Design LLM prompts for test generation.
7.  **Phase 5:** Integrate test generation with the CLI.

## Development Context

The project is using a domain-driven design approach with clear separation of concerns. We're focusing on maintainable, testable code with high coverage and clear documentation.

### Current Status

- Phase 000 (Project Setup) is complete
- Phase 001 (Testing Infrastructure) is complete
- Phase 002 (CI/CD Pipeline) is complete
- Phase 003 (Core Architecture) is complete
- Phase 004 (CLI Analysis Engine) is complete
- Phase 005 (Test Plan Generator) is now in progress
- The codebase has good test coverage (72%) and passing tests

Phase 004 - CLI Analysis Engine is now **complete**. The following features have been implemented:

1. **CLI Analysis Core**
   - Command execution and help text extraction
   - Help text parsing and structure detection
   - Relationship modeling between commands, options, and arguments

2. **LLM-Enhanced Analysis**
   - Improved detection of command relationships
   - Better handling of complex formats
   - Enhanced descriptions and usage examples

3. **Data Storage and Retrieval**
   - Database schema for CLI tools and commands
   - Repository pattern implementation
   - Search and retrieval functionality
   - Interactive database browser with Textual UI

4. **Command Line Interface**
   - `analyze tool [tool_name]` - Analyze a CLI tool
   - `analyze save [file]` - Save analysis to JSON file
   - `analyze list-db` - List analyzed tools in database
   - `analyze get-db [tool_name]` - Get detailed info for a specific tool
   - `analyze browser` - Launch interactive database browser

We are now ready to move to Phase 005 - Test Plan Generator implementation.

### Recent Activities
1. Added a UI database browser for CLI tools using Textual framework
2. Added database storage for CLI analysis results
3. Improved CLI analysis output formatting with cleaner help text in JSON
4. Changed CLI analyzer log level from INFO to DEBUG for cleaner output
5. Fixed security workflow to correctly configure dependency review action
6. Fixed docs workflow to include all required MkDocs plugins (autorefs, mkdocstrings)
7. Optimized CI/CD workflow to run tests only on Python 3.13 for faster execution
8. Prepared for test plan generation implementation
9. **Identified missing LLM Manager implementation.**
10. **Created foundational LLM Manager (`DefaultLLMManager`).**
11. **Created `LlamaCppProvider` structure.**
12. **Created `BaseLLMProvider` protocol.**
13. **Moved `llama-cpp-python` to optional dependencies.**
14. **Installed `llama-cpp-python` dependency.**
15. **Added `llama-cpp` configuration structure (`RegisteredModel`, list) to `LLMSettings`.**
16. **Implemented provider loading in `DefaultLLMManager`.**
17. **Registered `DefaultLLMManager` with the factory.**
18. **Implemented Hugging Face GGUF download utility.**
19. **Refactored `config` CLI command:** Removed `test-llm`, added `llm` subcommand group with `add`, `list`, `remove`, `set` commands for local model management.

## Current Tasks

### Phase 5: Test Plan Generator
1. TestPlan Model
   - [ ] Define the data structure for comprehensive test plans
   - [ ] Implement the TestPlan model
2. TestCase Model
   - [ ] Define the data structure for individual test cases
   - [ ] Implement the TestCase model
3. TestGenerator Interface
   - [ ] Define the abstract interface for test generation capabilities
   - [ ] Implement the TestGenerator interface
4. StandardTestGenerator
   - [ ] Create the concrete implementation (depends on LLM Manager)
   - [ ] Implement the StandardTestGenerator class
5. CLI Integration
   - [ ] Design the command-line interface for test plan generation
   - [ ] Implement the CLI integration

### LLM Management & Local Provider (Prioritized from Phase 8)
1. DefaultLLMManager Implementation
   - [ ] Implement delegation/prompting for `classify`
   - [ ] Implement delegation/prompting for `extract_structured_data`
   - [ ] Implement delegation/prompting for `analyze_help_text`
   - [ ] Implement delegation/prompting for `compare_outputs`
   - [ ] Implement fallback for `get_embedding` if provider lacks direct support
2. LlamaCppProvider Implementation
   - [ ] Implement `classify` using `generate_text`
   - [ ] Implement `extract_structured_data` using `generate_text`
   - [ ] Implement `analyze_help_text` using `generate_text`
   - [ ] Implement `compare_outputs` using `generate_text`
3. Configuration
   - [ ] Ensure provider-specific config (e.g., `model_path`, `n_ctx`) is passed correctly during initialization.
4. CLI (`config llm`)
   - [ ] Refine error handling and user feedback.
   - [ ] Add tests for the new CLI commands.
5. Testing (Core LLM)
   - [ ] Add unit/integration tests for LLM Manager and LlamaCppProvider.

## Decisions & Considerations

### Technology Decisions
1. **Python Version**: Using Python 3.13 for latest features and performance
2. **Package Management**: Using uv for speed and reliability
3. **CLI Framework**: Using Typer for type-safe CLI development
4. **ORM**: Using SQLModel for database interactions
5. **Logging**: Using structlog for structured logging
6. **Testing**: Using pytest with pytest-cov for coverage

### Architecture Decisions
1. **Modular Design**: Components with well-defined interfaces
2. **Repository Pattern**: For data access abstraction
3. **Factory Pattern**: For object creation
4. **Strategy Pattern**: For flexible implementations
5. **Test-Driven Development**: Writing tests before implementation
6. **Domain-Driven Design**: Organizing code around business domains

### Resolved Decisions
1. **Package Management**: Chosen uv over pip/poetry for speed and reliability
2. **Code Formatting**: Chosen ruff over black for linting and formatting
3. **Test Framework**: Chosen pytest over unittest for flexibility and plugins
4. **CI/CD Provider**: Chosen GitHub Actions for tight integration with repository
5. **CLI Analysis Approach**: Implemented two-phase analysis with cycle detection for robust processing

### Pending Decisions
1. **Default LLM Provider**: Evaluating OpenAI vs. Anthropic vs. local models
2. **Container Management**: Evaluating different Docker Python libraries

## Blockers & Challenges
1. **SQLModel Integration**: Ensuring proper integration with Pydantic v2
2. **Interface Design**: Creating flexible yet type-safe interfaces
3. **Error Handling**: Designing a comprehensive error handling system
4. **Testing Strategy**: Developing effective tests for abstract interfaces

## Active Discussions
1. Best approach for dependency injection in Python
2. Strategies for testing abstract interfaces
3. Error handling patterns for CLI applications
4. Performance considerations for database operations
