#!/bin/bash
# Book-Angel macOS Double-Click Launcher
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Ensure dependencies are installed
if ! python3 -c "import book_angel" &> /dev/null; then
    echo "First-time setup: installing Book-Angel..."
    pip3 install -e .
fi

# Run interactive launcher
python3 -m book_angel.cli
