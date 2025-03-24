#!/bin/bash

# Set error mode to exit on any error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}Testronaut Security Workflow Testing Utility${NC}"
echo "=============================================="
echo ""

# Make sure we're in the repository root
cd "$(git rev-parse --show-toplevel)"

# Create a temporary directory for output
TEMP_DIR=$(mktemp -d)
echo -e "${BLUE}Creating temporary directory for test output: $TEMP_DIR${NC}"

# Create a virtual environment
VENV_DIR="$TEMP_DIR/venv"
echo -e "${BLUE}Creating virtual environment at: $VENV_DIR${NC}"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Check if required tools are installed
if ! command -v pip &> /dev/null; then
    echo -e "${YELLOW}Warning: pip is not available in the virtual environment. Installing...${NC}"
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
fi

# Install security tools
echo -e "${BLUE}Installing security scanning tools...${NC}"
pip install safety bandit

# Create a requirements file
echo -e "${BLUE}Generating requirements file...${NC}"
pip freeze > "$TEMP_DIR/requirements-frozen.txt"

# Run Safety check
echo -e "${BLUE}Running Safety security check...${NC}"
safety check -r "$TEMP_DIR/requirements-frozen.txt" --full-report || {
    echo -e "${YELLOW}Safety check found security issues.${NC}"
}

# Run Bandit check
echo -e "${BLUE}Running Bandit security check...${NC}"
bandit -r src/ -f json -o "$TEMP_DIR/bandit-results.json" || {
    echo -e "${YELLOW}Bandit found security issues. Results saved to $TEMP_DIR/bandit-results.json${NC}"
}

# Deactivate the virtual environment
deactivate

# Print summary
echo ""
echo -e "${GREEN}Security scan testing complete.${NC}"
echo -e "${BLUE}Results:${NC}"
echo "- Safety report ran successfully"
echo "- Bandit report saved to $TEMP_DIR/bandit-results.json"
echo ""
echo -e "${YELLOW}Note: This script mimics the security workflow but doesn't run CodeQL analysis,${NC}"
echo -e "${YELLOW}which requires GitHub's infrastructure. Use GitHub Actions for complete testing.${NC}"