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
echo -e "${BLUE}Testronaut Documentation Workflow Testing Utility${NC}"
echo "================================================="
echo ""

# Make sure we're in the repository root
cd "$(git rev-parse --show-toplevel)"

# Create a temporary directory for output
TEMP_DIR=$(mktemp -d)
echo -e "${BLUE}Creating temporary directory for docs output: $TEMP_DIR${NC}"

# Create a virtual environment
VENV_DIR="$TEMP_DIR/venv"
echo -e "${BLUE}Creating virtual environment at: $VENV_DIR${NC}"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo -e "${YELLOW}Warning: pip is not available in the virtual environment. Installing...${NC}"
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
fi

# Install MkDocs and dependencies
echo -e "${BLUE}Installing MkDocs and dependencies...${NC}"
pip install -e '.[docs]'
pip install mkdocs-material mkdocstrings mkdocstrings-python

# Build documentation
echo -e "${BLUE}Building documentation...${NC}"
mkdocs build -d "$TEMP_DIR/site"

# Check if build was successful
if [ -f "$TEMP_DIR/site/index.html" ]; then
    echo -e "${GREEN}Documentation built successfully!${NC}"

    # Count files
    DOC_FILES=$(find "$TEMP_DIR/site" -type f | wc -l)
    echo -e "${BLUE}Generated $DOC_FILES documentation files.${NC}"

    # Offer to serve the docs
    echo ""
    read -p "Would you like to serve the documentation locally? (y/n) " SERVE_DOCS
    if [[ "$SERVE_DOCS" == "y" || "$SERVE_DOCS" == "Y" ]]; then
        echo -e "${BLUE}Serving documentation at http://localhost:8000/${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
        mkdocs serve
    else
        echo -e "${BLUE}Documentation files are available at: $TEMP_DIR/site${NC}"
    fi
else
    echo -e "${RED}Documentation build failed!${NC}"
    exit 1
fi

# Deactivate the virtual environment
deactivate

# Print summary
echo ""
echo -e "${GREEN}Documentation build test complete.${NC}"
echo -e "${BLUE}Results:${NC}"
echo "- Documentation built successfully"
echo "- Output saved to $TEMP_DIR/site"