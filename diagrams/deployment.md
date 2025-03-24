# Deployment Diagram

```mermaid
graph TD
    subgraph Host[Host Machine]
        App[AI-CLI-Testing Application]
        DB[(SQLite Database)]
        FS[File System]
        DockerService[Docker Service]
    end
    
    subgraph DockerEnvironment[Docker Environment]
        Network[Internal Docker Network]
        
        subgraph TestContainer1[Test Container 1]
            CLITool1[CLI Tool Instance]
        end
        
        subgraph TestContainer2[Test Container 2]
            CLITool2[CLI Tool Instance]
        end
        
        subgraph TestContainerN[Test Container N]
            CLIToolN[CLI Tool Instance]
        end
    end
    
    subgraph ExternalServices[External Services]
        CloudLLM[Cloud LLM API]
    end
    
    subgraph LocalAI[Local AI]
        LocalLLM[Local LLM]
    end
    
    App --> DB
    App --> FS
    App --> DockerService
    
    DockerService --> Network
    Network --> TestContainer1
    Network --> TestContainer2
    Network --> TestContainerN
    
    App --> CloudLLM
    App --> LocalLLM
    
    TestContainer1 --> AppFS[App File System Mount]
    TestContainer2 --> AppFS
    TestContainerN --> AppFS
    
    AppFS --> FS
    
    classDef host fill:#f9f,stroke:#333,stroke-width:2px;
    classDef container fill:#fbb,stroke:#a33,stroke-width:2px;
    classDef external fill:#bbf,stroke:#33a,stroke-width:2px;
    classDef local fill:#bfb,stroke:#3a3,stroke-width:2px;
    
    class App,DB,FS,DockerService host;
    class TestContainer1,TestContainer2,TestContainerN,CLITool1,CLITool2,CLIToolN,Network container;
    class CloudLLM external;
    class LocalLLM local;
```

This deployment diagram illustrates how the AI-CLI-Testing tool is deployed and how its components interact in a runtime environment:

1. **Host Machine**:
   - Contains the AI-CLI-Testing application
   - SQLite database for persistent storage
   - File system for test artifacts
   - Docker service for managing containers

2. **Docker Environment**:
   - Internal Docker network
   - Multiple test containers running in isolation
   - Each container has its own instance of the CLI tool being tested
   - Containers have limited access to host file system through mounts

3. **External Services**:
   - Cloud LLM APIs (OpenAI, Anthropic, etc.)
   - Used for AI-powered analysis, generation, and verification

4. **Local AI**:
   - Local LLM deployment for cost-efficient operation
   - Alternative to cloud APIs for sensitive environments

The deployment shows how the system maintains isolation between test executions using Docker containers while still allowing for efficient data exchange through controlled file system mounts. It also illustrates the flexibility of using either cloud or local LLMs depending on requirements.