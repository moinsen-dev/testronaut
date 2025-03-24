# Template Dockerfile for test containers
FROM ubuntu:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install essential tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        wget \
        git \
        python3 \
        python3-pip \
        ca-certificates \
        jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directories for test artifacts
RUN mkdir -p /test-artifacts/inputs \
    && mkdir -p /test-artifacts/outputs \
    && mkdir -p /test-artifacts/expected

# Set working directory
WORKDIR /workspace

# This is a template Dockerfile
# The following sections will be generated dynamically:
# 1. Tool installation command
# 2. Additional dependencies
# 3. Environment setup
# 4. Volume mounts

# Default command (will be overridden during test execution)
CMD ["bash"]
