# Architecture Diagram

```mermaid
graph TD
    subgraph UserInterface
        CLI[CLI Interface]
    end
    
    subgraph CoreComponents
        Analyzer[CLI Analyzer]
        TestGenerator[Test Plan Generator]
        TestExecutor[Test Executor]
        ResultVerifier[Result Verifier]
    end
    
    subgraph AILayer
        LLMManager[LLM Manager]
        LLMManager --> CloudLLM[Cloud LLMs]
        LLMManager --> LocalLLM[Local LLMs]
    end
    
    subgraph Storage
        DB[(SQLite Database)]
        FS[File System]
    end
    
    subgraph DockerEnvironment
        Container1[Test Container 1]
        Container2[Test Container 2]
        ContainerN[Test Container N]
    end
    
    CLI --> Analyzer
    Analyzer --> LLMManager
    Analyzer --> DB
    
    Analyzer --> TestGenerator
    TestGenerator --> LLMManager
    TestGenerator --> DB
    
    TestGenerator --> TestExecutor
    TestExecutor --> Container1
    TestExecutor --> Container2
    TestExecutor --> ContainerN
    TestExecutor --> FS
    
    TestExecutor --> ResultVerifier
    ResultVerifier --> LLMManager
    ResultVerifier --> DB
    ResultVerifier --> FS
    
    ResultVerifier --> CLI
    
    classDef core fill:#f9f,stroke:#333,stroke-width:2px;
    classDef ai fill:#bbf,stroke:#33a,stroke-width:2px;
    classDef storage fill:#bfb,stroke:#3a3,stroke-width:2px;
    classDef container fill:#fbb,stroke:#a33,stroke-width:2px;
    
    class Analyzer,TestGenerator,TestExecutor,ResultVerifier core;
    class LLMManager,CloudLLM,LocalLLM ai;
    class DB,FS storage;
    class Container1,Container2,ContainerN container;
```

This architecture diagram illustrates the main components of the AI-CLI-Testing tool and how they interact:

1. **User Interface**: A command-line interface for interacting with the system
2. **Core Components**:
   - CLI Analyzer: Parses and understands CLI tools using AI
   - Test Generator: Creates test plans based on CLI analysis
   - Test Executor: Runs tests in Docker containers
   - Result Verifier: Compares expected vs. actual results
3. **AI Layer**: Manages integration with both cloud and local LLMs
4. **Storage**: SQLite database for structured data and file system for artifacts
5. **Docker Environment**: Isolated containers for test execution

The arrows indicate the flow of data and control between components. The system follows a sequential workflow but with feedback loops for verification and reporting.