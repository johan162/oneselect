#!/bin/bash
# Coverage Badge Update Script
# Description: Update coverage badge/link in README.md from 'coverage.xml'
# CI/CD Support: Yes. Can be run in CI environments.
# Usage: ./scripts/mkcovupd.sh
#
# Example: ./scripts/mkcovupd.sh

set -euo pipefail # Exit on any error or uninitialized variable

# =====================================
# CONFIGURATION
# =====================================

declare PROGRAM_NAME="onesim"
declare PROGRAM_NAME_PRETTY="OneSim"
declare COVERAGE="80"

# Detect CI environment
if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo "🔧 Running in CI mode"
    CI_MODE=true
else
    echo "🔧 Running in local mode"
    CI_MODE=false
fi

# Color codes (disabled in CI)
if [ "$CI_MODE" = true ]; then
    GREEN=""
    RED=""
    YELLOW=""
    BLUE=""
    NC=""
else
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    NC='\033[0m'
fi

# =====================================
# Functions to print colored output
# =====================================
print_step() {
    echo -e "${BLUE}==>${NC} ${1}"
}

print_step_colored() {
    echo -e "${BLUE}==> ${1}${NC}"
}

print_sub_step() {
    echo -e "${BLUE}  ->${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ Success: ${1}${NC}"
}

print_success_colored() {
    if [ "$CI_MODE" = true ]; then
        echo -e "✓ Success: ${1}"
    else
        echo -e "${GREEN}✅ Success: ${1}${NC}"
    fi
}

print_error() {
    echo -e "${RED}✗ Error: ${NC} ${1}" >&2
}

print_error_colored() {
    if [ "$CI_MODE" = true ]; then
        echo -e "✗ Error: ${1}"
    else
        echo -e "${RED}❌ Error: ${1}${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠ Warning:${NC} ${1}"
}

print_warning_colored() {
    if [ "$CI_MODE" = true ]; then
        echo -e "⚠ Warning: ${1}"
    else
        echo -e "${YELLOW}⚠️  Warning: ${1}${NC}"
    fi
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_info_colored() {
    if [ "$CI_MODE" = true ]; then
        echo -e "ℹ $1"
    else
        echo -e "${BLUE}ℹ️  ${1}${NC}"
    fi
}

# Function to execute command or print it in dry-run mode
run_command() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would execute: ${cmd}"
    else
        print_sub_step "$description"
        echo "Executing: $cmd"
        if eval "$cmd"; then
            print_success_colored "$description completed"
        else
            print_error_colored "$description failed"
            exit 1
        fi
    fi
}

show_help() {
    cat << EOF
🚀 ${PROGRAM_NAME_PRETTY} Helper for coverage badge update

DESCRIPTION:
    This script updates the coverage badge/link in README.md based on the
    line-rate found in coverage.xml. It extracts the line-rate, determines
    the appropriate badge color, and updates the README.md file accordingly.

USAGE: 
    $0 [OPTIONS]

OPTIONS:
    --dry-run       Print commands that would be executed without running them
    --help          Show this help message and exit

REQUIREMENTS:
    - Must be run from the project root directory

EXAMPLES:
    $0                  # Run full build process
    $0 --dry-run        # Show what would be executed
    $0 --help           # Show this help

EXIT CODES:
    0    Success
    1    Usage error
EOF
}

# Default options
DRY_RUN=false
HELP=false

# File paths, The script must be run from the project root.
COVERAGE_XML="./coverage.xml"
README_FILE="./README.md"


# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 2
            ;;
    esac
done

# Show help if requested
if [ "$HELP" = true ]; then
    show_help
    exit 0
fi

# =====================================
# PHASE 1: PRE-RELEASE VALIDATION
# =====================================

print_step_colored ""
print_step_colored "🔍 PHASE 1: PRE-REQ VALIDATIONS"
print_step_colored ""

# 1.1 Check if we're in the right directory
run_command "test -f pyproject.toml" "Build script must be run from project root."

# 1.2 Check if coverage.xml exists
print_sub_step "Check for 'coverage.xml'"
if [ ! -f "$COVERAGE_XML" ]; then
    print_error_colored "coverage.xml not found"
    echo "Run pytest with coverage first: pytest --cov=src/${PROGRAM_NAME} --cov-report=xml"
    exit 1
fi

# 1.3 Check if README.md exists
print_sub_step "Check for 'README.md'"
if [ ! -f "$README_FILE" ]; then
    print_error_colored "README.md not found"
    exit 1
fi

# =====================================
# PHASE 2: EXTRACT COVERAGE
# =====================================

echo ""
print_step_colored ""
print_step_colored "🧪 PHASE 2: EXTRACT COVERAGE"
print_step_colored ""

# Extract line-rate from coverage.xml
# The coverage XML format: <coverage line-rate="0.8345" ...>
line_rate=$(grep -o '<coverage[^>]*line-rate="[0-9.]*"' "$COVERAGE_XML" | grep -o 'line-rate="[0-9.]*"' | cut -d'"' -f2)

if [ -z "$line_rate" ]; then
    print_error_colored "Could not extract line-rate from coverage.xml"
    exit 1
fi

# Convert to percentage and round to 2 decimal places
coverage_percent=$(echo "$line_rate * 100" | bc -l | xargs printf "%.0f")

echo -e "📊 Coverage line-rate: ${MAGENTA}${line_rate}${NC}"
echo -e "📊 Coverage percentage: ${MAGENTA}${coverage_percent}%${NC}"

# Determine badge color based on coverage
if [ "$coverage_percent" -ge 90 ]; then
    badge_color="darkgreen"
elif [ "$coverage_percent" -ge 80 ]; then
    badge_color="brightgreen"
elif [ "$coverage_percent" -ge 70 ]; then
    badge_color="yellowgreen"
elif [ "$coverage_percent" -ge 60 ]; then
    badge_color="yellow"
elif [ "$coverage_percent" -ge 50 ]; then
    badge_color="orange"
else
    badge_color="red"
fi

echo -e "🎨 Badge color: ${MAGENTA}${badge_color}${NC}"

# Create the new badge URL
new_badge_url="https://img.shields.io/badge/coverage-${coverage_percent}%25-${badge_color}.svg"


# =====================================
# PHASE 3: UPDATE README FILE
# =====================================

echo ""
print_step_colored ""
print_step_colored "🧪 PHASE 3: UPDATE README FILE"
print_step_colored ""

# Find the line with the coverage badge and replace it
if grep -q "img.shields.io/badge/coverage-" "$README_FILE"; then
    # Use sed to replace the coverage badge URL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS sed requires empty string after -i
        run_command "sed -i '' \"s|https://img.shields.io/badge/coverage-[0-9]*%25-[a-z]*.svg|${new_badge_url}|g\" \"$README_FILE\"" "Updating coverage badge in README.md to ${coverage_percent}%"
        # sed -i '' "s|https://img.shields.io/badge/coverage-[0-9]*%25-[a-z]*.svg|${new_badge_url}|g" "$README_FILE"
    else
        # Linux sed
        run_command "sed -i \"s|https://img.shields.io/badge/coverage-[0-9]*%25-[a-z]*.svg|${new_badge_url}|g\" \"$README_FILE\"" "Updating coverage badge in README.md to ${coverage_percent}%"
        # sed -i "s|https://img.shields.io/badge/coverage-[0-9]*%25-[a-z]*.svg|${new_badge_url}|g" "$README_FILE"
    fi
    # print_success_colored "Updated coverage badge in README.md to ${coverage_percent}%"
else
    print_warning_colored "Coverage badge not found in README.md"
    echo "Expected pattern: https://img.shields.io/badge/coverage-XX%25-COLOR.svg"
    exit 1
fi

# Verify the change
run_command "grep '${new_badge_url}' \"$README_FILE\"" "Verifying updated badge (${coverage_percent}%) in README.md"

echo ""
exit 0
# End of script
