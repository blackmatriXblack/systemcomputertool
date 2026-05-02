#!/usr/bin/env bash
# ComputerTool Launcher for Linux and macOS

set -e

# Check for Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3.7+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3"
    echo "  Fedora:        sudo dnf install python3"
    echo "  macOS:         brew install python3"
    exit 1
fi

# Determine Python command
if command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run ComputerTool
cd "$SCRIPT_DIR"
"$PYTHON" computertool.py "$@"
