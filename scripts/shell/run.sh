#!/bin/bash

# ANSI Color Codes
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_BLUE='\033[0;34m'
C_CYAN='\033[0;36m'
C_NC='\033[0m' # No Color

# --- Helper Functions ---

print_header() {
    echo -e "${C_CYAN}======================================================================${C_NC}"
    echo -e "${C_CYAN}  $1${C_NC}"
    echo -e "${C_CYAN}======================================================================${C_NC}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

kill_on_port() {
    local port=$1
    if command_exists lsof; then
        local pid=$(lsof -t -i:$port)
        if [ -n "$pid" ]; then
            echo -e "${C_YELLOW}Killing existing process on port $port (PID: $pid)...${C_NC}"
            kill -9 "$pid"
        fi
    fi
}

# --- Main Logic ---

# --- BULLETPROOF FIX: Resolve the real script path, even when called via symlink ---
# Get the path of the script itself.
# BASH_SOURCE[0] is the path of the script as it was called.
# readlink -f resolves all symlinks and returns the absolute, canonical path.
SCRIPT_PATH=$(readlink -f "${BASH_SOURCE[0]}")
# Get the directory containing the real script.
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")

# Change to project root (two levels up from scripts/shell/)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
cd "$PROJECT_ROOT" || { echo -e "${C_RED}Error: Could not change to the project root directory '$PROJECT_ROOT'${C_NC}"; exit 1; }
echo -e "${C_BLUE}Working directory successfully set to: $PWD${C_NC}"


# Clean up previous runs on exit
trap "echo -e '\n${C_YELLOW}Shutting down services...${C_NC}'; kill 0 2>/dev/null" EXIT

# --- Backend Setup & Launch ---

print_header "NEXUS Backend Startup"

# Check for Poetry
if ! command_exists poetry; then
    echo -e "${C_YELLOW}Poetry not found. Installing...${C_NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install Python dependencies via Poetry
if [ -f "pyproject.toml" ]; then
    echo "Installing Python dependencies via Poetry..."
    poetry install --only main --quiet
else
    echo -e "${C_RED}Error: pyproject.toml not found!${C_NC}"
    exit 1
fi

# Clean port and start backend in the background
kill_on_port 8000
echo -e "${C_GREEN}Starting NEXUS backend server in the background...${C_NC}"
poetry run python -m nexus.main &
BACKEND_PID=$!
echo -e "Backend PID: ${C_BLUE}$BACKEND_PID${C_NC}"
sleep 3 # Give backend a moment to start

# --- Frontend Setup & Launch ---

print_header "AURA Frontend Startup"

# Navigate to aura directory
if [ ! -d "aura" ]; then
    echo -e "${C_RED}Error: 'aura' directory not found in $PWD!${C_NC}"
    exit 1
fi
cd aura

# Check for pnpm
if ! command_exists pnpm; then
    echo -e "${C_YELLOW}pnpm not found. Installing via npm...${C_NC}"
    npm install -g pnpm
fi

# Check and install Node.js dependencies
if [ -f "package.json" ]; then
    echo "Checking Node.js dependencies..."
    pnpm install --silent
else
    echo -e "${C_RED}Error: package.json not found!${C_NC}"
    exit 1
fi

# Clean port and start frontend in the background
kill_on_port 5173
echo -e "${C_GREEN}Starting AURA frontend server in the background...${C_NC}"
pnpm dev &
FRONTEND_PID=$!
echo -e "Frontend PID: ${C_BLUE}$FRONTEND_PID${C_NC}"

# --- Wait for processes ---

cd .. # Return to root directory
echo -e "\n${C_GREEN}NEXUS & AURA are running.${C_NC}"
echo -e "Frontend available at: ${C_YELLOW}http://localhost:5173${C_NC}"
echo -e "Backend logs will appear below. Press ${C_YELLOW}Ctrl+C${C_NC} to shut down all services."

wait $BACKEND_PID