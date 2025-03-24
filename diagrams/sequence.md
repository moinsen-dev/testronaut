# Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI Interface
    participant Analyzer as CLI Analyzer
    participant LLM as LLM Service
    participant TestGen as Test Generator
    participant Executor as Test Executor
    participant Docker as Docker Container
    participant Verifier as Result Verifier
    participant DB as SQLite Database
    participant FS as File System
    
    User->>CLI: ai-cli-test analyze --tool=[tool]
    CLI->>Analyzer: Analyze CLI tool
    Analyzer->>CLI: Execute help commands
    CLI->>CLI: Collect help output
    
    Analyzer->>LLM: Send help output for analysis
    LLM-->>Analyzer: Return structured command metadata
    Analyzer->>DB: Store CLI tool metadata
    
    Analyzer->>TestGen: Generate test plan
    TestGen->>LLM: Request test cases
    LLM-->>TestGen: Return generated test cases
    TestGen->>DB: Store test plan
    TestGen-->>CLI: Display test plan summary
    CLI-->>User: Show test plan
    
    User->>CLI: ai-cli-test generate --plan=[id]
    CLI->>Executor: Execute test plan (generate mode)
    Executor->>Docker: Create container
    Executor->>Docker: Install CLI tool
    
    loop For each test case
        Executor->>DB: Get test case
        Executor->>Docker: Execute command
        Docker-->>Executor: Return outputs
        Executor->>FS: Store expected outputs
        Executor->>DB: Update test case with expected results
    end
    
    Executor-->>CLI: Generation complete
    CLI-->>User: Show generation results
    
    User->>CLI: ai-cli-test verify --plan=[id]
    CLI->>Executor: Execute test plan (verify mode)
    
    loop For each test case
        Executor->>DB: Get test case with expected results
        Executor->>Docker: Execute command
        Docker-->>Executor: Return actual outputs
        Executor->>Verifier: Compare outputs
        Verifier->>LLM: Request semantic comparison
        LLM-->>Verifier: Return comparison results
        Verifier->>DB: Store test results
    end
    
    Executor-->>CLI: Verification complete
    CLI-->>User: Show verification summary
    
    User->>CLI: ai-cli-test report --plan=[id]
    CLI->>DB: Generate comprehensive report
    DB-->>CLI: Return report data
    CLI-->>User: Display detailed test report
```

This sequence diagram illustrates the complete workflow of the AI-CLI-Testing tool:

1. **Analysis Phase**
   - User requests CLI tool analysis
   - System extracts help text and sends to LLM
   - LLM returns structured command metadata
   - System generates a test plan

2. **Generation Phase**
   - User initiates test generation
   - System creates Docker container and installs CLI tool
   - System executes each test case and captures expected outputs
   - Expected results are stored for later verification

3. **Verification Phase**
   - User initiates test verification
   - System re-executes test cases and captures actual outputs
   - LLM performs semantic comparison between expected and actual outputs
   - Results are stored in the database

4. **Reporting Phase**
   - User requests a test report
   - System generates comprehensive report from results
   - Report is displayed to the user

The diagram shows interaction between all major components and how data flows through the system.