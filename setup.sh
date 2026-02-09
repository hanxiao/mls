#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up MLS..."
echo "Project directory: $PROJECT_DIR"

# Create venv if needed
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

# Install dependencies
echo "Installing dependencies..."
"$PROJECT_DIR/.venv/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"

# Make scripts executable
chmod +x "$PROJECT_DIR/bin/server.py"
chmod +x "$PROJECT_DIR/bin/qwen3-asr"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Symlink wrapper to ~/.local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$PROJECT_DIR/bin/qwen3-asr" "$HOME/.local/bin/qwen3-asr"

echo ""
echo "Setup complete!"
echo "  - Start: cd $PROJECT_DIR && uv run bin/server.py"
echo "  - Server: http://127.0.0.1:18321"
echo "  - History UI: http://127.0.0.1:18321/history"
echo "  - CLI: qwen3-asr <audio_file> [language]"
