#!/bin/bash

# Set error mode to exit on any error
set -e

# Script to test GitHub Actions workflows locally using act
# This script builds a Docker image and uses it to run GitHub Actions workflows

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define variables
DOCKER_IMAGE="testronaut-workflows:latest"
ACT_ARGS=""
WORKFLOW_FILE=""

# Print header
echo -e "${BLUE}Testronaut Workflow Testing Utility${NC}"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${YELLOW}Warning: 'act' is not installed. Installing...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install act
    else
        # Linux
        curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
    fi
fi

# Function to print usage
function print_usage {
    echo -e "${BLUE}Usage:${NC}"
    echo "  $0 [options]"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo "  -w, --workflow FILE   Specify the workflow file to test (e.g. main.yml)"
    echo "  -j, --job JOB         Specify a job to run"
    echo "  -l, --list            List workflows and jobs"
    echo "  -b, --build           Build Docker image only (don't run workflows)"
    echo "  -v, --validate        Validate workflow files"
    echo "  -h, --help            Show this help message"
    echo ""
    echo -e "${BLUE}Example:${NC}"
    echo "  $0 --workflow main.yml"
    echo "  $0 --workflow main.yml --job test"
    echo "  $0 --list"
    echo "  $0 --validate"
}

# Process command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -w|--workflow) WORKFLOW_FILE="$2"; shift ;;
        -j|--job) ACT_ARGS="$ACT_ARGS -j $2"; shift ;;
        -l|--list) LIST_MODE=true ;;
        -b|--build) BUILD_ONLY=true ;;
        -v|--validate) VALIDATE_MODE=true ;;
        -h|--help) print_usage; exit 0 ;;
        *) echo -e "${RED}Unknown parameter: $1${NC}"; print_usage; exit 1 ;;
    esac
    shift
done

# Make sure we're in the repository root
cd "$(git rev-parse --show-toplevel)"

# Build Docker image
echo -e "${BLUE}Building Docker image for workflow testing...${NC}"
docker build -t "$DOCKER_IMAGE" -f ci/Dockerfile.workflows .

# If build only mode, exit here
if [[ "$BUILD_ONLY" = true ]]; then
    echo -e "${GREEN}Docker image built successfully.${NC}"
    exit 0
fi

# If validate mode, run GitHub Actions validator
if [[ "$VALIDATE_MODE" = true ]]; then
    echo -e "${BLUE}Validating workflow files...${NC}"
    docker run --rm -v "$(pwd):/github/workspace" "$DOCKER_IMAGE" \
        actions-validator .github/workflows/*.yml
    echo -e "${GREEN}Validation complete.${NC}"
    exit 0
fi

# If list mode, list workflows and jobs
if [[ "$LIST_MODE" = true ]]; then
    echo -e "${BLUE}Available workflows and jobs:${NC}"
    act -l
    exit 0
fi

# If no workflow specified, prompt user
if [[ -z "$WORKFLOW_FILE" ]]; then
    echo -e "${YELLOW}No workflow specified. Available workflows:${NC}"
    ls -1 .github/workflows/*.yml | xargs -n 1 basename
    echo ""
    read -p "Enter workflow filename (e.g. main.yml): " WORKFLOW_FILE
fi

# Check if workflow file exists
if [[ ! -f ".github/workflows/$WORKFLOW_FILE" ]]; then
    echo -e "${RED}Error: Workflow file '.github/workflows/$WORKFLOW_FILE' not found${NC}"
    exit 1
fi

# Run the workflow using act
echo -e "${BLUE}Running workflow: $WORKFLOW_FILE${NC}"
act -P ubuntu-latest=testronaut-workflows:latest -W ".github/workflows/$WORKFLOW_FILE" $ACT_ARGS

echo -e "${GREEN}Workflow testing complete.${NC}"