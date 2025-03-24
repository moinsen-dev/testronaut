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
echo -e "${BLUE}Testronaut Main Workflow Testing Utility${NC}"
echo "=========================================="
echo ""

# Make sure we're in the repository root
cd "$(git rev-parse --show-toplevel)"

# Create a temporary directory for output
TEMP_DIR=$(mktemp -d)
echo -e "${BLUE}Creating temporary directory for test output: $TEMP_DIR${NC}"

# Check if required tools are installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}Warning: UV is not installed. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for the current script
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Process command line arguments
SKIP_TESTS=false
SKIP_LINT=false
RUN_MYPY=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --skip-tests) SKIP_TESTS=true ;;
        --skip-lint) SKIP_LINT=true ;;
        --mypy) RUN_MYPY=true ;;
        -h|--help)
            echo -e "${BLUE}Usage:${NC}"
            echo "  $0 [options]"
            echo ""
            echo -e "${BLUE}Options:${NC}"
            echo "  --skip-tests   Skip running tests"
            echo "  --skip-lint    Skip running linting"
            echo "  --mypy         Run mypy type checking"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *) echo -e "${RED}Unknown parameter: $1${NC}"; exit 1 ;;
    esac
    shift
done

# Install dev dependencies
echo -e "${BLUE}Installing dev dependencies...${NC}"
uv pip install --system -e '.[dev]'

# Run linting if not skipped
if [ "$SKIP_LINT" = false ]; then
    echo -e "${BLUE}Running linting with ruff...${NC}"
    ruff check . > "$TEMP_DIR/ruff-output.txt" || {
        echo -e "${YELLOW}Ruff found linting issues. See $TEMP_DIR/ruff-output.txt${NC}"
        cat "$TEMP_DIR/ruff-output.txt"
    }

    echo -e "${BLUE}Running ruff format check...${NC}"
    ruff format --check . > "$TEMP_DIR/ruff-format-output.txt" || {
        echo -e "${YELLOW}Ruff found formatting issues. See $TEMP_DIR/ruff-format-output.txt${NC}"
        cat "$TEMP_DIR/ruff-format-output.txt"
    }

    # Run mypy if requested
    if [ "$RUN_MYPY" = true ]; then
        echo -e "${BLUE}Running type checking with mypy...${NC}"
        mypy src > "$TEMP_DIR/mypy-output.txt" || {
            echo -e "${YELLOW}Mypy found type issues. See $TEMP_DIR/mypy-output.txt${NC}"
            cat "$TEMP_DIR/mypy-output.txt"
        }
    fi
fi

# Run tests if not skipped
if [ "$SKIP_TESTS" = false ]; then
    echo -e "${BLUE}Running tests with pytest...${NC}"
    pytest -v --cov=src --cov-report=term --cov-report=html:$TEMP_DIR/coverage > "$TEMP_DIR/pytest-output.txt" || {
        echo -e "${RED}Tests failed. See $TEMP_DIR/pytest-output.txt${NC}"
        cat "$TEMP_DIR/pytest-output.txt"
        exit 1
    }

    # Show coverage report
    echo -e "${BLUE}Coverage Report:${NC}"
    cat "$TEMP_DIR/pytest-output.txt" | grep -A 100 "---------- coverage: "

    echo -e "${GREEN}Tests passed successfully!${NC}"
    echo -e "${BLUE}HTML coverage report saved to $TEMP_DIR/coverage/index.html${NC}"
fi

# Print summary
echo ""
echo -e "${GREEN}Main workflow test complete.${NC}"
echo -e "${BLUE}Results:${NC}"
if [ "$SKIP_LINT" = false ]; then
    echo "- Linting ran successfully"
    if [ "$RUN_MYPY" = true ]; then
        echo "- Type checking completed"
    fi
fi
if [ "$SKIP_TESTS" = false ]; then
    echo "- Tests executed successfully"
    echo "- Coverage report generated"
fi
echo "- All output saved to $TEMP_DIR"